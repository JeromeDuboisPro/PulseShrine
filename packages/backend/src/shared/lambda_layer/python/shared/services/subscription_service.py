"""
Subscription Service for PulseShrine Monetization

Handles subscription management, usage tracking, and quota enforcement.
"""

import boto3
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from aws_lambda_powertools import Logger

from ..models.pulse import UserSubscription, SubscriptionTier, SubscriptionStatus

logger = Logger()


class SubscriptionService:
    """Service for managing user subscriptions and usage quotas"""
    
    def __init__(self, table_name: str, dynamodb_client=None):
        """
        Initialize subscription service
        
        Args:
            table_name: DynamoDB table name for subscriptions
            dynamodb_client: Optional boto3 DynamoDB client
        """
        self.dynamodb = dynamodb_client or boto3.client('dynamodb')
        self.table_name = table_name
    
    def create_user_subscription(self, user_id: str, email: str = None) -> UserSubscription:
        """
        Create a new user subscription (starts as FREE tier)
        
        Args:
            user_id: Unique user identifier
            email: User email for billing
            
        Returns:
            UserSubscription: Created subscription object
        """
        subscription = UserSubscription(
            user_id=user_id,
            subscription_tier=SubscriptionTier.FREE,
            subscription_status=SubscriptionStatus.ACTIVE
        )
        
        # Save to DynamoDB
        item = {
            'PK': {'S': f'USER#{user_id}'},
            'SK': {'S': 'SUBSCRIPTION'},
            'user_id': {'S': subscription.user_id},
            'subscription_tier': {'S': subscription.subscription_tier.value},
            'subscription_status': {'S': subscription.subscription_status.value},
            'billing_cycle_start': {'S': subscription.billing_cycle_start.isoformat()},
            'billing_cycle_end': {'S': subscription.billing_cycle_end.isoformat()},
            'current_pulse_count': {'N': str(subscription.current_pulse_count)},
            'current_ai_enhancement_count': {'N': str(subscription.current_ai_enhancement_count)},
            'total_ai_cost_cents': {'N': str(subscription.total_ai_cost_cents)},
            'created_at': {'S': subscription.created_at.isoformat()},
            'updated_at': {'S': subscription.updated_at.isoformat()},
        }
        
        if email:
            item['email'] = {'S': email}
            
        self.dynamodb.put_item(TableName=self.table_name, Item=item)
        logger.info(f"Created subscription for user {user_id}")
        
        return subscription
    
    def get_user_subscription(self, user_id: str) -> Optional[UserSubscription]:
        """
        Get user subscription by user_id
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            UserSubscription or None if not found
        """
        try:
            response = self.dynamodb.get_item(
                TableName=self.table_name,
                Key={
                    'PK': {'S': f'USER#{user_id}'},
                    'SK': {'S': 'SUBSCRIPTION'}
                }
            )
            
            if 'Item' not in response:
                return None
                
            item = response['Item']
            
            # Parse DynamoDB item back to UserSubscription
            subscription = UserSubscription(
                user_id=item['user_id']['S'],
                subscription_tier=SubscriptionTier(item['subscription_tier']['S']),
                subscription_status=SubscriptionStatus(item['subscription_status']['S']),
                stripe_customer_id=item.get('stripe_customer_id', {}).get('S'),
                stripe_subscription_id=item.get('stripe_subscription_id', {}).get('S'),
                billing_cycle_start=datetime.fromisoformat(item['billing_cycle_start']['S']),
                billing_cycle_end=datetime.fromisoformat(item['billing_cycle_end']['S']),
                next_billing_date=datetime.fromisoformat(item['next_billing_date']['S']) if 'next_billing_date' in item else None,
                current_pulse_count=int(item['current_pulse_count']['N']),
                current_ai_enhancement_count=int(item['current_ai_enhancement_count']['N']),
                total_ai_cost_cents=float(item['total_ai_cost_cents']['N']),
                trial_end_date=datetime.fromisoformat(item['trial_end_date']['S']) if 'trial_end_date' in item else None,
                created_at=datetime.fromisoformat(item['created_at']['S']),
                updated_at=datetime.fromisoformat(item['updated_at']['S'])
            )
            
            return subscription
            
        except Exception as e:
            logger.error(f"Error getting subscription for user {user_id}: {str(e)}")
            return None
    
    def get_or_create_subscription(self, user_id: str, email: str = None) -> UserSubscription:
        """
        Get existing subscription or create new one
        
        Args:
            user_id: Unique user identifier
            email: User email for new subscription
            
        Returns:
            UserSubscription: Existing or newly created subscription
        """
        subscription = self.get_user_subscription(user_id)
        if not subscription:
            subscription = self.create_user_subscription(user_id, email)
        return subscription
    
    def check_pulse_quota(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user can create a new pulse
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Dict with 'allowed' boolean and 'reason' string
        """
        subscription = self.get_or_create_subscription(user_id)
        
        if subscription.can_create_pulse:
            return {
                'allowed': True,
                'remaining': (subscription.quotas.monthly_pulses - subscription.current_pulse_count) if subscription.quotas.monthly_pulses != -1 else -1,
                'quota': subscription.quotas.monthly_pulses
            }
        else:
            return {
                'allowed': False,
                'reason': f'Monthly pulse limit reached ({subscription.quotas.monthly_pulses})',
                'upgrade_required': True,
                'current_tier': subscription.subscription_tier.value
            }
    
    def check_ai_quota(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user can use AI enhancement
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Dict with 'allowed' boolean and 'reason' string
        """
        subscription = self.get_or_create_subscription(user_id)
        
        if subscription.can_use_ai_enhancement:
            return {
                'allowed': True,
                'remaining': (subscription.quotas.ai_enhancements - subscription.current_ai_enhancement_count) if subscription.quotas.ai_enhancements != -1 else -1,
                'quota': subscription.quotas.ai_enhancements
            }
        else:
            if subscription.quotas.ai_enhancements == 0:
                return {
                    'allowed': False,
                    'reason': 'AI enhancement not available in FREE tier',
                    'upgrade_required': True,
                    'current_tier': subscription.subscription_tier.value
                }
            else:
                return {
                    'allowed': False,
                    'reason': f'Monthly AI enhancement limit reached ({subscription.quotas.ai_enhancements})',
                    'upgrade_required': False,
                    'current_tier': subscription.subscription_tier.value
                }
    
    def record_pulse_usage(self, user_id: str) -> bool:
        """
        Record pulse usage for billing cycle
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            bool: Success status
        """
        try:
            # Increment usage counter
            response = self.dynamodb.update_item(
                TableName=self.table_name,
                Key={
                    'PK': {'S': f'USER#{user_id}'},
                    'SK': {'S': 'SUBSCRIPTION'}
                },
                UpdateExpression='ADD current_pulse_count :inc SET updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':inc': {'N': '1'},
                    ':timestamp': {'S': datetime.now(timezone.utc).isoformat()}
                },
                ReturnValues='UPDATED_NEW'
            )
            
            logger.info(f"Recorded pulse usage for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording pulse usage for user {user_id}: {str(e)}")
            return False
    
    def record_ai_usage(self, user_id: str, cost_cents: float = 0.0) -> bool:
        """
        Record AI enhancement usage and cost
        
        Args:
            user_id: Unique user identifier  
            cost_cents: Cost in cents for the AI enhancement
            
        Returns:
            bool: Success status
        """
        try:
            # Increment AI usage counter and add cost
            response = self.dynamodb.update_item(
                TableName=self.table_name,
                Key={
                    'PK': {'S': f'USER#{user_id}'},
                    'SK': {'S': 'SUBSCRIPTION'}
                },
                UpdateExpression='ADD current_ai_enhancement_count :inc, total_ai_cost_cents :cost SET updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':inc': {'N': '1'},
                    ':cost': {'N': str(cost_cents)},
                    ':timestamp': {'S': datetime.now(timezone.utc).isoformat()}
                },
                ReturnValues='UPDATED_NEW'
            )
            
            logger.info(f"Recorded AI usage for user {user_id}, cost: {cost_cents} cents")
            return True
            
        except Exception as e:
            logger.error(f"Error recording AI usage for user {user_id}: {str(e)}")
            return False
    
    def upgrade_subscription(self, user_id: str, new_tier: SubscriptionTier, stripe_subscription_id: str = None) -> bool:
        """
        Upgrade user subscription tier
        
        Args:
            user_id: Unique user identifier
            new_tier: New subscription tier
            stripe_subscription_id: Stripe subscription ID
            
        Returns:
            bool: Success status
        """
        try:
            update_expression = 'SET subscription_tier = :tier, updated_at = :timestamp'
            expression_values = {
                ':tier': {'S': new_tier.value},
                ':timestamp': {'S': datetime.now(timezone.utc).isoformat()}
            }
            
            if stripe_subscription_id:
                update_expression += ', stripe_subscription_id = :stripe_id'
                expression_values[':stripe_id'] = {'S': stripe_subscription_id}
            
            self.dynamodb.update_item(
                TableName=self.table_name,
                Key={
                    'PK': {'S': f'USER#{user_id}'},
                    'SK': {'S': 'SUBSCRIPTION'}
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            logger.info(f"Upgraded subscription for user {user_id} to {new_tier.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error upgrading subscription for user {user_id}: {str(e)}")
            return False
    
    def get_usage_analytics(self, user_id: str) -> Dict[str, Any]:
        """
        Get usage analytics for user (for dashboard)
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Dict with usage analytics
        """
        subscription = self.get_or_create_subscription(user_id)
        
        if not subscription:
            return {'error': 'Subscription not found'}
        
        # Calculate usage percentages
        pulse_usage_pct = (subscription.current_pulse_count / subscription.quotas.monthly_pulses * 100) if subscription.quotas.monthly_pulses > 0 else 0
        ai_usage_pct = (subscription.current_ai_enhancement_count / subscription.quotas.ai_enhancements * 100) if subscription.quotas.ai_enhancements > 0 else 0
        
        # Days remaining in billing cycle
        days_remaining = (subscription.billing_cycle_end - datetime.now(timezone.utc)).days
        
        return {
            'subscription_tier': subscription.subscription_tier.value,
            'subscription_status': subscription.subscription_status.value,
            'billing_cycle': {
                'start': subscription.billing_cycle_start.isoformat(),
                'end': subscription.billing_cycle_end.isoformat(),
                'days_remaining': max(0, days_remaining)
            },
            'usage': {
                'pulses': {
                    'used': subscription.current_pulse_count,
                    'quota': subscription.quotas.monthly_pulses,
                    'percentage': min(100, pulse_usage_pct),
                    'unlimited': subscription.quotas.monthly_pulses == -1
                },
                'ai_enhancements': {
                    'used': subscription.current_ai_enhancement_count,
                    'quota': subscription.quotas.ai_enhancements, 
                    'percentage': min(100, ai_usage_pct),
                    'unlimited': subscription.quotas.ai_enhancements == -1
                },
                'ai_cost_cents': subscription.total_ai_cost_cents
            },
            'features': {
                'advanced_analytics': subscription.quotas.advanced_analytics,
                'export_enabled': subscription.quotas.export_enabled,
                'priority_processing': subscription.quotas.priority_processing,
                'custom_prompts': subscription.quotas.custom_prompts,
                'team_workspaces': subscription.quotas.team_workspaces
            }
        }