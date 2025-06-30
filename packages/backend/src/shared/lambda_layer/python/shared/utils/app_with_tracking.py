"""Wrapper for Lambda handlers with AI tracking integration."""
import functools
from typing import Any, Dict, Callable
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()


def app_with_tracking(handler_func: Callable, tracking_integration: Any) -> Callable:
    """
    Wrap a Lambda handler function with AI tracking error handling.
    
    Args:
        handler_func: The original Lambda handler function
        tracking_integration: AITrackingIntegration instance for error tracking
        
    Returns:
        Wrapped handler function that tracks errors
    """
    
    @functools.wraps(handler_func)
    def wrapped_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
        try:
            # Call the original handler
            return handler_func(event, context)
        except Exception as e:
            # Track the error using tracking integration
            try:
                # Extract user_id from event if available for error tracking
                user_id = "unknown"
                pulse_id = "unknown"
                
                # Try to extract user context from different event types
                if isinstance(event, dict):
                    # For DynamoDB stream events
                    if "Records" in event:
                        for record in event["Records"]:
                            if "dynamodb" in record and "NewImage" in record["dynamodb"]:
                                new_image = record["dynamodb"]["NewImage"]
                                if "user_id" in new_image:
                                    user_id = new_image["user_id"].get("S", "unknown")
                                if "pulse_id" in new_image:
                                    pulse_id = new_image["pulse_id"].get("S", "unknown")
                                break
                    
                    # For API Gateway events
                    elif "body" in event:
                        import json
                        try:
                            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
                            user_id = body.get("user_id", "unknown")
                            pulse_id = body.get("pulse_id", "unknown")
                        except:
                            pass
                
                # Track the error
                tracking_integration.track_error(
                    user_id=user_id,
                    pulse_id=pulse_id,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    handler_name=handler_func.__name__,
                    metadata={
                        "event_type": type(event).__name__,
                        "context": {
                            "function_name": context.function_name if hasattr(context, 'function_name') else 'unknown',
                            "request_id": context.aws_request_id if hasattr(context, 'aws_request_id') else 'unknown',
                        }
                    }
                )
                logger.error(f"Error tracked for handler {handler_func.__name__}: {e}")
                
            except Exception as tracking_error:
                # If tracking itself fails, just log it but don't let it break the original error
                logger.warning(f"Failed to track error in {handler_func.__name__}: {tracking_error}")
            
            # Re-raise the original exception
            raise e
    
    return wrapped_handler