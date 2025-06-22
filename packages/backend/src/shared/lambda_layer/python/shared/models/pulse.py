from datetime import datetime, timezone
from functools import cached_property
from pydantic import BaseModel, Field, computed_field
from typing import List, Optional


class PulseCreationError(Exception):
    """Custom exception for pulse creation errors"""

    pass


class PulseBase(BaseModel):
    user_id: str
    intent: str
    pulse_id: Optional[str] = Field(default=None)
    start_time: Optional[datetime | str] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Start time of the pulse, defaults to UTC now if not provided",
    )
    duration_seconds: Optional[int] = Field(default=None)
    intent_emotion: Optional[str] = Field(
        default=None, description="Energy type for the pulse (creation, focus, etc.)"
    )
    tags: Optional[List[str]] = Field(default=None)
    is_public: bool = Field(default=False)

    @cached_property
    def start_time_dt(self) -> datetime:
        """Return the start time as timezone-aware datetime."""
        if isinstance(self.start_time, datetime):
            # Ensure timezone-aware
            if self.start_time.tzinfo is None:
                return self.start_time.replace(tzinfo=timezone.utc)
            return self.start_time
        elif isinstance(self.start_time, str):
            try:
                dt = datetime.fromisoformat(self.start_time)
                # Ensure timezone-aware
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError as exc:
                raise PulseCreationError(f"Invalid start_time format: {exc}") from exc
        else:
            raise PulseCreationError(
                "start_time must be a datetime or ISO formatted string"
            )

    @cached_property
    def valid_pulse_id(self) -> str:
        """Return a valid pulse ID, generating one if not provided."""
        if self.pulse_id:
            return self.pulse_id
        raise PulseCreationError(
            "Pulse ID is required but not provided. Please provide a valid pulse_id."
        )


class StartPulse(PulseBase):
    def model_post_init(self, _):
        if isinstance(self.start_time, str):
            try:
                object.__setattr__(
                    self, "start_time", datetime.fromisoformat(self.start_time)
                )
            except Exception as exc:
                raise PulseCreationError(f"Failed to parse start_time: {exc}") from exc

    pass


class StopPulse(PulseBase):
    reflection: str
    reflection_emotion: Optional[str] = Field(
        default=None, description="Emotion felt after completing the pulse"
    )
    stopped_at: Optional[datetime | str] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Stop time of the pulse, defaults to UTC now if not provided",
    )

    @cached_property
    def stopped_at_dt(self) -> datetime:
        """Return the stopped_at time in ISO format."""
        if isinstance(self.stopped_at, datetime):
            return self.stopped_at
        elif self.stopped_at:
            return datetime.fromisoformat(self.stopped_at)
        else:
            raise PulseCreationError("stopped_at field cannot be None for StopPulse.")

    def model_post_init(self, _):
        if self.duration_seconds is None and self.start_time and self.stopped_at_dt:
            try:
                start = self.start_time_dt
                stop = self.stopped_at_dt
                object.__setattr__(
                    self, "duration_seconds", int((stop - start).total_seconds())
                )
            except Exception:
                pass


class ArchivedPulse(StopPulse):
    archived_at: Optional[datetime | str] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Archive time of the pulse, defaults to UTC now if not provided",
    )
    gen_title: str = Field(
        default="",
        description="Generated title for the pulse, used for display purposes",
    )
    gen_badge: str = Field(
        default="",
        description="Generated badge for the pulse, used for display purposes",
    )

    @computed_field
    @cached_property
    def inverted_timestamp(self) -> int:
        """Return the stopped time 'reversed to optimize most recent search in ddb."""
        return int(
            (
                datetime(year=9999, month=12, day=31, hour=23, minute=59, second=59)
                - self.stopped_at_dt
            ).total_seconds()
        )

    def archived_at_dt(self) -> datetime:
        """Return the archived_at time in ISO format."""
        if isinstance(self.archived_at, datetime):
            return self.archived_at
        elif isinstance(self.archived_at, str):
            try:
                return datetime.fromisoformat(self.archived_at)
            except ValueError as exc:
                raise PulseCreationError(f"Invalid archived_at format: {exc}") from exc
        else:
            raise PulseCreationError(
                "archived_at must be a datetime or ISO formatted string"
            )
