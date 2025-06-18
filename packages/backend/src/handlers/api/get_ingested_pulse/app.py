import os
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from aws_lambda_powertools.event_handler.exceptions import BadRequestError
from aws_lambda_powertools.utilities.typing import LambdaContext
from typing import Any

from shared.models.pulse import (
    ArchivedPulse,
)

from services import DEFAULT_NB_ITEMS, get_ingested_pulses

# Initialize the logger
logger = Logger()

# Retrieve environment variable
INGESTED_PULSE_TABLE_NAME = os.environ["INGESTED_PULSE_TABLE_NAME"]

# Configure CORS
cors_config = CORSConfig(
    allow_origin="*",  # In production, specify your actual domain
)

# Initialize the APIGatewayRestResolver
app = APIGatewayRestResolver(cors=cors_config)


@app.get("/get-ingested-pulses")
def get_ingested_pulses_handler() -> list[ArchivedPulse]:
    """
    Handler function to get the start pulse of a user.
    """
    user_id = app.current_event.get_query_string_value("user_id")
    if not user_id:
        logger.error("Missing user_id in query parameters")
        raise BadRequestError("Missing user_id in query parameters")
    nb_items = app.current_event.get_query_string_value("nb_items")
    nb_items = int(nb_items or DEFAULT_NB_ITEMS)
    logger.warning(f"Retrieving current IngestedPulses for user {user_id}")

    try:
        results = list(
            get_ingested_pulses(
                user_id=user_id, nb_items=nb_items, table_name=INGESTED_PULSE_TABLE_NAME
            )
        )
        print(
            f"For user {user_id} got the following last {nb_items} ArchivedPulse: {results}"
        )
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
