from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class PulseCreationError(Exception):
    """Custom exception for pulse creation errors"""

    pass


class PulseBase(BaseModel):
    user_id: str
    pulse_id: str
    start_time: str
    intent: str
    duration_seconds: Optional[int] = None
    tags: Optional[List[str]] = Field(default=None)
    is_public: bool = False


class StartPulse(PulseBase):
    pass


class StopPulse(PulseBase):
    reflection: str
    stopped_at: str

    def model_post_init(self, _):
        if self.duration_seconds is None and self.start_time and self.stopped_at:
            try:
                start = datetime.fromisoformat(self.start_time)
                stop = datetime.fromisoformat(self.stopped_at)
                object.__setattr__(
                    self, "duration_seconds", int((stop - start).total_seconds())
                )
            except Exception:
                pass
