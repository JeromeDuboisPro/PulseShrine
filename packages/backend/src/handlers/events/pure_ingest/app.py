import datetime
import os
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from typing import Dict, Any, Union, Optional

from shared.models.pulse import StopPulse, ArchivedPulse
from shared.services.aws import get_ddb_table
from botocore.exceptions import BotoCoreError, ClientError

# Initialize the logger
logger = Logger()

# Environment variables
STOP_PULSE_TABLE_NAME = os.environ["STOP_PULSE_TABLE_NAME"]
INGESTED_PULSE_TABLE_NAME = os.environ["INGESTED_PULSE_TABLE_NAME"]


@logger.inject_lambda_context
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda function handler for pure ingestion (DynamoDB operations only).
    
    Input: Event with pulseData, generatedTitle, generatedBadge from previous steps
    Output: Success/failure result
    """
    logger.info("Pure Ingest Lambda invoked for DynamoDB operations")
    
    try:
        # Extract data from the event
        pulse_data = event.get('pulseData', {})
        stop_pulse_dict = event.get('stopPulse', {})
        
        # Get generated title and badge (from either Bedrock or cheap AI)
        generated_title = event.get('generatedTitle') or event.get('enhancedPulse', {}).get('gen_title')
        generated_badge = event.get('generatedBadge') or event.get('enhancedPulse', {}).get('gen_badge')
        ai_enhanced = event.get('aiEnhanced', False) or event.get('enhanced', False)
        
        # AI insights (only available from Bedrock path)
        ai_insights = event.get('enhancedPulse', {}).get('ai_insights')
        ai_cost_cents = event.get('aiCost', 0)
        
        if not pulse_data and not stop_pulse_dict:
            logger.error("No pulse data found in event")
            return {'success': False, 'error': 'No pulse data found'}
        
        # Create StopPulse object
        if stop_pulse_dict:
            stop_pulse = StopPulse(**stop_pulse_dict)
        else:
            stop_pulse = convert_ddb_to_stop_pulse(pulse_data)
        
        pulse_id = stop_pulse.pulse_id or "unknown"
        if not pulse_id or pulse_id == "unknown":
            logger.error("No valid pulse_id found")
            return {'success': False, 'error': 'No valid pulse_id found'}
        logger.info(f"Ingesting pulse {pulse_id} with AI enhanced: {ai_enhanced}")
        
        # Validate required fields
        if not generated_title:
            logger.warning(f"No generated title found, using fallback for pulse {pulse_id}")
            generated_title = "Session Complete! ✨"
        
        if not generated_badge:
            logger.warning(f"No generated badge found, using fallback for pulse {pulse_id}")
            generated_badge = "✨ Progress Maker"
        
        # Create archived pulse with generated content
        archived_pulse_data: Dict[str, Any] = {
            **stop_pulse.model_dump(),
            'archived_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'gen_title': generated_title,
            'gen_badge': generated_badge,
            'ai_enhanced': ai_enhanced
        }
        
        # Add AI-specific fields if available
        if ai_insights:
            archived_pulse_data['ai_insights'] = ai_insights
        
        if ai_cost_cents > 0:
            archived_pulse_data['ai_cost_cents'] = ai_cost_cents
        
        archived_pulse = ArchivedPulse(**archived_pulse_data)  # type: ignore
        
        # Store in ingested pulses table
        success = store_ingested_pulse(archived_pulse, INGESTED_PULSE_TABLE_NAME)
        
        if success:
            # Archive/delete from stop pulse table
            archive_success = archive_stop_pulse(pulse_id, STOP_PULSE_TABLE_NAME)  # type: ignore
            
            logger.info(
                f"Successfully ingested pulse {pulse_id}",
                extra={
                    "pulse_id": pulse_id,
                    "ai_enhanced": ai_enhanced,
                    "title": generated_title,
                    "badge": generated_badge,
                    "archived_from_stop_table": archive_success
                }
            )
            
            return {
                'success': True,
                'pulseId': pulse_id,
                'aiEnhanced': ai_enhanced,
                'archivedPulse': archived_pulse.model_dump()
            }
        else:
            return {'success': False, 'error': 'Failed to store pulse'}
        
    except Exception as e:
        logger.exception("Error in pure ingestion")
        return {'success': False, 'error': str(e)}


def convert_ddb_to_stop_pulse(pulse_data: Dict[str, Any]) -> StopPulse:
    """Convert DynamoDB format pulse data to StopPulse model"""
    
    def get_ddb_value(key: str, default: Optional[Any] = None) -> Union[str, int, float, bool, None]:
        """Extract value from DynamoDB attribute format"""
        if key in pulse_data:
            attr = pulse_data[key]
            if isinstance(attr, dict):
                if 'S' in attr:
                    return str(attr['S'])
                elif 'N' in attr:
                    return int(float(attr['N'])) if key == 'duration_seconds' else float(attr['N'])
                elif 'BOOL' in attr:
                    return bool(attr['BOOL'])
                elif 'NULL' in attr:
                    return None
            return attr
        return default
    
    # Extract all required fields with proper typing
    converted_data: Dict[str, Any] = {}
    
    # Required string fields
    if pulse_id := get_ddb_value('pulse_id'):
        converted_data['pulse_id'] = str(pulse_id)
    if user_id := get_ddb_value('user_id'):
        converted_data['user_id'] = str(user_id)
    if intent := get_ddb_value('intent'):
        converted_data['intent'] = str(intent)
    
    # Optional string fields
    if reflection := get_ddb_value('reflection'):
        converted_data['reflection'] = str(reflection)
    if start_time := get_ddb_value('start_time'):
        converted_data['start_time'] = str(start_time)
    if stopped_at := get_ddb_value('stopped_at'):
        converted_data['stopped_at'] = str(stopped_at)
    if intent_emotion := get_ddb_value('intent_emotion'):
        converted_data['intent_emotion'] = str(intent_emotion)
    if reflection_emotion := get_ddb_value('reflection_emotion'):
        converted_data['reflection_emotion'] = str(reflection_emotion)
    
    # Numeric fields
    if duration_seconds := get_ddb_value('duration_seconds'):
        converted_data['duration_seconds'] = int(duration_seconds) if isinstance(duration_seconds, (int, float)) else None
    
    # Boolean fields
    is_public = get_ddb_value('is_public', False)
    converted_data['is_public'] = bool(is_public)
    
    # List fields
    if tags := get_ddb_value('tags'):
        if isinstance(tags, list):
            converted_data['tags'] = [str(tag) for tag in tags]
    
    return StopPulse(**converted_data)  # type: ignore


def store_ingested_pulse(archived_pulse: ArchivedPulse, table_name: str) -> bool:
    """Store the ingested pulse in DynamoDB"""
    try:
        item = archived_pulse.model_dump()
        
        get_ddb_table(table_name).put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(pulse_id)",  # Prevent overwrites
        )
        
        logger.info(f"Successfully stored pulse {archived_pulse.pulse_id} in ingested table")
        return True
        
    except ClientError as e:
        error_message = e.response.get('Error', {}).get('Message', str(e)) if hasattr(e, 'response') else str(e)
        logger.error(
            f"Error storing pulse {archived_pulse.pulse_id}: {error_message}"
        )
        return False
    except BotoCoreError as e:
        logger.error(f"AWS connection error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error storing pulse {archived_pulse.pulse_id}: {str(e)}")
        return False


def archive_stop_pulse(pulse_id: str, table_name: str) -> bool:
    """Archive/delete the pulse from stop pulse table"""
    try:
        response = get_ddb_table(table_name).delete_item(
            Key={"pulse_id": pulse_id}, 
            ReturnValues="ALL_OLD"
        )
        
        if "Attributes" in response:
            logger.info(f"Successfully archived pulse {pulse_id} from stop table")
            return True
        else:
            logger.warning(f"No pulse found for {pulse_id} to archive")
            return False
            
    except ClientError as e:
        error_message = e.response.get('Error', {}).get('Message', str(e)) if hasattr(e, 'response') else str(e)
        logger.error(
            f"Error archiving pulse {pulse_id}: {error_message}"
        )
        return False
    except BotoCoreError as e:
        logger.error(f"AWS connection error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error archiving pulse {pulse_id}: {str(e)}")
        return False