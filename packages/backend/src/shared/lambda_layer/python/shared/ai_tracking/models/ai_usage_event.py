"""AI Usage Event model for tracking AI API calls and costs."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from decimal import Decimal


def convert_floats_to_decimal(obj: Any) -> Any:
    """Recursively convert float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    else:
        return obj


class AIEventType(str, Enum):
    """Types of AI events we track."""
    ENHANCEMENT_REQUEST = "enhancement_request"
    ENHANCEMENT_COMPLETED = "enhancement_completed"
    ENHANCEMENT_FAILED = "enhancement_failed"
    SELECTION_EVALUATED = "selection_evaluated"
    CREDIT_CHECK = "credit_check"


class AIModelProvider(str, Enum):
    """AI model providers."""
    BEDROCK = "bedrock"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    STANDARD = "standard"  # Non-AI processing


@dataclass
class AIUsageEvent:
    """Represents a single AI usage event for tracking purposes."""
    
    # Primary identifiers
    event_id: str  # Unique ID for this event
    user_id: str
    pulse_id: Optional[str] = None  # Associated pulse if applicable
    
    # Event details
    event_type: AIEventType = AIEventType.ENHANCEMENT_REQUEST
    model_provider: AIModelProvider = AIModelProvider.BEDROCK
    model_id: Optional[str] = None  # e.g., "anthropic.claude-3-haiku-20240307-v1:0"
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_date: str = field(default="")  # YYYY-MM-DD for partitioning
    duration_ms: Optional[int] = None  # Processing duration
    
    # Cost tracking
    estimated_cost_cents: Optional[float] = None
    actual_cost_cents: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    
    # Request/Response details
    request_metadata: Dict[str, Any] = field(default_factory=dict)
    response_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Status and errors
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # Quality metrics
    quality_score: Optional[float] = None  # 0-1 score if evaluated
    user_feedback: Optional[str] = None  # positive/negative/neutral
    
    def __post_init__(self):
        """Set derived fields after initialization."""
        if not self.event_date:
            self.event_date = self.timestamp.strftime("%Y-%m-%d")
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        item = {
            "PK": f"USER#{self.user_id}",
            "SK": f"EVENT#{self.timestamp.isoformat()}#{self.event_id}",
            "event_id": self.event_id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "model_provider": self.model_provider,
            "timestamp": self.timestamp.isoformat(),
            "event_date": self.event_date,
            "success": self.success,
        }
        
        # Add optional fields if present, converting floats to Decimal
        optional_fields = [
            "pulse_id", "model_id", "duration_ms", 
            "estimated_cost_cents", "actual_cost_cents",
            "input_tokens", "output_tokens", "total_tokens",
            "error_code", "error_message", 
            "quality_score", "user_feedback"
        ]
        
        for field_name in optional_fields:
            value = getattr(self, field_name)
            if value is not None:
                # Convert float values to Decimal for DynamoDB
                if isinstance(value, float):
                    item[field_name] = Decimal(str(value))
                else:
                    item[field_name] = value
        
        # Add metadata if present, converting floats to Decimal
        if self.request_metadata:
            item["request_metadata"] = convert_floats_to_decimal(self.request_metadata)
        if self.response_metadata:
            item["response_metadata"] = convert_floats_to_decimal(self.response_metadata)
            
        # Add GSI keys for different access patterns
        item["GSI1PK"] = f"DATE#{self.event_date}"
        item["GSI1SK"] = f"USER#{self.user_id}#{self.timestamp.isoformat()}"
        
        if self.pulse_id:
            item["GSI2PK"] = f"PULSE#{self.pulse_id}"
            item["GSI2SK"] = f"EVENT#{self.timestamp.isoformat()}"
            
        return item
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> "AIUsageEvent":
        """Create instance from DynamoDB item."""
        return cls(
            event_id=item["event_id"],
            user_id=item["user_id"],
            pulse_id=item.get("pulse_id"),
            event_type=AIEventType(item["event_type"]),
            model_provider=AIModelProvider(item["model_provider"]),
            model_id=item.get("model_id"),
            timestamp=datetime.fromisoformat(item["timestamp"]),
            event_date=item["event_date"],
            duration_ms=item.get("duration_ms"),
            estimated_cost_cents=item.get("estimated_cost_cents"),
            actual_cost_cents=item.get("actual_cost_cents"),
            input_tokens=item.get("input_tokens"),
            output_tokens=item.get("output_tokens"),
            total_tokens=item.get("total_tokens"),
            request_metadata=item.get("request_metadata", {}),
            response_metadata=item.get("response_metadata", {}),
            success=item.get("success", True),
            error_code=item.get("error_code"),
            error_message=item.get("error_message"),
            quality_score=item.get("quality_score"),
            user_feedback=item.get("user_feedback"),
        )