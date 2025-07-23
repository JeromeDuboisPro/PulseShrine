"""
Centralized subscription tier configuration constants.

This module defines all subscription tier quotas and limits in one place 
to follow DRY (Don't Repeat Yourself) principles.
"""

# Free Tier Configuration
FREE_MONTHLY_PULSES = 100  # Generous free tier to build habits
FREE_AI_SAMPLES = 3  # AI samples per month to taste the power
FREE_TEAM_WORKSPACES = 1

# Pro Tier Configuration  
PRO_MONTHLY_PULSES = -1  # Unlimited
PRO_AI_ENHANCEMENTS = -1  # Unlimited
PRO_TEAM_WORKSPACES = 1
PRO_PRICE_USD = 9.99

# Enterprise Tier Configuration
ENTERPRISE_MONTHLY_PULSES = -1  # Unlimited
ENTERPRISE_AI_ENHANCEMENTS = -1  # Unlimited
ENTERPRISE_TEAM_WORKSPACES = 10
ENTERPRISE_PRICE_USD = 29.99

# Pricing Configuration
TRIAL_DAYS = 14
CURRENCY = "USD"
CURRENCY_SYMBOL = "$"

# Feature descriptions for marketing
FREE_DESCRIPTION = "Perfect for trying out PulseShrine with AI samples"
PRO_DESCRIPTION = "For productive individuals who want AI-powered insights"
ENTERPRISE_DESCRIPTION = "For teams and organizations with advanced needs"