"""Cost calculation service for AI operations."""
from typing import Dict, Tuple
from aws_lambda_powertools import Logger

logger = Logger()


class AICostCalculator:
    """Service for calculating AI operation costs."""
    
    # Cost per 1000 tokens (in cents)
    # Based on AWS Bedrock pricing as of 2024
    BEDROCK_COSTS = {
        "anthropic.claude-3-haiku-20240307-v1:0": {
            "input": 0.025,  # $0.00025 per 1K input tokens
            "output": 0.125,  # $0.00125 per 1K output tokens
        },
        "anthropic.claude-3-sonnet-20240229-v1:0": {
            "input": 0.3,    # $0.003 per 1K input tokens
            "output": 1.5,   # $0.015 per 1K output tokens
        },
        "anthropic.claude-3-opus-20240229-v1:0": {
            "input": 1.5,    # $0.015 per 1K input tokens
            "output": 7.5,   # $0.075 per 1K output tokens
        },
        "us.amazon.nova-lite-v1:0": {
            "input": 0.006,  # $0.00006 per 1K input tokens
            "output": 0.024, # $0.00024 per 1K output tokens
        },
        "us.amazon.nova-micro-v1:0": {
            "input": 0.0035, # $0.000035 per 1K input tokens
            "output": 0.014, # $0.00014 per 1K output tokens
        },
        "us.amazon.nova-pro-v1:0": {
            "input": 0.08,   # $0.0008 per 1K input tokens
            "output": 0.32,  # $0.0032 per 1K output tokens
        },
    }
    
    # Regional variants of Nova models
    REGIONAL_NOVA_MODELS = {
        "eu.amazon.nova-lite-v1:0": BEDROCK_COSTS["us.amazon.nova-lite-v1:0"],
        "apac.amazon.nova-lite-v1:0": BEDROCK_COSTS["us.amazon.nova-lite-v1:0"],
        "eu.amazon.nova-micro-v1:0": BEDROCK_COSTS["us.amazon.nova-micro-v1:0"],
        "apac.amazon.nova-micro-v1:0": BEDROCK_COSTS["us.amazon.nova-micro-v1:0"],
        "eu.amazon.nova-pro-v1:0": BEDROCK_COSTS["us.amazon.nova-pro-v1:0"],
        "apac.amazon.nova-pro-v1:0": BEDROCK_COSTS["us.amazon.nova-pro-v1:0"],
    }
    
    def __init__(self):
        """Initialize calculator with all model costs."""
        self.model_costs = {**self.BEDROCK_COSTS, **self.REGIONAL_NOVA_MODELS}
    
    def estimate_cost(
        self,
        model_id: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int
    ) -> float:
        """
        Estimate cost in cents for an AI operation.
        
        Args:
            model_id: The model identifier
            estimated_input_tokens: Estimated input token count
            estimated_output_tokens: Estimated output token count
            
        Returns:
            Estimated cost in cents
        """
        if model_id not in self.model_costs:
            logger.warning(f"Unknown model {model_id}, using Haiku pricing as default")
            model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        costs = self.model_costs[model_id]
        input_cost = (estimated_input_tokens / 1000) * costs["input"]
        output_cost = (estimated_output_tokens / 1000) * costs["output"]
        
        total_cost = input_cost + output_cost
        logger.info(
            f"Estimated cost for {model_id}: "
            f"{estimated_input_tokens} input tokens = {input_cost:.4f} cents, "
            f"{estimated_output_tokens} output tokens = {output_cost:.4f} cents, "
            f"total = {total_cost:.4f} cents"
        )
        
        return round(total_cost, 4)  # 4 decimal places for 0.0001 cent precision
    
    def calculate_actual_cost(
        self,
        model_id: str,
        actual_input_tokens: int,
        actual_output_tokens: int
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate actual cost in cents for completed AI operation.
        
        Args:
            model_id: The model identifier
            actual_input_tokens: Actual input token count
            actual_output_tokens: Actual output token count
            
        Returns:
            Tuple of (total_cost_cents, cost_breakdown_dict)
        """
        if model_id not in self.model_costs:
            logger.warning(f"Unknown model {model_id}, using Haiku pricing as default")
            model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        costs = self.model_costs[model_id]
        input_cost = (actual_input_tokens / 1000) * costs["input"]
        output_cost = (actual_output_tokens / 1000) * costs["output"]
        total_cost = input_cost + output_cost
        
        breakdown = {
            "input_cost_cents": round(input_cost, 4),  # 0.0001 cent precision
            "output_cost_cents": round(output_cost, 4),  # 0.0001 cent precision
            "total_cost_cents": round(total_cost, 4),  # 0.0001 cent precision
            "input_tokens": actual_input_tokens,
            "output_tokens": actual_output_tokens,
            "model_id": model_id,
        }
        
        logger.info(
            f"Actual cost for {model_id}: "
            f"{actual_input_tokens} input = ${input_cost/100:.6f}, "
            f"{actual_output_tokens} output = ${output_cost/100:.6f}, "
            f"total = ${total_cost/100:.6f}"
        )
        
        return round(total_cost, 4), breakdown  # 0.0001 cent precision
    
    def get_model_pricing(self, model_id: str) -> Dict[str, float]:
        """Get pricing information for a specific model."""
        if model_id not in self.model_costs:
            return {
                "available": False,
                "model_id": model_id,
                "message": "Model pricing not found"
            }
        
        costs = self.model_costs[model_id]
        return {
            "available": True,
            "model_id": model_id,
            "input_cost_per_1k_tokens_cents": costs["input"],
            "output_cost_per_1k_tokens_cents": costs["output"],
            "input_cost_per_token_cents": costs["input"] / 1000,
            "output_cost_per_token_cents": costs["output"] / 1000,
        }