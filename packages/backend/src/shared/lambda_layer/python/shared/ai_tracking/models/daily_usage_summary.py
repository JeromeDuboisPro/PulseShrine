"""Daily usage summary model for aggregated AI usage metrics."""
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Any
from decimal import Decimal

from .ai_usage_event import convert_floats_to_decimal


@dataclass
class DailyUsageSummary:
    """Aggregated daily AI usage metrics per user."""
    
    # Identifiers
    user_id: str
    date: date
    
    # Usage counts
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # Cost tracking
    total_estimated_cost_cents: float = 0.0
    total_actual_cost_cents: float = 0.0
    
    # Token usage
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    
    # Breakdown by model
    usage_by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Format: {
    #     "model_id": {
    #         "requests": 10,
    #         "tokens": 5000,
    #         "cost_cents": 50.0
    #     }
    # }
    
    # Breakdown by event type
    usage_by_type: Dict[str, int] = field(default_factory=dict)
    
    # Performance metrics
    average_duration_ms: float = 0.0
    max_duration_ms: int = 0
    
    # Quality metrics
    average_quality_score: float = 0.0
    quality_scores_count: int = 0
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        item = {
            "PK": f"USER#{self.user_id}",
            "SK": f"DAILY#{self.date.isoformat()}",
            "user_id": self.user_id,
            "date": self.date.isoformat(),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "max_duration_ms": self.max_duration_ms,
            "quality_scores_count": self.quality_scores_count,
            # GSI for date-based queries
            "GSI1PK": f"DATE#{self.date.isoformat()}",
            "GSI1SK": f"USER#{self.user_id}",
        }
        
        # Convert float fields to Decimal
        item["total_estimated_cost_cents"] = Decimal(str(self.total_estimated_cost_cents))
        item["total_actual_cost_cents"] = Decimal(str(self.total_actual_cost_cents))
        item["average_duration_ms"] = Decimal(str(self.average_duration_ms))
        item["average_quality_score"] = Decimal(str(self.average_quality_score))
        
        # Convert nested dictionaries with potential floats
        item["usage_by_model"] = convert_floats_to_decimal(self.usage_by_model)
        item["usage_by_type"] = convert_floats_to_decimal(self.usage_by_type)
        
        return item
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> "DailyUsageSummary":
        """Create instance from DynamoDB item."""
        return cls(
            user_id=item["user_id"],
            date=date.fromisoformat(item["date"]),
            total_requests=item.get("total_requests", 0),
            successful_requests=item.get("successful_requests", 0),
            failed_requests=item.get("failed_requests", 0),
            total_estimated_cost_cents=item.get("total_estimated_cost_cents", 0.0),
            total_actual_cost_cents=item.get("total_actual_cost_cents", 0.0),
            total_input_tokens=item.get("total_input_tokens", 0),
            total_output_tokens=item.get("total_output_tokens", 0),
            total_tokens=item.get("total_tokens", 0),
            usage_by_model=item.get("usage_by_model", {}),
            usage_by_type=item.get("usage_by_type", {}),
            average_duration_ms=item.get("average_duration_ms", 0.0),
            max_duration_ms=item.get("max_duration_ms", 0),
            average_quality_score=item.get("average_quality_score", 0.0),
            quality_scores_count=item.get("quality_scores_count", 0),
        )