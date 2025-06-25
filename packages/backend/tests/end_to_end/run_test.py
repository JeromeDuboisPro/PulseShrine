#!/usr/bin/env python3
"""
Runner script for the end-to-end pipeline test.

This script sets up the necessary mocks and environment for testing
the complete PulseShrine pipeline without requiring actual AWS resources.
"""

import sys
import os
from unittest.mock import Mock, patch
import json

# Add the src directory to Python path
src_path = os.path.join(os.path.dirname(__file__), '../../src')
shared_path = os.path.join(os.path.dirname(__file__), '../../src/shared/lambda_layer/python')
handlers_path = os.path.join(os.path.dirname(__file__), '../../src/handlers')

sys.path.insert(0, src_path)
sys.path.insert(0, shared_path)
sys.path.insert(0, handlers_path)

# Add individual handler directories to Python path for module imports
api_handlers = ['start_pulse', 'stop_pulse', 'get_start_pulse', 'get_stop_pulse', 'get_ingested_pulse']
event_handlers = ['ai_selection', 'bedrock_enhancement', 'standard_enhancement', 'pure_ingest']

for handler in api_handlers:
    handler_path = os.path.join(os.path.dirname(__file__), f'../../src/handlers/api/{handler}')
    sys.path.insert(0, handler_path)

for handler in event_handlers:
    handler_path = os.path.join(os.path.dirname(__file__), f'../../src/handlers/events/{handler}')
    sys.path.insert(0, handler_path)

def setup_aws_mocks():
    """Set up AWS service mocks for testing."""
    
    # Mock boto3 clients
    mock_dynamodb = Mock()
    mock_ssm = Mock() 
    mock_bedrock = Mock()
    
    # Mock DynamoDB operations
    mock_dynamodb.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_dynamodb.get_item.return_value = {"Item": {}}
    mock_dynamodb.query.return_value = {"Items": [], "Count": 0}
    mock_dynamodb.scan.return_value = {"Items": [], "Count": 0}
    
    # Mock SSM parameters for AI configuration
    mock_ssm.get_parameter.return_value = {
        "Parameter": {"Value": "true"}  # Default to enabled
    }
    
    # Mock Bedrock for AI enhancement
    mock_bedrock.invoke_model.return_value = {
        "body": Mock(read=lambda: json.dumps({
            "results": [{
                "outputText": "🎯 Deep Focus Coding Session Complete!"
            }]
        }).encode())
    }
    
    return mock_dynamodb, mock_ssm, mock_bedrock

def setup_environment():
    """Set up test environment variables."""
    
    test_env = {
        "START_PULSE_TABLE_NAME": "test-start-pulse-table",
        "STOP_PULSE_TABLE_NAME": "test-stop-pulse-table", 
        "INGESTED_PULSE_TABLE_NAME": "test-ingested-pulse-table",
        "PARAMETER_PREFIX": "/pulseshrine/ai/",
        "AWS_REGION": "us-east-1",
        "AWS_DEFAULT_REGION": "us-east-1"
    }
    
    os.environ.update(test_env)
    
    print("🔧 Test environment configured:")
    for key, value in test_env.items():
        print(f"   {key}: {value}")

def main():
    """Run the end-to-end test with proper mocking."""
    
    print("🚀 PulseShrine End-to-End Test Runner")
    print("=====================================")
    
    # Set up environment
    setup_environment()
    
    # Set up AWS mocks
    mock_dynamodb, mock_ssm, mock_bedrock = setup_aws_mocks()
    
    print("\n🔍 Setting up AWS service mocks...")
    
    # Apply patches for AWS services
    with patch('boto3.client') as mock_boto3_client, \
         patch('boto3.resource') as mock_boto3_resource:
        
        # Configure boto3 client mock
        def client_side_effect(service_name, **kwargs):
            if service_name == 'dynamodb':
                return mock_dynamodb
            elif service_name == 'ssm':
                return mock_ssm
            elif service_name == 'bedrock-runtime':
                return mock_bedrock
            else:
                return Mock()
        
        def resource_side_effect(service_name, **kwargs):
            if service_name == 'dynamodb':
                mock_table = Mock()
                mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
                mock_table.get_item.return_value = {"Item": {}}
                mock_table.query.return_value = {"Items": [], "Count": 0}
                mock_resource = Mock()
                mock_resource.Table.return_value = mock_table
                return mock_resource
            else:
                return Mock()
        
        mock_boto3_client.side_effect = client_side_effect
        mock_boto3_resource.side_effect = resource_side_effect
        
        print("✅ AWS service mocks configured")
        print("\n🧪 Running end-to-end pipeline test...")
        
        # Import and run the test
        try:
            from test_complete_pipeline import test_complete_pipeline
            
            success = test_complete_pipeline()
            
            if success:
                print(f"\n🎉 END-TO-END TEST PASSED!")
                print("All pipeline components are working correctly.")
                return 0
            else:
                print(f"\n❌ END-TO-END TEST FAILED!")
                return 1
                
        except ImportError as e:
            print(f"❌ Failed to import test: {e}")
            return 1
        except Exception as e:
            print(f"💥 Test execution failed: {e}")
            import traceback
            traceback.print_exc()
            return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)