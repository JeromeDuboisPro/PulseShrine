"""
Quota Middleware for PulseShrine API Endpoints

Intercepts API calls to enforce subscription quotas before processing.
"""

import json
from functools import wraps
from typing import Dict, Any, Callable, Optional
from aws_lambda_powertools import Logger

from ..services.subscription_service import SubscriptionService

logger = Logger()


class QuotaExceededException(Exception):
    """Exception raised when user quota is exceeded"""
    def __init__(self, message: str, quota_info: dict = None):
        self.message = message
        self.quota_info = quota_info or {}
        super().__init__(self.message)


def extract_user_id_from_event(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract user_id from Lambda event
    
    Supports both API Gateway and direct invocation patterns.
    For Cognito authentication, user_id is in requestContext.
    
    Args:
        event: Lambda event dict
        
    Returns:
        str: User ID or None if not found
    """
    try:
        # Try API Gateway with Cognito authorizer
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            authorizer = event['requestContext']['authorizer']
            # Cognito user pool authorizer
            if 'claims' in authorizer and 'sub' in authorizer['claims']:
                return authorizer['claims']['sub']
        
        # Try body for direct invocation
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
            
            if 'user_id' in body:
                return body['user_id']
        
        # Try direct event attributes
        if 'user_id' in event:
            return event['user_id']
            
        return None
        
    except Exception as e:
        logger.error(f"Error extracting user_id from event: {str(e)}")
        return None


def quota_check(quota_type: str, table_name: str = None):
    """
    Decorator to check user quotas before executing Lambda function
    
    Args:
        quota_type: 'pulse' or 'ai' - type of quota to check
        table_name: Optional DynamoDB table name (uses env var if not provided)
        
    Usage:
        @quota_check('pulse')
        def start_pulse_handler(event, context):
            # Function will only run if user has pulse quota
            pass
    """
    def decorator(handler_func: Callable) -> Callable:
        @wraps(handler_func)
        def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
            try:
                # Extract user ID from event
                user_id = extract_user_id_from_event(event)
                if not user_id:
                    logger.warning("No user_id found in event, skipping quota check")
                    return handler_func(event, context)
                
                # Initialize subscription service
                import os
                subscription_table = table_name or os.environ.get('SUBSCRIPTION_TABLE_NAME', 'ps-subscriptions-dev')
                subscription_service = SubscriptionService(subscription_table)
                
                # Check quota based on type
                if quota_type == 'pulse':
                    quota_result = subscription_service.check_pulse_quota(user_id)
                elif quota_type == 'ai':
                    quota_result = subscription_service.check_ai_quota(user_id)
                else:
                    logger.error(f"Unknown quota type: {quota_type}")
                    return handler_func(event, context)
                
                # If quota exceeded, return error response
                if not quota_result['allowed']:
                    error_response = {
                        'statusCode': 429,  # Too Many Requests
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'error': 'Quota exceeded',
                            'message': quota_result['reason'],
                            'quota_info': quota_result,
                            'upgrade_url': '/subscribe' if quota_result.get('upgrade_required') else None
                        })
                    }
                    
                    logger.warning(f"Quota exceeded for user {user_id}: {quota_result['reason']}")
                    return error_response
                
                # Quota OK, proceed with handler
                logger.info(f"Quota check passed for user {user_id}, quota_type: {quota_type}")
                
                # Execute original handler
                result = handler_func(event, context)
                
                # If handler succeeded, record usage
                if isinstance(result, dict) and result.get('statusCode') == 200:
                    if quota_type == 'pulse':
                        subscription_service.record_pulse_usage(user_id)
                        logger.info(f"Recorded pulse usage for user {user_id}")
                    elif quota_type == 'ai':
                        # For AI usage, we'll record in the AI handler with cost
                        pass
                
                return result
                
            except Exception as e:
                logger.error(f"Error in quota middleware: {str(e)}")
                # On middleware error, allow request to proceed
                return handler_func(event, context)
        
        return wrapper
    return decorator


def record_ai_usage(user_id: str, cost_cents: float, table_name: str = None) -> bool:
    """
    Utility function to record AI usage with cost tracking
    
    Args:
        user_id: User identifier
        cost_cents: Cost of AI operation in cents
        table_name: Optional DynamoDB table name
        
    Returns:
        bool: Success status
    """
    try:
        import os
        subscription_table = table_name or os.environ.get('SUBSCRIPTION_TABLE_NAME', 'ps-subscriptions-dev')
        subscription_service = SubscriptionService(subscription_table)
        
        return subscription_service.record_ai_usage(user_id, cost_cents)
        
    except Exception as e:
        logger.error(f"Error recording AI usage: {str(e)}")
        return False


def get_user_subscription_info(user_id: str, table_name: str = None) -> Dict[str, Any]:
    """
    Utility function to get user subscription information for API responses
    
    Args:
        user_id: User identifier
        table_name: Optional DynamoDB table name
        
    Returns:
        Dict with subscription info
    """
    try:
        import os
        subscription_table = table_name or os.environ.get('SUBSCRIPTION_TABLE_NAME', 'ps-subscriptions-dev')
        subscription_service = SubscriptionService(subscription_table)
        
        return subscription_service.get_usage_analytics(user_id)
        
    except Exception as e:
        logger.error(f"Error getting subscription info: {str(e)}")
        return {'error': str(e)}


# Enhanced response helper that includes quota info
def create_api_response(
    status_code: int,
    body: Dict[str, Any],
    user_id: str = None,
    include_quota: bool = False,
    table_name: str = None
) -> Dict[str, Any]:
    """
    Create standardized API response with optional quota information
    
    Args:
        status_code: HTTP status code
        body: Response body dict
        user_id: Optional user ID to include quota info
        include_quota: Whether to include quota information
        table_name: Optional DynamoDB table name
        
    Returns:
        Dict: API Gateway response format
    """
    response_body = body.copy()
    
    # Add quota information if requested and user_id provided
    if include_quota and user_id:
        try:
            quota_info = get_user_subscription_info(user_id, table_name)
            response_body['subscription'] = quota_info
        except Exception as e:
            logger.error(f"Error adding quota info to response: {str(e)}")
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(response_body, default=str)
    }