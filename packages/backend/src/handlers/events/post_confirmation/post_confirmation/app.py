import os
from typing import Dict, Any
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

# Import shared services
try:
    from shared.services.user_service import UserService
    from shared.services.ai_budget_service import AIBudgetService
except ImportError:
    # Fallback imports for local testing
    import sys
    import os
    
    sys.path.append(
        os.path.join(os.path.dirname(__file__), "../../shared/lambda_layer/python")
    )
    from shared.services.user_service import UserService
    from shared.services.ai_budget_service import AIBudgetService

# Initialize the logger
logger = Logger()

# Initialize services
users_table_name = os.environ.get("USERS_TABLE_NAME", "ps-users")
ai_usage_table_name = os.environ.get("AI_USAGE_TRACKING_TABLE_NAME", "ps-ai-usage-tracking")

user_service = UserService(users_table_name)
ai_budget_service = AIBudgetService(ai_usage_table_name)


def extract_user_info(event: Dict[str, Any]) -> Dict[str, str]:
    """Extract user information from Cognito post-confirmation event."""
    try:
        # Extract user details from Cognito event
        user_id = event["request"]["userAttributes"]["sub"]
        email = event["request"]["userAttributes"]["email"]
        username = event["userName"]  # This is the email used as username
        
        logger.info(f"Processing post-confirmation for user: {user_id}, email: {email}")
        
        return {
            "user_id": user_id,
            "email": email,
            "username": username
        }
    except KeyError as e:
        logger.error(f"Missing required user attribute: {e}")
        raise ValueError(f"Invalid Cognito event structure: missing {e}")


def initialize_user_profile(user_info: Dict[str, str]) -> bool:
    """Initialize user profile in DynamoDB."""
    try:
        user_id = user_info["user_id"]
        email = user_info["email"]
        
        # Check if user already exists (safety check)
        existing_profile = user_service.get_user_profile(user_id)
        
        # If user already exists and has stats, don't overwrite
        if existing_profile.get("stats", {}).get("total_pulses", 0) > 0:
            logger.info(f"User {user_id} already has activity, skipping initialization")
            return True
        
        # Create/update user profile with additional Cognito information
        now_iso = user_service.table.meta.client._make_api_call(
            'GetItem', {'TableName': users_table_name, 'Key': {'pk': {'S': 'dummy'}}}
        )  # Just to get proper ISO format - will use datetime in actual implementation
        
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        
        # Enhanced profile with Cognito data
        enhanced_profile = {
            "PK": f"USER#{user_id}",
            "SK": "PROFILE",
            "user_id": user_id,
            "email": email,
            "username": user_info["username"],
            "plan": "free",
            "plan_expires": None,
            "created_at": now,
            "updated_at": now,
            "cognito_confirmed_at": now,
            "preferences": {
                "notifications": True,
                "daily_summary": True,
                "ai_enhancement_priority": "balanced",  # Options: aggressive, balanced, conservative
            },
            "stats": {
                "total_pulses": 0,
                "total_ai_enhancements": 0,
                "member_since": now,
                "registration_source": "cognito_signup",
            },
            "ai_credits": {
                "total_earned": 0,
                "total_used": 0,
                "current_balance": 0,
            }
        }
        
        # Save enhanced profile
        user_service.table.put_item(Item=enhanced_profile)
        logger.info(f"Created enhanced user profile for {user_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error initializing user profile: {e}")
        return False


def initialize_ai_usage_tracking(user_id: str) -> bool:
    """Initialize AI usage tracking for the new user."""
    try:
        # Create initial daily usage record
        daily_usage = ai_budget_service.get_or_create_daily_usage(user_id)
        
        if daily_usage:
            logger.info(f"AI usage tracking initialized for user {user_id}")
            return True
        else:
            logger.warning(f"Failed to initialize AI usage tracking for user {user_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error initializing AI usage tracking: {e}")
        return False


@logger.inject_lambda_context
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Cognito Post-Confirmation Lambda handler.
    
    Automatically initializes new users in DynamoDB when they complete
    Cognito registration and email verification.
    
    Input: Cognito Post-Confirmation trigger event
    Output: Same event (required by Cognito)
    """
    logger.info("Post-confirmation Lambda triggered", extra={
        "event_source": event.get("eventName", "unknown"),
        "user_pool_id": event.get("userPoolId", "unknown")
    })
    
    try:
        # Extract user information from Cognito event
        user_info = extract_user_info(event)
        user_id = user_info["user_id"]
        
        # Initialize user profile in DynamoDB
        profile_success = initialize_user_profile(user_info)
        if not profile_success:
            logger.error(f"Failed to initialize user profile for {user_id}")
            # Don't fail the Cognito flow, but log the error
        
        # Initialize AI usage tracking
        ai_tracking_success = initialize_ai_usage_tracking(user_id)
        if not ai_tracking_success:
            logger.error(f"Failed to initialize AI tracking for {user_id}")
            # Don't fail the Cognito flow, but log the error
        
        # Log successful initialization
        if profile_success and ai_tracking_success:
            logger.info(f"Successfully initialized user {user_id} in DynamoDB")
        else:
            logger.warning(f"Partial initialization for user {user_id}: profile={profile_success}, ai_tracking={ai_tracking_success}")
        
        # IMPORTANT: Return the original event unchanged
        # Cognito requires this for the trigger to complete successfully
        return event
        
    except Exception as e:
        logger.exception("Error in post-confirmation handler")
        
        # IMPORTANT: Don't raise exceptions from Cognito triggers
        # This would prevent user registration from completing
        # Instead, log errors and return the event to allow registration to proceed
        logger.error(f"Post-confirmation failed but allowing registration to proceed: {e}")
        return event