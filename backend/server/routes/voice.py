"""
Voice input routes for Grok-Pilot.
Handles Twilio webhooks and voice commands.
"""

from flask import Blueprint, request, jsonify, current_app
from core.logger import get_logger
from utils.helpers import is_abort_keyword

voice_bp = Blueprint('voice', __name__)
log = get_logger('routes.voice')


@voice_bp.route('/webhook', methods=['POST'])
def twilio_webhook():
    """
    Handle Twilio webhook with voice transcription.
    
    Expected form data:
        SpeechResult: Transcribed text from user
    
    Response:
        TwiML for text-to-speech response
    """
    try:
        # Get transcription from Twilio form data
        speech_result = request.form.get('SpeechResult', '').strip()
        
        if not speech_result:
            return generate_twiml("Sorry, I didn't catch that. Please try again.")
        
        log.info(f"Voice command: {speech_result}")
        
        # Check for abort keywords
        if is_abort_keyword(speech_result):
            log.warning("Abort keyword detected in voice command")
            current_app.events.publish('abort', {'source': 'voice'})
            current_app.drone.emergency_stop()
            return generate_twiml("Emergency stop activated! Drone is hovering.")
        
        # Process command with Grok
        messages = [
            {"role": "user", "content": speech_result}
        ]
        
        result = current_app.grok.chat_with_tools(
            messages=messages,
            tools=current_app.tools.get_schemas()
        )
        
        # Execute tool calls
        if result.get('tool_calls'):
            for call in result['tool_calls']:
                current_app.tools.execute(call['name'], **call['arguments'])
        
        # Return spoken response
        response_text = result.get('response', 'Command received.')
        return generate_twiml(response_text)
    
    except Exception as e:
        log.error(f"Voice webhook error: {e}")
        return generate_twiml("Sorry, I encountered an error processing your command.")


@voice_bp.route('/test', methods=['POST'])
def test_voice():
    """
    Test voice endpoint (for testing without Twilio).
    
    Request JSON:
        {
            "text": "take off and look around"
        }
    
    Response JSON:
        {
            "response": "...",
            "tool_calls": [...]
        }
    """
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'Missing text field'}), 400
        
        # Check abort
        if is_abort_keyword(text):
            current_app.drone.emergency_stop()
            return jsonify({
                'status': 'aborted',
                'response': 'Emergency stop activated'
            })
        
        # Process with Grok
        result = current_app.grok.chat_with_tools(
            messages=[{"role": "user", "content": text}],
            tools=current_app.tools.get_schemas()
        )
        
        # Execute tools
        tool_results = []
        if result.get('tool_calls'):
            for call in result['tool_calls']:
                tool_result = current_app.tools.execute(call['name'], **call['arguments'])
                tool_results.append({
                    'tool': call['name'],
                    'success': tool_result.success,
                    'message': tool_result.message
                })
        
        return jsonify({
            'response': result.get('response', ''),
            'tool_results': tool_results
        })
    
    except Exception as e:
        log.error(f"Test voice error: {e}")
        return jsonify({'error': str(e)}), 500


def generate_twiml(text):
    """
    Generate TwiML response for Twilio.
    
    Args:
        text: Text to speak
        
    Returns:
        TwiML XML response
    """
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>{text}</Say>
</Response>'''
    
    from flask import Response
    return Response(twiml, mimetype='text/xml')
