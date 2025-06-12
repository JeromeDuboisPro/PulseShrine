from datetime import datetime

from moto import mock_aws

# Your pulse creation code here (from previous artifact)
from src.shared.services.pulse import get_start_pulse, start_pulse
from tests.fixtures.ddb import create_start_pulse_table


@mock_aws
def test_create_pulse_with_moto():
    """Test pulse creation using moto mock"""

    # Create test table
    table = create_start_pulse_table()

    # Test pulse creation
    created_start_pulse_1 = start_pulse(
        user_id="test_user",
        start_time=datetime.now(),
        intent="test_intent",
        duration_seconds=300,
        tags=["test", "example"],
        is_public=True,
        table_name=table.name,
    )

    assert created_start_pulse_1 is not None
    assert len(created_start_pulse_1.pulse_id) == 36  # UUID length

    # Verify the pulse was created
    created_start_pulse_2 = get_start_pulse(
        user_id="test_user",
        table_name=table.name,
    )
    assert created_start_pulse_2 is not None
    assert created_start_pulse_2.pulse_id == created_start_pulse_1.pulse_id
    assert created_start_pulse_2.user_id == "test_user"
    assert created_start_pulse_2.intent == "test_intent"

    created_start_pulse_1 = start_pulse(
        user_id="test_user_2",
        start_time=datetime.now(),
        intent="other_intent",
        table_name=table.name,
    )
    created_start_pulse_2 = get_start_pulse(
        user_id="test_user_2",
        table_name=table.name,
    )
    assert created_start_pulse_2 is not None
    assert created_start_pulse_1.pulse_id == created_start_pulse_2.pulse_id
    assert created_start_pulse_2.user_id == "test_user_2"
    assert created_start_pulse_2.intent == "other_intent"
