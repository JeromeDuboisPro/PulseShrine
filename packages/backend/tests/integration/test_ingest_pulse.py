import datetime
from moto import mock_aws

from shared.models.pulse import StartPulse
from shared.services.generators import PulseTitleGenerator
from shared.services.pulse import ingest_pulse, start_pulse, stop_pulse
from tests.fixtures.ddb import (create_ingested_pulse_table,
                                create_start_pulse_table,
                                create_stop_pulse_table)


@mock_aws
def test_ingest_pulse():
    """Test pulse ingestion without moto mock"""

    # Create test table
    start_pulse_table = create_start_pulse_table()

    user_id = "test_user"

    pulse_duration = 300  # seconds

    start_pulse(
        StartPulse(
            user_id=user_id,
            start_time=datetime.datetime.now(),
            intent="add ingestPulse to backend",
        ),
        table_name=start_pulse_table.name,
    )

    stop_pulse_table = create_stop_pulse_table()

    reflection_text = "fixes for stopPulse along the road, got some interesting first easy implementation for glyph generation etc… For the short pulse it was, was excellent!"
    reflection_text = "Oopsie worked on UI design with Blandine"
    reflection_text = " took more time to prepare the foundations. Very happy to have integration testing with moto for ddb. Achieved first implementation to start a pulse"
    reflection_text = " Super happy to have a first working version. Trivial to improve in the short future"

    stopped_pulse = stop_pulse(
        user_id=user_id,
        start_pulse_table_name=start_pulse_table.name,
        stop_pulse_table_name=stop_pulse_table.name,
        reflection=reflection_text,
        stopped_at=datetime.datetime.now() + datetime.timedelta(seconds=pulse_duration),
    )
    assert stopped_pulse is not None
    ingested_table = create_ingested_pulse_table()

    ingested_pulse = ingest_pulse(
        stop_pulse=stopped_pulse,
        ingested_pulse_table_name=ingested_table.name,
        stop_pulse_table_name=stop_pulse_table.name,
    )

    print(ingested_pulse)

    assert ingested_pulse is not None

    generated_title = ingested_pulse.gen_title
    print("Generated Pulse Title")
    print(generated_title)
    print()
    assert generated_title is not None
    assert len(generated_title) > 0

    badge = ingested_pulse.gen_badge
    print("Generated Achievement Badge")
    print(badge)
    print()
    assert badge is not None
    assert badge != ""

    generated_titles = PulseTitleGenerator.generate_multiple_options(ingested_pulse, 3)
    print("Generated Multiple Pulse Titles")
    for title in generated_titles:
        print("- ", title)
    assert len(generated_titles) == 3
    assert generated_title is not None
