from moto import mock_aws
from datetime import datetime

# Your pulse creation code here (from previous artifact)
from src.shared.services.pulse import start_pulse, stop_pulse
from tests.fixtures.ddb import create_ingest_pulse_table, create_start_pulse_table

@mock_aws
def test_stop_pulse_with_moto():
    """Test pulse stop using moto mock"""

    # Create test table
    start_pulse_table = create_start_pulse_table()
    
    user_id = "test_user"
    
    pulse_id = start_pulse(
        user_id=user_id,
        start_time=datetime.now(),
        intent="test_intent",
        duration_seconds=300,
        tags=["test", "example"],
        is_public=True,
        table_name=start_pulse_table.name,
    )
    
    stop_pulse_table = create_ingest_pulse_table()
    
    ingest_pulse = stop_pulse(
        user_id=user_id,
        start_pulse_table_name=start_pulse_table.name,
        stop_pulse_table_name=stop_pulse_table.name,
        reflection="Test reflection",
        stopped_at=datetime.now(),
    )
    assert ingest_pulse is not None
    assert ingest_pulse["user_id"] == user_id
    assert ingest_pulse["reflection"] == "Test reflection"
    assert ingest_pulse["pulse_id"] == pulse_id
    
    ingest_pulse = stop_pulse(
        user_id=user_id,
        start_pulse_table_name=start_pulse_table.name,
        stop_pulse_table_name=stop_pulse_table.name,
        reflection="Other reflection",
        stopped_at=datetime.now(),
    )
    assert ingest_pulse is None
    
@mock_aws
def test_stop_pulse_no_pulse_with_moto():
    """Test pulse stop, no pulse using moto mock"""

    # Create test table
    start_pulse_table = create_start_pulse_table()
    stop_pulse_table = create_ingest_pulse_table()
    
    ingest_pulse = stop_pulse(
        user_id="test_user",
        start_pulse_table_name=start_pulse_table.name,
        stop_pulse_table_name=stop_pulse_table.name,
        reflection="Other reflection",
        stopped_at=datetime.now(),
    )
    assert ingest_pulse is None