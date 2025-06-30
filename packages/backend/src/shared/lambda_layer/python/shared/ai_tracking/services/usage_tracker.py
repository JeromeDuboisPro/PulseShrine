"""Usage tracking service for AI operations."""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

from ..models.ai_usage_event import AIUsageEvent, AIEventType, AIModelProvider
from shared.services.aws import get_ddb_table

logger = Logger()


class AIUsageTracker:
    """Service for tracking AI usage events."""
    
    def __init__(self, table_name: str):
        """Initialize with DynamoDB table name."""
        self.table_name = table_name
        self._table = None
    
    @property
    def table(self):
        """Lazy load DynamoDB table."""
        if self._table is None:
            self._table = get_ddb_table(self.table_name)
        return self._table
    
    def start_enhancement(
        self,
        user_id: str,
        pulse_id: str,
        model_provider: AIModelProvider,
        model_id: str,
        estimated_cost_cents: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Track the start of an AI enhancement request.
        
        Returns:
            event_id: Unique identifier for this event
        """
        event_id = str(uuid.uuid4())
        event = AIUsageEvent(
            event_id=event_id,
            user_id=user_id,
            pulse_id=pulse_id,
            event_type=AIEventType.ENHANCEMENT_REQUEST,
            model_provider=model_provider,
            model_id=model_id,
            estimated_cost_cents=estimated_cost_cents,
            request_metadata=metadata or {},
        )
        
        try:
            self.table.put_item(Item=event.to_dynamodb_item())
            logger.info(f"Tracked enhancement start for user {user_id}, pulse {pulse_id}")
            return event_id
        except ClientError as e:
            logger.error(f"Failed to track enhancement start: {e}")
            raise
    
    def complete_enhancement(
        self,
        event_id: str,
        user_id: str,
        actual_cost_cents: float,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int,
        response_metadata: Optional[Dict[str, Any]] = None,
        quality_score: Optional[float] = None
    ) -> None:
        """Track successful completion of AI enhancement."""
        event = AIUsageEvent(
            event_id=event_id,
            user_id=user_id,
            event_type=AIEventType.ENHANCEMENT_COMPLETED,
            actual_cost_cents=actual_cost_cents,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            duration_ms=duration_ms,
            response_metadata=response_metadata or {},
            quality_score=quality_score,
            success=True,
        )
        
        try:
            self.table.put_item(Item=event.to_dynamodb_item())
            logger.info(f"Tracked enhancement completion for event {event_id}")
        except ClientError as e:
            logger.error(f"Failed to track enhancement completion: {e}")
            raise
    
    def fail_enhancement(
        self,
        event_id: str,
        user_id: str,
        error_code: str,
        error_message: str,
        duration_ms: Optional[int] = None
    ) -> None:
        """Track failed AI enhancement."""
        event = AIUsageEvent(
            event_id=event_id,
            user_id=user_id,
            event_type=AIEventType.ENHANCEMENT_FAILED,
            duration_ms=duration_ms,
            success=False,
            error_code=error_code,
            error_message=error_message,
        )
        
        try:
            self.table.put_item(Item=event.to_dynamodb_item())
            logger.info(f"Tracked enhancement failure for event {event_id}: {error_code}")
        except ClientError as e:
            logger.error(f"Failed to track enhancement failure: {e}")
            raise
    
    def track_selection_evaluation(
        self,
        user_id: str,
        pulse_id: str,
        worthiness_score: float,
        decision: str,
        estimated_cost_cents: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track AI selection/worthiness evaluation."""
        event_id = str(uuid.uuid4())
        event = AIUsageEvent(
            event_id=event_id,
            user_id=user_id,
            pulse_id=pulse_id,
            event_type=AIEventType.SELECTION_EVALUATED,
            estimated_cost_cents=estimated_cost_cents,
            request_metadata={
                "worthiness_score": worthiness_score,
                "decision": decision,
                **(metadata or {})
            },
        )
        
        try:
            self.table.put_item(Item=event.to_dynamodb_item())
            logger.info(f"Tracked selection evaluation for pulse {pulse_id}")
        except ClientError as e:
            logger.error(f"Failed to track selection evaluation: {e}")
            raise
    
    def get_user_events(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> list[AIUsageEvent]:
        """Get AI usage events for a user within date range."""
        try:
            # Query by user partition key
            key_condition = f"PK = :pk"
            expression_values = {":pk": f"USER#{user_id}"}
            
            # Add date range to sort key if provided
            if start_date and end_date:
                key_condition += " AND SK BETWEEN :start AND :end"
                expression_values[":start"] = f"EVENT#{start_date}"
                expression_values[":end"] = f"EVENT#{end_date}T23:59:59"
            elif start_date:
                key_condition += " AND SK >= :start"
                expression_values[":start"] = f"EVENT#{start_date}"
            
            response = self.table.query(
                KeyConditionExpression=key_condition,
                ExpressionAttributeValues=expression_values,
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
            
            return [
                AIUsageEvent.from_dynamodb_item(item)
                for item in response.get("Items", [])
            ]
        except ClientError as e:
            logger.error(f"Failed to get user events: {e}")
            raise
    
    def get_pulse_events(self, pulse_id: str) -> list[AIUsageEvent]:
        """Get all AI events associated with a specific pulse."""
        try:
            response = self.table.query(
                IndexName="GSI2",  # Pulse index
                KeyConditionExpression="GSI2PK = :pk",
                ExpressionAttributeValues={
                    ":pk": f"PULSE#{pulse_id}"
                }
            )
            
            return [
                AIUsageEvent.from_dynamodb_item(item)
                for item in response.get("Items", [])
            ]
        except ClientError as e:
            logger.error(f"Failed to get pulse events: {e}")
            raise