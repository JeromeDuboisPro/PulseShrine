"""
AI Budget and Usage Tracking Service

Handles daily/monthly budget tracking, AI credits, and gamification rewards.
"""

import boto3
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, List, Optional
from decimal import Decimal
from aws_lambda_powertools import Logger

from .user_service import UserService

logger = Logger()

# Budget tiers configuration - Updated pricing strategy
BUDGET_TIERS = {
    "free": {
        "daily_base_cents": 5,   # 5¢ daily (≈2-5 AI enhancements)
        "daily_bonus_credits": 0,  # No bonus credits for free tier
        "monthly_cap_cents": 30,   # 30¢ monthly cap - hook users with AI taste
    },
    "premium": {
        "daily_base_cents": 18,    # 18¢ daily (≈7-20 AI enhancements)
        "daily_bonus_credits": 2,  # 2¢ bonus credits
        "monthly_cap_cents": 375,  # $3.75 monthly cap (75% of $5 revenue)
    },
    "unlimited": {
        "daily_base_cents": 75,    # 75¢ daily (≈25-100 AI enhancements)
        "daily_bonus_credits": 25, # 25¢ bonus credits ($1.00 total daily)
        "monthly_cap_cents": 1000, # $10.00 monthly cap (50% of $20 revenue)
    },
}

# Reward triggers for gamification
REWARD_TRIGGERS = {
    "streak_3_days": {"ai_credits": 5, "message": "🔥 3-day streak! Bonus AI credits!"},
    "deep_reflection": {
        "ai_credits": 2,
        "message": "📝 Thoughtful reflection detected!",
    },
    "long_session": {"ai_credits": 3, "message": "⏰ 2+ hour session! Extra AI boost!"},
    "weekly_warrior": {
        "ai_credits": 10,
        "message": "💪 5+ pulses this week! You're on fire!",
    },
    "breakthrough_words": {
        "ai_credits": 1,
        "message": "🚀 Innovation detected! AI bonus!",
    },
    "first_ai_enhancement": {
        "ai_credits": 5,
        "message": "🤖 Welcome to AI enhancement!",
    },
    "consistency_master": {
        "ai_credits": 8,
        "message": "📅 7-day streak! Consistency master!",
    },
}

# Achievement definitions
ACHIEVEMENTS = {
    "ai_apprentice": {
        "name": "🤖 AI Apprentice",
        "requirement": "first_ai_enhancement",
    },
    "ai_enthusiast": {"name": "🧠 AI Enthusiast", "requirement": "10_ai_enhancements"},
    "ai_master": {"name": "🚀 AI Master", "requirement": "50_ai_enhancements"},
    "research_pioneer": {
        "name": "🔬 Research Pioneer",
        "requirement": "breakthrough_session",
    },
    "endurance_champion": {
        "name": "⏰ Endurance Champion",
        "requirement": "marathon_session",
    },
    "consistency_king": {"name": "👑 Consistency King", "requirement": "7_day_streak"},
    "deep_thinker": {"name": "🧐 Deep Thinker", "requirement": "long_reflections"},
}


