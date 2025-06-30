import datetime
import os
from moto import mock_aws

from shared.models.pulse import StartPulse, StopPulse, ArchivedPulse
from src.handlers.events.standard_enhancement.standard_enhancement.generators import PulseTitleGenerator
from src.handlers.api.start_pulse.start_pulse.services import start_pulse
from src.handlers.api.stop_pulse.stop_pulse.services import stop_pulse
from src.handlers.events.pure_ingest.pure_ingest.app import handler as ingest_handler
from tests.fixtures.ddb import (
    create_ingested_pulse_table,
    create_start_pulse_table,
    create_stop_pulse_table,
)


@mock_aws
def test_ingest_pulse():
    """Test pulse ingestion with standard enhancement"""

    # Create test tables
    start_pulse_table = create_start_pulse_table()
    stop_pulse_table = create_stop_pulse_table()
    ingested_table = create_ingested_pulse_table()

    # Set environment variables for the handlers
    os.environ["STOP_PULSE_TABLE_NAME"] = stop_pulse_table.name
    os.environ["INGESTED_PULSE_TABLE_NAME"] = ingested_table.name

    user_id = "test_user"
    pulse_duration = 300  # seconds

    # Start a pulse
    start_time = datetime.datetime.now(datetime.timezone.utc)
    start_pulse(
        StartPulse(
            user_id=user_id,
            start_time=start_time,
            intent="add ingestPulse to backend",
        ),
        table_name=start_pulse_table.name,
    )

    # Stop the pulse
    reflection_text = "Super happy to have a first working version. Trivial to improve in the short future"
    stopped_pulse = stop_pulse(
        user_id=user_id,
        start_pulse_table_name=start_pulse_table.name,
        stop_pulse_table_name=stop_pulse_table.name,
        reflection=reflection_text,
        stopped_at=start_time + datetime.timedelta(seconds=pulse_duration),
    )
    assert stopped_pulse is not None

    # Create event for ingestion handler
    event = {
        "stopPulse": stopped_pulse.model_dump(),
        "generatedTitle": "Achievement Unlocked! 🎯",
        "generatedBadge": "✨ Code Warrior",
        "aiEnhanced": False,
    }

    # Call the ingest handler
    result = ingest_handler(event, None)  # type: ignore
    
    assert result["success"] is True
    assert result["pulseId"] == stopped_pulse.pulse_id
    
    # Verify the pulse was archived
    archived_pulse_data = result["archivedPulse"]
    assert archived_pulse_data["gen_title"] == "Achievement Unlocked! 🎯"
    assert archived_pulse_data["gen_badge"] == "✨ Code Warrior"
    assert archived_pulse_data["ai_enhanced"] is False

    # Test title generation with the archived pulse
    archived_pulse = ArchivedPulse(**archived_pulse_data)
    generated_titles = PulseTitleGenerator.generate_multiple_options(archived_pulse, 3)
    print("Generated Multiple Pulse Titles")
    for title in generated_titles:
        print("- ", title)
    assert len(generated_titles) == 3
