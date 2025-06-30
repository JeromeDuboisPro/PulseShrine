import os
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from aws_lambda_powertools.event_handler.exceptions import BadRequestError
from aws_lambda_powertools.utilities.typing import LambdaContext
from typing import Any

from shared.models.pulse import (
    StopPulse,
)

from get_stop_pulse.services import get_stop_pulses

# Initialize the logger
logger = Logger()

# Retrieve environment variable
STOP_PULSE_TABLE_NAME = os.environ["STOP_PULSE_TABLE_NAME"]

# Configure CORS
cors_config = CORSConfig(
    allow_origin="*",  # In production, specify your actual domain
)

# Initialize the APIGatewayRestResolver
app = APIGatewayRestResolver(cors=cors_config)


@app.get("/get-stop-pulses")
def get_stop_pulses_handler() -> list[StopPulse]:
    """
    Handler function to get the start pulse of a user.
    """
    user_id = app.current_event.get_query_string_value("user_id")
    if not user_id:
        logger.error("Missing user_id in query parameters")
        raise BadRequestError("Missing user_id in query parameters")
    logger.warning(f"Retrieving current StopPulses for user {user_id}")

    try:
        results = list(
            get_stop_pulses(user_id=user_id, table_name=STOP_PULSE_TABLE_NAME)
        )
        print(f"For user {user_id} got the following StopPulses: {results}")
        return results

    except Exception as exc:
        logger.error(f"Unexpected error: {str(exc)}")
        raise BadRequestError("An unexpected error occurred while starting the pulse.")


def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Lambda function handler.
    """
    logger.info(f"Type of event: {type(event)}")
    logger.info(f"Received event: {event}")

    return app.resolve(event, context)