class AIBudgetService:
    def __init__(self, table_name: str, user_service: Optional[UserService] = None):
        self.table_name = table_name
        self.user_service = user_service or UserService()
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

    def get_today_date(self) -> str:
        """Get today's date in YYYY-MM-DD format (UTC)"""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def get_current_month(self) -> str:
        """Get current month in YYYY-MM format (UTC)"""
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def get_user_tier(self, user_id: str) -> str:
        """Get user's tier (free/premium/unlimited)"""
        try:
            return self.user_service.get_user_plan(user_id)
        except Exception as e:
            logger.error(f"Error getting user tier for {user_id}: {e}")
            return "free"  # Safe fallback

    def get_or_create_daily_usage(
        self, user_id: str, date: str = None
    ) -> Dict[str, Any]:
        """Get or create daily usage record for user"""
        if not date:
            date = self.get_today_date()

        try:
            response = self.table.get_item(Key={"PK": f"USER#{user_id}", "SK": f"DAILY#{date}"})

            if "Item" in response:
                # Convert Decimals to floats/ints for easier handling
                item = response["Item"]
                return {
                    "user_id": item["user_id"],
                    "date": item["date"],
                    "daily_cost_cents": int(item.get("daily_cost_cents", 0)),
                    "daily_ai_credits": int(item.get("daily_ai_credits", 0)),
                    "daily_pulses_enhanced": int(item.get("daily_pulses_enhanced", 0)),
                    "monthly_cost_cents": int(item.get("monthly_cost_cents", 0)),
                    "monthly_ai_credits": int(item.get("monthly_ai_credits", 0)),
                    "user_tier": item.get("user_tier", "free"),
                    "streak_days": int(item.get("streak_days", 0)),
                    "achievements": item.get("achievements", []),
                    "last_gift_date": item.get("last_gift_date", ""),
                    "total_ai_enhancements": int(item.get("total_ai_enhancements", 0)),
                }
            else:
                # Create new record
                user_tier = self.get_user_tier(user_id)
                tier_config = BUDGET_TIERS[user_tier]

                new_record = {
                    "user_id": user_id,
                    "date": date,
                    "daily_cost_cents": 0,
                    "daily_ai_credits": tier_config[
                        "daily_bonus_credits"
                    ],  # Start with bonus credits
                    "daily_pulses_enhanced": 0,
                    "monthly_cost_cents": 0,
                    "monthly_ai_credits": tier_config["daily_bonus_credits"],
                    "user_tier": user_tier,
                    "streak_days": 0,
                    "achievements": [],
                    "last_gift_date": "",
                    "total_ai_enhancements": 0,
                    "month": self.get_current_month(),
                    "ttl": int(
                        (datetime.now(timezone.utc) + timedelta(days=90)).timestamp()
                    ),  # 90 day retention
                }

                # Convert to new table format
                new_record_item = {
                    "PK": f"USER#{user_id}",
                    "SK": f"DAILY#{date}",
                    **new_record
                }
                self.table.put_item(Item=new_record_item)
                return new_record

        except Exception as e:
            logger.error(f"Error getting daily usage for user {user_id}: {e}")
            # Return default values on error
            user_tier = self.get_user_tier(user_id)
            tier_config = BUDGET_TIERS[user_tier]
            return {
                "user_id": user_id,
                "date": date,
                "daily_cost_cents": 0,
                "daily_ai_credits": tier_config["daily_bonus_credits"],
                "daily_pulses_enhanced": 0,
                "monthly_cost_cents": 0,
                "monthly_ai_credits": tier_config["daily_bonus_credits"],
                "user_tier": user_tier,
                "streak_days": 0,
                "achievements": [],
                "last_gift_date": "",
                "total_ai_enhancements": 0,
            }

    def get_user_budget(self, user_id: str) -> Dict[str, int]:
        """Get user's budget configuration based on tier"""
        usage = self.get_or_create_daily_usage(user_id)
        tier_config = BUDGET_TIERS[usage["user_tier"]]

        return {
            "daily_base_cents": tier_config["daily_base_cents"],
            "daily_bonus_credits": usage["daily_ai_credits"],
            "monthly_cap_cents": tier_config["monthly_cap_cents"],
            "total_daily_available": tier_config["daily_base_cents"]
            + usage["daily_ai_credits"],
        }

    def can_afford_enhancement(
        self, user_id: str, estimated_cost_cents: float
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Check if user can afford AI enhancement"""
        usage = self.get_or_create_daily_usage(user_id)
        budget = self.get_user_budget(user_id)

        # Check monthly cap first
        if usage["monthly_cost_cents"] >= budget["monthly_cap_cents"]:
            return False, "Monthly budget exceeded", usage

        # Check if adding this cost would exceed monthly cap
        if (
            usage["monthly_cost_cents"] + estimated_cost_cents
            > budget["monthly_cap_cents"]
        ):
            return False, "Would exceed monthly budget", usage

        # Check daily budget (base + credits)
        total_available = budget["total_daily_available"]
        if usage["daily_cost_cents"] + estimated_cost_cents > total_available:
            return False, "Daily budget exceeded", usage

        return True, "Budget available", usage

    def record_ai_enhancement(
        self, user_id: str, cost_cents: float, pulse_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Record AI enhancement usage and trigger rewards"""
        try:
            date = self.get_today_date()
            month = self.get_current_month()

            # Get current usage
            usage = self.get_or_create_daily_usage(user_id, date)

            # Update usage
            new_daily_cost = usage["daily_cost_cents"] + cost_cents
            new_monthly_cost = usage["monthly_cost_cents"] + cost_cents
            new_daily_enhanced = usage["daily_pulses_enhanced"] + 1
            new_total_enhanced = usage["total_ai_enhancements"] + 1

            # Check for rewards and achievements
            rewards = self._check_rewards_and_achievements(usage, pulse_data)
            new_credits = usage["daily_ai_credits"] + sum(
                r.get("ai_credits", 0) for r in rewards
            )

            # Update record
            update_expression = """
                SET daily_cost_cents = :daily_cost,
                    daily_pulses_enhanced = :daily_enhanced,
                    monthly_cost_cents = :monthly_cost,
                    daily_ai_credits = :daily_credits,
                    total_ai_enhancements = :total_enhanced,
                    #month = :month
            """

            expression_values = {
                ":daily_cost": Decimal(str(new_daily_cost)),
                ":daily_enhanced": new_daily_enhanced,
                ":monthly_cost": Decimal(str(new_monthly_cost)),
                ":daily_credits": new_credits,
                ":total_enhanced": new_total_enhanced,
                ":month": month,
            }

            expression_names = {"#month": "month"}  # month is a reserved keyword

            # Add achievements if any
            if rewards:
                new_achievements = list(
                    set(
                        usage["achievements"]
                        + [
                            r.get("achievement")
                            for r in rewards
                            if r.get("achievement")
                        ]
                    )
                )
                update_expression += ", achievements = :achievements"
                expression_values[":achievements"] = new_achievements

            self.table.update_item(
                Key={"PK": f"USER#{user_id}", "SK": f"DAILY#{date}"},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names,
            )

            logger.info(
                f"Recorded AI enhancement for user {user_id}: {cost_cents} cents, {len(rewards)} rewards"
            )

            return {
                "success": True,
                "new_daily_cost": new_daily_cost,
                "new_monthly_cost": new_monthly_cost,
                "rewards": rewards,
                "remaining_daily_budget": self.get_user_budget(user_id)[
                    "total_daily_available"
                ]
                - new_daily_cost,
            }

        except Exception as e:
            logger.error(f"Error recording AI enhancement for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    def _check_rewards_and_achievements(
        self, usage: Dict[str, Any], pulse_data: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Check for triggered rewards and achievements"""
        rewards = []

        # First AI enhancement
        if usage["total_ai_enhancements"] == 0:
            rewards.append(
                {
                    "type": "first_ai_enhancement",
                    "ai_credits": REWARD_TRIGGERS["first_ai_enhancement"]["ai_credits"],
                    "message": REWARD_TRIGGERS["first_ai_enhancement"]["message"],
                    "achievement": "ai_apprentice",
                }
            )

        # Achievement milestones
        total_enhanced = usage["total_ai_enhancements"] + 1
        if total_enhanced == 10:
            rewards.append(
                {
                    "type": "ai_enthusiast",
                    "ai_credits": 5,
                    "message": "🧠 AI Enthusiast unlocked!",
                    "achievement": "ai_enthusiast",
                }
            )
        elif total_enhanced == 50:
            rewards.append(
                {
                    "type": "ai_master",
                    "ai_credits": 15,
                    "message": "🚀 AI Master achieved!",
                    "achievement": "ai_master",
                }
            )

        # Pulse-based rewards (if pulse data provided)
        if pulse_data:
            # Long session reward
            duration_hours = float(pulse_data.get("duration_seconds", 0)) / 3600
            if duration_hours >= 2:
                rewards.append(
                    {
                        "type": "long_session",
                        "ai_credits": REWARD_TRIGGERS["long_session"]["ai_credits"],
                        "message": REWARD_TRIGGERS["long_session"]["message"],
                    }
                )

            # Deep reflection reward
            reflection_length = len(pulse_data.get("reflection", ""))
            if reflection_length >= 200:
                rewards.append(
                    {
                        "type": "deep_reflection",
                        "ai_credits": REWARD_TRIGGERS["deep_reflection"]["ai_credits"],
                        "message": REWARD_TRIGGERS["deep_reflection"]["message"],
                    }
                )

            # Breakthrough words reward
            breakthrough_words = [
                "breakthrough",
                "innovation",
                "revolutionary",
                "novel",
                "pioneering",
                "discovery",
            ]
            content = (
                pulse_data.get("intent", "") + " " + pulse_data.get("reflection", "")
            ).lower()
            if any(word in content for word in breakthrough_words):
                rewards.append(
                    {
                        "type": "breakthrough_words",
                        "ai_credits": REWARD_TRIGGERS["breakthrough_words"][
                            "ai_credits"
                        ],
                        "message": REWARD_TRIGGERS["breakthrough_words"]["message"],
                    }
                )

        return rewards

    def get_daily_pulse_count(self, user_id: str, date: str = None) -> int:
        """Get user's pulse count for a specific date (approximation from enhanced pulses)"""
        # This is a simplified version - in production you'd query the actual pulse tables
        # For now, we'll estimate based on enhanced pulses
        usage = self.get_or_create_daily_usage(user_id, date)
        # Assume enhanced pulses are ~10-20% of total pulses
        return max(1, usage["daily_pulses_enhanced"] * 8)  # Rough estimate
