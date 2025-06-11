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
    pulse_id = start_pulse(
        user_id="test_user",
        start_time=datetime.now(),
        intent="test_intent",
        duration_seconds=300,
        tags=["test", "example"],
        is_public=True,
        table_name=table.name,
    )

    assert pulse_id is not None
    assert len(pulse_id) == 36  # UUID length

    # Verify the pulse was created
    pulse = get_start_pulse(
        user_id="test_user",
        table_name=table.name,
    )
    assert pulse["pulse_id"] == pulse_id
    assert pulse["user_id"] == "test_user"
    assert pulse["intent"] == "test_intent"

    pulse_id = start_pulse(
        user_id="test_user_2",
        start_time=datetime.now(),
        intent="other_intent",
        table_name=table.name,
    )
    pulse = get_start_pulse(
        user_id="test_user_2",
        table_name=table.name,
    )
    assert pulse["pulse_id"] == pulse_id
    assert pulse["user_id"] == "test_user_2"
    assert pulse["intent"] == "other_intent"
