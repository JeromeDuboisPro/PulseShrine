import os
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from aws_lambda_powertools.event_handler.exceptions import BadRequestError
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError
from typing import Any

from stop_pulse.models import StopPulseRequest
from stop_pulse.services import stop_pulse

# Initialize the logger
logger = Logger()

# Retrieve environment variable
START_PULSE_TABLE_NAME = os.environ["START_PULSE_TABLE_NAME"]
STOP_PULSE_TABLE_NAME = os.environ["STOP_PULSE_TABLE_NAME"]

# Configure CORS
cors_config = CORSConfig(
    allow_origin="*",  # In production, specify your actual domain
)

# Initialize the APIGatewayRestResolver
app = APIGatewayRestResolver(cors=cors_config)


@app.post("/stop-pulse")
def stop_pulse_handler():
    """
    Handler function to post a pulse.
    """
    try:
        body = app.current_event.json_body
        stop_pulse_data = StopPulseRequest(**body)
    except (ValidationError, TypeError, ValueError) as exc:
        logger.error(f"Validation error: {str(exc)}")
        raise BadRequestError(f"Invalid request: {str(exc)}")

    result = stop_pulse(
        user_id=stop_pulse_data.user_id,
        reflection=stop_pulse_data.reflection,
        reflection_emotion=stop_pulse_data.reflection_emotion,
        stopped_at=stop_pulse_data.stopped_at_dt(),
        start_pulse_table_name=START_PULSE_TABLE_NAME,
        stop_pulse_table_name=STOP_PULSE_TABLE_NAME,
    )

    if not result:
        logger.error("Failed to post pulse due to invalid input data.")
        raise BadRequestError("Failed to post pulse. Please check the input data.")

    return result.model_dump(mode="json")


def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Lambda function handler.
    """
    logger.info(f"Type of event: {type(event)}")
    logger.info(f"Received event: {event}")

    return app.resolve(event, context)
