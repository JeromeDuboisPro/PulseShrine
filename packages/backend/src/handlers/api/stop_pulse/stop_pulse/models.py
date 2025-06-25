from datetime import datetime, timezone
from pydantic import BaseModel


class StopPulseRequest(BaseModel):
    user_id: str
    reflection: str
    reflection_emotion: str | None = None
    stopped_at: str | None = None

    def stopped_at_dt(self) -> datetime:
        """Return the stopped_at time as timezone-aware datetime."""
        if self.stopped_at:
            dt = datetime.fromisoformat(self.stopped_at)
            # Ensure timezone-aware
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        return datetime.now(timezone.utc)
