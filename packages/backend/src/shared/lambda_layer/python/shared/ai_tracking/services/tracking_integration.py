"""Integration layer to connect AI tracking with existing handlers."""
import os
from typing import Dict, Any, Optional
from datetime import datetime
from aws_lambda_powertools import Logger

from .usage_tracker import AIUsageTracker
from .cost_calculator import AICostCalculator
from ..models.ai_usage_event import AIModelProvider

logger = Logger()


class AITrackingIntegration:
    """Helper class to integrate AI tracking into existing Lambda handlers."""
    
    def __init__(self, table_name: Optional[str] = None):
        """Initialize with optional table name override."""
        self.table_name = table_name or os.environ.get(
            "AI_USAGE_TRACKING_TABLE_NAME", "ps-ai-usage-tracking"
        )
        self.tracker = AIUsageTracker(self.table_name)
        self.calculator = AICostCalculator()
    
    def track_selection_decision(
        self,
        user_id: str,
        pulse_id: str,
        worthiness_score: float,
        decision: str,
        ai_worthy: bool,
        estimated_cost_cents: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track AI selection/worthiness evaluation."""
        try:
            # Track the selection evaluation event
            self.tracker.track_selection_evaluation(
                user_id=user_id,
                pulse_id=pulse_id,
                worthiness_score=worthiness_score,
                decision=decision,
                estimated_cost_cents=estimated_cost_cents if ai_worthy else 0,
                metadata={
                    "ai_worthy": ai_worthy,
                    **(metadata or {})
                }
            )
            logger.info(f"Tracked selection decision for pulse {pulse_id}")
        except Exception as e:
            logger.error(f"Failed to track selection decision: {e}")
            # Don't fail the main flow if tracking fails
    
    def start_enhancement_tracking(
        self,
        user_id: str,
        pulse_id: str,
        model_id: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Start tracking an AI enhancement request."""
        try:
            # Calculate estimated cost
            estimated_cost = self.calculator.estimate_cost(
                model_id=model_id,
                estimated_input_tokens=estimated_input_tokens,
                estimated_output_tokens=estimated_output_tokens
            )
            
            # Determine provider from model ID
            provider = self._get_provider_from_model(model_id)
            
            # Start tracking
            event_id = self.tracker.start_enhancement(
                user_id=user_id,
                pulse_id=pulse_id,
                model_provider=provider,
                model_id=model_id,
                estimated_cost_cents=estimated_cost,
                metadata={
                    "estimated_input_tokens": estimated_input_tokens,
                    "estimated_output_tokens": estimated_output_tokens,
                    **(metadata or {})
                }
            )
            
            logger.info(f"Started enhancement tracking for pulse {pulse_id}, event {event_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to start enhancement tracking: {e}")
            return None
    
    def complete_enhancement_tracking(
        self,
        event_id: str,
        user_id: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int,
        response_metadata: Optional[Dict[str, Any]] = None,
        quality_score: Optional[float] = None
    ) -> Optional[float]:
        """Complete tracking for successful AI enhancement."""
        try:
            # Calculate actual cost
            actual_cost, cost_breakdown = self.calculator.calculate_actual_cost(
                model_id=model_id,
                actual_input_tokens=input_tokens,
                actual_output_tokens=output_tokens
            )
            
            # Complete tracking
            self.tracker.complete_enhancement(
                event_id=event_id,
                user_id=user_id,
                actual_cost_cents=actual_cost,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                response_metadata={
                    "cost_breakdown": cost_breakdown,
                    **(response_metadata or {})
                },
                quality_score=quality_score
            )
            
            logger.info(
                f"Completed enhancement tracking for event {event_id}, "
                f"actual cost: ${actual_cost/100:.4f}"
            )
            return actual_cost
            
        except Exception as e:
            logger.error(f"Failed to complete enhancement tracking: {e}")
            return None
    
    def fail_enhancement_tracking(
        self,
        event_id: str,
        user_id: str,
        error_code: str,
        error_message: str,
        duration_ms: Optional[int] = None
    ) -> None:
        """Track failed AI enhancement."""
        try:
            self.tracker.fail_enhancement(
                event_id=event_id,
                user_id=user_id,
                error_code=error_code,
                error_message=error_message,
                duration_ms=duration_ms
            )
            logger.info(f"Tracked enhancement failure for event {event_id}: {error_code}")
        except Exception as e:
            logger.error(f"Failed to track enhancement failure: {e}")
    
    def track_error(
        self,
        user_id: str,
        pulse_id: str,
        error_type: str,
        error_message: str,
        handler_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track general errors in Lambda handlers."""
        try:
            # Track as a general AI event with error details
            self.tracker.track_selection_evaluation(
                user_id=user_id,
                pulse_id=pulse_id,
                worthiness_score=0.0,  # N/A for errors
                decision=f"ERROR in {handler_name}: {error_type}",
                estimated_cost_cents=0.0,
                metadata={
                    "error_type": error_type,
                    "error_message": error_message,
                    "handler_name": handler_name,
                    "is_error_event": True,
                    **(metadata or {})
                }
            )
            logger.info(f"Tracked error for handler {handler_name}: {error_type}")
        except Exception as e:
            logger.error(f"Failed to track error: {e}")
            # Silently fail - don't break error handling
    
    def _get_provider_from_model(self, model_id: str) -> AIModelProvider:
        """Determine provider from model ID."""
        if "anthropic" in model_id:
            return AIModelProvider.BEDROCK
        elif "amazon" in model_id:
            return AIModelProvider.BEDROCK
        elif "meta" in model_id:
            return AIModelProvider.BEDROCK
        else:
            return AIModelProvider.BEDROCK  # Default for AWS Bedrock