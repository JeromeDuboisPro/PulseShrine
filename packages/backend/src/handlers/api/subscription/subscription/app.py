import os
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, UnauthorizedError
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError
from typing import Any, Dict

from shared.utils.auth import extract_user_id_from_event
from shared.services.subscription_service import SubscriptionService
from shared.models.pulse import SubscriptionTier
from shared.constants.subscription_tiers import (
    FREE_MONTHLY_PULSES, FREE_AI_SAMPLES, FREE_DESCRIPTION,
    PRO_MONTHLY_PULSES, PRO_AI_ENHANCEMENTS, PRO_PRICE_USD, PRO_DESCRIPTION,
    ENTERPRISE_MONTHLY_PULSES, ENTERPRISE_AI_ENHANCEMENTS, ENTERPRISE_PRICE_USD, ENTERPRISE_DESCRIPTION,
    CURRENCY, CURRENCY_SYMBOL, TRIAL_DAYS
)

# Initialize the logger
logger = Logger()

# Retrieve environment variables
SUBSCRIPTION_TABLE_NAME = os.environ.get("SUBSCRIPTION_TABLE_NAME", "ps-subscriptions-dev")

# Configure CORS
cors_config = CORSConfig(
    allow_origin="*",  # In production, specify your actual domain
)

# Initialize the APIGatewayRestResolver
app = APIGatewayRestResolver(cors=cors_config)


@app.get("/subscription")
def get_subscription() -> Dict[str, Any]:
    """
    Get user's current subscription information and usage analytics
    """
    # Extract user_id from JWT token
    user_id = extract_user_id_from_event(app.current_event.raw_event)
    if not user_id:
        logger.error("No user_id found in JWT token")
        raise UnauthorizedError("Authentication required")
    
    try:
        subscription_service = SubscriptionService(SUBSCRIPTION_TABLE_NAME)
        analytics = subscription_service.get_usage_analytics(user_id)
        
        if 'error' in analytics:
            logger.error(f"Error getting analytics for user {user_id}: {analytics['error']}")
            raise BadRequestError(f"Failed to retrieve subscription: {analytics['error']}")
        
        return analytics
        
    except Exception as exc:
        logger.error(f"Unexpected error getting subscription for {user_id}: {str(exc)}")
        raise BadRequestError("Failed to retrieve subscription information")


@app.post("/subscription/upgrade")
def upgrade_subscription() -> Dict[str, Any]:
    """
    Upgrade user's subscription tier
    Expected body: {"tier": "pro|enterprise", "stripe_subscription_id": "sub_xxx"}
    """
    # Extract user_id from JWT token
    user_id = extract_user_id_from_event(app.current_event.raw_event)
    if not user_id:
        logger.error("No user_id found in JWT token")
        raise UnauthorizedError("Authentication required")
    
    try:
        body = app.current_event.json_body
        
        # Validate required fields
        if 'tier' not in body:
            raise BadRequestError("Missing required field: tier")
        
        # Validate tier value
        tier_value = body['tier'].lower()
        if tier_value not in ['pro', 'enterprise']:
            raise BadRequestError("Invalid tier. Must be 'pro' or 'enterprise'")
        
        new_tier = SubscriptionTier.PRO if tier_value == 'pro' else SubscriptionTier.ENTERPRISE
        stripe_subscription_id = body.get('stripe_subscription_id')
        
    except (ValidationError, TypeError, ValueError, KeyError) as exc:
        logger.error(f"Validation error: {str(exc)}")
        raise BadRequestError(f"Invalid request: {str(exc)}")
    
    try:
        subscription_service = SubscriptionService(SUBSCRIPTION_TABLE_NAME)
        
        # Upgrade the subscription
        success = subscription_service.upgrade_subscription(
            user_id, 
            new_tier, 
            stripe_subscription_id
        )
        
        if not success:
            raise BadRequestError("Failed to upgrade subscription")
        
        # Return updated subscription info
        updated_analytics = subscription_service.get_usage_analytics(user_id)
        
        return {
            'success': True,
            'message': f'Successfully upgraded to {new_tier.value}',
            'subscription': updated_analytics
        }
        
    except Exception as exc:
        logger.error(f"Error upgrading subscription for {user_id}: {str(exc)}")
        raise BadRequestError("Failed to upgrade subscription")


@app.get("/subscription/pricing")
def get_pricing() -> Dict[str, Any]:
    """
    Get pricing tiers and feature comparison
    """
    return {
        'tiers': {
            'free': {
                'name': 'Free',
                'price': 0,
                'currency': CURRENCY,
                'interval': 'month',
                'features': {
                    'monthly_pulses': FREE_MONTHLY_PULSES,
                    'ai_enhancements': FREE_AI_SAMPLES,
                    'advanced_analytics': False,
                    'export_enabled': False,
                    'priority_processing': False,
                    'custom_prompts': False,
                    'team_workspaces': 1
                },
                'description': FREE_DESCRIPTION
            },
            'pro': {
                'name': 'Pro',
                'price': PRO_PRICE_USD,
                'currency': CURRENCY,
                'interval': 'month',
                'features': {
                    'monthly_pulses': PRO_MONTHLY_PULSES,
                    'ai_enhancements': PRO_AI_ENHANCEMENTS,
                    'advanced_analytics': True,
                    'export_enabled': True,
                    'priority_processing': True,
                    'custom_prompts': False,
                    'team_workspaces': 1
                },
                'description': PRO_DESCRIPTION,
                'popular': True
            },
            'enterprise': {
                'name': 'Enterprise',
                'price': ENTERPRISE_PRICE_USD,
                'currency': CURRENCY,
                'interval': 'month',
                'features': {
                    'monthly_pulses': ENTERPRISE_MONTHLY_PULSES,
                    'ai_enhancements': ENTERPRISE_AI_ENHANCEMENTS,
                    'advanced_analytics': True,
                    'export_enabled': True,
                    'priority_processing': True,
                    'custom_prompts': True,
                    'team_workspaces': 10
                },
                'description': ENTERPRISE_DESCRIPTION
            }
        },
        'currency_symbol': CURRENCY_SYMBOL,
        'trial_days': TRIAL_DAYS
    }


@app.post("/subscription/create-customer")
def create_stripe_customer() -> Dict[str, Any]:
    """
    Create Stripe customer for user (placeholder for Stripe integration)
    Expected body: {"email": "user@example.com"}
    """
    # Extract user_id from JWT token
    user_id = extract_user_id_from_event(app.current_event.raw_event)
    if not user_id:
        logger.error("No user_id found in JWT token")
        raise UnauthorizedError("Authentication required")
    
    try:
        body = app.current_event.json_body
        email = body.get('email')
        
        if not email:
            raise BadRequestError("Email is required")
        
        # TODO: Integrate with Stripe API
        # For now, return mock customer ID
        mock_customer_id = f"cus_mock_{user_id[:8]}"
        
        # Update subscription with Stripe customer ID
        subscription_service = SubscriptionService(SUBSCRIPTION_TABLE_NAME)
        subscription = subscription_service.get_or_create_subscription(user_id, email)
        
        return {
            'success': True,
            'customer_id': mock_customer_id,
            'message': 'Customer created successfully'
        }
        
    except Exception as exc:
        logger.error(f"Error creating customer for {user_id}: {str(exc)}")
        raise BadRequestError("Failed to create customer")


def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda function handler.
    """
    return app.resolve(event, context)