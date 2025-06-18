from shared.models.pulse import PulseCreationError


class PulseCreationErrorAlreadyPresent(PulseCreationError):
    """Exception raised when a pulse with the same ID already exists"""

    def __init__(self, user_id: str):
        super().__init__(f"Pulse already exists for use {user_id}.")
        self.user_id = user_id
