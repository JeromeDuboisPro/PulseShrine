"""
Authentication utilities for extracting user information from API Gateway events.
"""
from typing import Dict, Any, Optional
from aws_lambda_powertools import Logger

logger = Logger()


def extract_user_id_from_event(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract user_id from API Gateway event context (Cognito JWT).
    
    When API Gateway uses Cognito authorization, it automatically validates
    the JWT token and provides user claims in the request context.
    
    Args:
        event: API Gateway event dictionary
        
    Returns:
        User ID (sub claim) from the JWT token, or None if not found
    """
    try:
        # API Gateway adds Cognito claims to requestContext.authorizer.claims
        request_context = event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {})
        claims = authorizer.get("claims", {})
        
        # The 'sub' claim contains the unique user identifier
        user_id = claims.get("sub")
        
        if user_id:
            logger.debug(f"Successfully extracted user_id: {user_id}")
            return user_id
        else:
            logger.warning("No user_id found in JWT claims")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting user_id from event: {e}")
        return None


def extract_user_email_from_event(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract user email from API Gateway event context (Cognito JWT).
    
    Args:
        event: API Gateway event dictionary
        
    Returns:
        User email from the JWT token, or None if not found
    """
    try:
        request_context = event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {})
        claims = authorizer.get("claims", {})
        
        # Email is stored in the 'email' claim
        email = claims.get("email")
        
        if email:
            logger.debug(f"Successfully extracted email: {email}")
            return email
        else:
            logger.warning("No email found in JWT claims")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting email from event: {e}")
        return None


def get_all_user_claims(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract all user claims from API Gateway event context.
    
    Useful for debugging or when you need access to all claims.
    
    Args:
        event: API Gateway event dictionary
        
    Returns:
        Dictionary of all JWT claims
    """
    try:
        request_context = event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {})
        claims = authorizer.get("claims", {})
        
        logger.debug(f"All user claims: {claims}")
        return claims
        
    except Exception as e:
        logger.error(f"Error extracting claims from event: {e}")
        return {}


def validate_user_access(event: Dict[str, Any], required_user_id: str = None) -> bool:
    """
    Validate that the authenticated user has access to perform this operation.
    
    Args:
        event: API Gateway event dictionary
        required_user_id: If provided, check that the authenticated user matches this ID
        
    Returns:
        True if user is properly authenticated and authorized
    """
    try:
        authenticated_user_id = extract_user_id_from_event(event)
        
        if not authenticated_user_id:
            logger.warning("No authenticated user found")
            return False
            
        if required_user_id and authenticated_user_id != required_user_id:
            logger.warning(f"User {authenticated_user_id} attempted to access resource for user {required_user_id}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error validating user access: {e}")
        return False