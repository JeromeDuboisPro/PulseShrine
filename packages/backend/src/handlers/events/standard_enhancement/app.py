from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from typing import Dict, Any

from shared.models.pulse import StopPulse
from generators import PulseTitleGenerator

# Initialize the logger
logger = Logger()


@logger.inject_lambda_context
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda function handler for cheap AI (standard title/badge generation).
    
    Input: Event with pulseData from previous step
    Output: Event with generated title and badge added
    """
    logger.info("Cheap AI Lambda invoked for standard title/badge generation")
    
    try:
        # Extract pulse data from the event
        pulse_data = event.get('pulseData', {})
        if not pulse_data:
            logger.error("No pulse data found in event")
            return {**event, 'error': 'No pulse data found'}
        
        # Convert DynamoDB format to StopPulse model
        stop_pulse = convert_ddb_to_stop_pulse(pulse_data)
        pulse_id = stop_pulse.pulse_id
        
        logger.info(f"Generating standard title and badge for pulse {pulse_id}")
        
        # Generate title and badge using standard generators
        generated_title = PulseTitleGenerator.generate_title(stop_pulse)
        generated_badge = PulseTitleGenerator.get_achievement_badge(stop_pulse)
        
        if not generated_title:
            logger.warning(f"Failed to generate title for pulse {pulse_id}")
            generated_title = "Session Complete! ✨"
        
        if not generated_badge:
            logger.warning(f"Failed to generate badge for pulse {pulse_id}")
            generated_badge = "✨ Progress Maker"
        
        logger.info(f"Generated standard title: '{generated_title}', badge: '{generated_badge}'")
        
        # Add generated content to the event
        result = {
            **event,
            'generatedTitle': generated_title,
            'generatedBadge': generated_badge,
            'aiEnhanced': False,  # This is standard generation
            'stopPulse': stop_pulse.model_dump()
        }
        
        return result
        
    except Exception as e:
        logger.exception("Error in cheap AI generation")
        return {
            **event,
            'error': str(e),
            'generatedTitle': "Session Complete! ✨",
            'generatedBadge': "✨ Progress Maker",
            'aiEnhanced': False
        }


def convert_ddb_to_stop_pulse(pulse_data: Dict[str, Any]) -> StopPulse:
    """Convert DynamoDB format pulse data to StopPulse model"""
    
    def get_ddb_value(key: str, default=None):
        """Extract value from DynamoDB attribute format"""
        if key in pulse_data:
            attr = pulse_data[key]
            if isinstance(attr, dict):
                if 'S' in attr:
                    return attr['S']
                elif 'N' in attr:
                    return float(attr['N'])
                elif 'BOOL' in attr:
                    return attr['BOOL']
                elif 'NULL' in attr:
                    return None
            return attr
        return default
    
    # Extract all required fields
    converted_data = {
        'pulse_id': get_ddb_value('pulse_id'),
        'user_id': get_ddb_value('user_id'),
        'intent': get_ddb_value('intent'),
        'reflection': get_ddb_value('reflection'),
        'start_time': get_ddb_value('start_time'),
        'stopped_at': get_ddb_value('stopped_at'),
        'duration_seconds': get_ddb_value('duration_seconds'),
        'intent_emotion': get_ddb_value('intent_emotion'),
        'reflection_emotion': get_ddb_value('reflection_emotion'),
        'is_public': get_ddb_value('is_public', False),
        'tags': get_ddb_value('tags')
    }
    
    # Remove None values
    converted_data = {k: v for k, v in converted_data.items() if v is not None}
    
    return StopPulse(**converted_data)