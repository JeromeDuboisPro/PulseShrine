"""
User Service for managing user profiles and plans.
"""

import boto3
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from aws_lambda_powertools import Logger

logger = Logger()


class UserService:
    """Service for managing user profiles and plan information."""
    
    def __init__(self, table_name: Optional[str] = None):
        self.table_name = table_name or os.environ.get("USERS_TABLE_NAME", "ps-users")
        self._dynamodb = None
        self._table = None

    @property
    def dynamodb(self):
        """Lazy initialization of DynamoDB resource"""
        if self._dynamodb is None:
            self._dynamodb = boto3.resource("dynamodb")
        return self._dynamodb

    @property
    def table(self):
        """Lazy initialization of DynamoDB table"""
        if self._table is None:
            self._table = self.dynamodb.Table(self.table_name)
        return self._table

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile, creating a default one if it doesn't exist."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "PROFILE"
                }
            )
            
            if "Item" in response:
                return response["Item"]
            else:
                # Create default user profile
                default_profile = self._create_default_user_profile(user_id)
                return default_profile
                
        except Exception as e:
            logger.error(f"Error getting user profile for {user_id}: {e}")
            # Return a safe default profile without saving
            return {
                "PK": f"USER#{user_id}",
                "SK": "PROFILE",
                "user_id": user_id,
                "plan": "free",
                "plan_expires": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

    def get_user_plan(self, user_id: str) -> str:
        """Get user's current plan (free, premium, unlimited)."""
        try:
            profile = self.get_user_profile(user_id)
            plan = profile.get("plan", "free")
            
            # Check if plan has expired
            plan_expires = profile.get("plan_expires")
            if plan_expires and plan != "free":
                expiry_date = datetime.fromisoformat(plan_expires.replace('Z', '+00:00'))
                if datetime.now(timezone.utc) > expiry_date:
                    logger.info(f"Plan expired for user {user_id}, downgrading to free")
                    # Could auto-update to free here, but for now just return free
                    return "free"
            
            return plan
            
        except Exception as e:
            logger.error(f"Error getting user plan for {user_id}: {e}")
            return "free"  # Safe default

    def _create_default_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Create a default user profile."""
        now = datetime.now(timezone.utc).isoformat()
        
        default_profile = {
            "PK": f"USER#{user_id}",
            "SK": "PROFILE",
            "user_id": user_id,
            "plan": "free",
            "plan_expires": None,
            "created_at": now,
            "updated_at": now,
            "preferences": {
                "notifications": True,
                "daily_summary": True,
            },
            "stats": {
                "total_pulses": 0,
                "total_ai_enhancements": 0,
                "member_since": now,
            }
        }
        
        try:
            self.table.put_item(Item=default_profile)
            logger.info(f"Created default profile for user {user_id}")
            return default_profile
        except Exception as e:
            logger.error(f"Error creating default profile for {user_id}: {e}")
            return default_profile

    def update_user_plan(self, user_id: str, plan: str, expires: Optional[str] = None) -> bool:
        """Update user's plan."""
        try:
            update_expression = "SET plan = :plan, updated_at = :updated_at"
            expression_values = {
                ":plan": plan,
                ":updated_at": datetime.now(timezone.utc).isoformat(),
            }
            
            if expires:
                update_expression += ", plan_expires = :expires"
                expression_values[":expires"] = expires
            elif plan == "free":
                # Clear expiry for free plan
                update_expression += " REMOVE plan_expires"
            
            self.table.update_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "PROFILE"
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            logger.info(f"Updated plan for user {user_id} to {plan}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating plan for user {user_id}: {e}")
            return False

    def update_user_stats(self, user_id: str, pulse_increment: int = 0, ai_enhancement_increment: int = 0) -> bool:
        """Update user statistics."""
        try:
            update_expression = "ADD stats.total_pulses :pulse_inc, stats.total_ai_enhancements :ai_inc SET updated_at = :updated_at"
            expression_values = {
                ":pulse_inc": pulse_increment,
                ":ai_inc": ai_enhancement_increment,
                ":updated_at": datetime.now(timezone.utc).isoformat(),
            }
            
            self.table.update_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "PROFILE"
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating stats for user {user_id}: {e}")
            return False