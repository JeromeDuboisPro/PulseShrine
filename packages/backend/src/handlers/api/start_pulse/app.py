import os
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from aws_lambda_powertools.event_handler.exceptions import BadRequestError
from aws_lambda_powertools.utilities.typing import LambdaContext
from datetime import datetime
from pydantic import BaseModel, ValidationError
from typing import Any

from shared.models.pulse import (
    PulseCreationError,
    StartPulse,
)

from models import PulseCreationErrorAlreadyPresent
from services import start_pulse

# Initialize the logger
logger = Logger()

# Retrieve environment variable
START_PULSE_TABLE_NAME = os.environ["START_PULSE_TABLE_NAME"]

# Configure CORS
cors_config = CORSConfig(
    allow_origin="*",  # In production, specify your actual domain
)

# Initialize the APIGatewayRestResolver
app = APIGatewayRestResolver(cors=cors_config)


@app.post("/start-pulse")
def start_pulse_handler():
    """
    Handler function to start a pulse.
    """
    try:
        body = app.current_event.json_body
        pulse_data = StartPulse(**body)
    except (ValidationError, TypeError, ValueError) as exc:
        logger.error(f"Validation error: {str(exc)}")
        raise BadRequestError(f"Invalid request: {str(exc)}")

    try:
        result = start_pulse(pulse_data=pulse_data, table_name=START_PULSE_TABLE_NAME)
    except PulseCreationErrorAlreadyPresent as exc:
        logger.error(f"Pulse already exists: {str(exc)}")
        raise BadRequestError(f"Pulse with ID {pulse_data.pulse_id} already exists.")
    except PulseCreationError as exc:
        logger.error(f"Pulse creation error: {str(exc)}")
        raise BadRequestError(f"Failed to create pulse: {str(exc)}")
    except Exception as exc:
        logger.error(f"Unexpected error: {str(exc)}")
        raise BadRequestError("An unexpected error occurred while starting the pulse.")

    if not result:
        logger.error("Failed to start pulse due to invalid input data.")
        raise BadRequestError("Failed to start pulse. Please check the input data.")
    return result.model_dump(mode="json")


def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Lambda function handler.
    """
    return app.resolve(event, context)
