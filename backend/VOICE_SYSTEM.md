# 🎤 Voice Control System - Complete Guide

## Overview

Grok-Pilot supports **voice control via phone calls** using Twilio. Call a phone number, speak commands, and the drone responds with voice feedback!

## 🏗️ Architecture

```
┌──────────────┐
│   You Call   │ "Take off and fly forward"
│  Phone Number│
└──────┬───────┘
       │ Voice
       ↓
┌──────────────────┐
│  Twilio Service  │ (Speech-to-Text)
│   (Cloud-based)  │
└──────┬───────────┘
       │ HTTP Webhook (text)
       ↓
┌────────────────────────────┐
│  POST /voice/webhook       │
│  (server/routes/voice.py)  │
└────────┬───────────────────┘
       │ Text command
       ↓
┌──────────────────────────┐
│   Grok AI (grok-4-1)     │ "takeoff() + wait(2) + look()"
│   Tool Selection Engine  │
└────────┬─────────────────┘
       │ Tool calls
       ↓
┌──────────────────────────┐
│  Execute Tools           │
│  - Drone movement        │
│  - Vision analysis       │
│  - Status checks         │
└────────┬─────────────────┘
       │ Results
       ↓
┌──────────────────────────┐
│  Format TwiML Response   │ <Say>Taking off! I see a tree.</Say>
│  (Text-to-Speech markup) │
└────────┬─────────────────┘
       │ TwiML XML
       ↓
┌──────────────────────────┐
│  Twilio TTS Engine       │
│  (Speaks response)       │
└────────┬─────────────────┘
       │ Audio
       ↓
┌──────────────┐
│   You Hear   │ "Taking off! I see a tree."
│   Response   │
└──────────────┘
```

## 📞 How Voice Calls Work

### 1. Phone Setup (Twilio)
You need a Twilio phone number configured to call your webhook:

```
Twilio Phone Number Settings:
  Voice & Fax → Configure With:
    Webhook URL: https://your-server.com/voice/webhook
    HTTP Method: POST
```

### 2. Call Flow

**Step 1: You Call**
```
User: *dials Twilio number*
Twilio: Answers call, starts recording
```

**Step 2: You Speak**
```
User: "Take off and look around"
Twilio: Converts speech to text using ASR (Automatic Speech Recognition)
```

**Step 3: Webhook Triggered**
```http
POST /voice/webhook HTTP/1.1
Host: your-server.com
Content-Type: application/x-www-form-urlencoded

SpeechResult=take+off+and+look+around&
Confidence=0.95&
CallSid=CA1234567890
```

**Step 4: Grok Processes Command**
```python
# server/routes/voice.py processes this
text = "take off and look around"
↓
Grok AI: Analyzes intent
↓
Tool Calls:
  1. takeoff()
  2. wait(2)
  3. look_around()
↓
Results: "Drone airborne at 50cm. I see trees ahead, buildings to the right..."
```

**Step 5: TwiML Response**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">
        Taking off! Rising to 50cm. I can see trees ahead, 
        buildings to the right, and a parking lot behind.
    </Say>
    <Pause length="1"/>
    <Gather input="speech" timeout="5" action="/voice/webhook">
        <Say>What's your next command?</Say>
    </Gather>
</Response>
```

**Step 6: You Hear Response**
```
Twilio: Speaks the response using Text-to-Speech
User: Hears "Taking off! Rising to 50cm..."
```

**Step 7: Continuous Conversation**
```
Twilio: "What's your next command?"
User: "Search for a person wearing red"
[Loop back to Step 2]
```

## 💻 Code Implementation

### Voice Route Handler
Located in `server/routes/voice.py`:

```python
@voice_bp.route('/webhook/', methods=['POST'])
def handle_voice():
    """Handle Twilio voice webhook - voice command execution"""
    
    # 1. Get speech-to-text result from Twilio
    speech_result = request.form.get('SpeechResult', '')
    confidence = float(request.form.get('Confidence', 0))
    
    log.info(f"🎤 Voice command: '{speech_result}' (confidence: {confidence:.2f})")
    
    # 2. Safety check
    if confidence < 0.5:
        return _create_twiml_response(
            "I didn't understand that clearly. Can you repeat?"
        )
    
    # 3. Emergency stop detection
    if any(word in speech_result.lower() for word in ['stop', 'halt', 'emergency', 'abort']):
        ABORT_FLAG.set()
        return _create_twiml_response(
            "Emergency stop activated! Hovering in place."
        )
    
    # 4. Call Grok AI with tools
    messages = [
        {"role": "system", "content": DRONE_PILOT_SYSTEM_PROMPT},
        {"role": "user", "content": speech_result}
    ]
    
    result = current_app.grok.chat_with_tools(
        messages=messages,
        tools=current_app.tools.get_openai_functions()
    )
    
    # 5. Execute tool calls
    tool_results = []
    for tool_call in result.get('tool_calls', []):
        tool_name = tool_call['name']
        tool_args = tool_call['arguments']
        
        tool_result = current_app.tools.execute(tool_name, **tool_args)
        tool_results.append(tool_result)
    
    # 6. Format response for speech
    response_text = _format_for_speech(result, tool_results)
    
    # 7. Return TwiML (XML for Twilio)
    return _create_twiml_response(response_text)
```

### TwiML Response Generator
```python
def _create_twiml_response(message: str, gather_next: bool = True) -> str:
    """Create TwiML response for Twilio"""
    
    response = VoiceResponse()  # Twilio TwiML object
    
    # Speak the message
    response.say(
        message,
        voice='alice',  # Voice options: alice, man, woman
        language='en-US'
    )
    
    # Add pause for clarity
    response.pause(length=1)
    
    # Gather next command (keeps conversation going)
    if gather_next:
        gather = Gather(
            input='speech',
            timeout=5,
            speech_timeout='auto',
            action='/voice/webhook'
        )
        gather.say("What's your next command?")
        response.append(gather)
    
    return str(response)
```

## 🎛️ Twilio Configuration

### Required Environment Variables
```bash
# Add to your .env file
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+15551234567
```

### Webhook URL Setup

**Development (ngrok):**
```bash
# Install ngrok
brew install ngrok

# Start your server
python3 main.py

# In another terminal, expose it
ngrok http 5000

# Copy the URL (e.g., https://abc123.ngrok.io)
# Set in Twilio: https://abc123.ngrok.io/voice/webhook
```

**Production:**
```bash
# Use your actual domain
https://grokpilot.yourdomain.com/voice/webhook
```

### Twilio Dashboard Setup

1. **Buy a Phone Number**
   - Go to: Phone Numbers → Buy a Number
   - Select one with Voice capabilities
   - Cost: ~$1-2/month

2. **Configure Webhook**
   - Phone Numbers → Manage → Active Numbers
   - Click your number
   - Voice & Fax section:
     - "A call comes in" → Webhook
     - URL: `https://your-server.com/voice/webhook`
     - HTTP: POST
     - Save

3. **Test**
   - Call your Twilio number
   - Speak a command
   - Listen for response!

## 🎯 Example Voice Commands

### Simple Commands
```
You: "Take off"
Drone: "Taking off! Rising to 50cm."

You: "What do you see?"
Drone: "I see a white wall ahead and a window to the left."

You: "Move forward"
Drone: "Moving forward 50 centimeters!"

You: "Land"
Drone: "Landing safely. Mission complete!"
```

### Complex Commands
```
You: "Take off and fly forward 80 centimeters"
Drone: "Roger that! Taking off... now moving forward 80cm."

You: "Search for a person wearing red"
Drone: "Starting 360 degree search... Found them! Person in red 
       jacket at approximately 270 degrees, about 3 meters away."

You: "Fly in a square pattern"
Drone: "Executing square flight pattern... complete!"
```

### Emergency Commands
```
You: "STOP!" or "EMERGENCY!" or "ABORT!"
Drone: "Emergency stop activated! Hovering in place."
```

## 🎙️ Speech Recognition Tips

### For Best Recognition
- ✅ Speak clearly and at normal pace
- ✅ Use simple commands first
- ✅ Pause briefly after each command
- ✅ Say numbers clearly ("fifty centimeters")
- ✅ Use wake words: "drone", "grok"

### Common Issues
- ❌ Background noise → Use quiet environment
- ❌ Mumbling → Speak confidently
- ❌ Too fast → Slow down slightly
- ❌ Accent issues → Enunciate clearly

### Confidence Threshold
```python
# In voice.py
if confidence < 0.5:
    return "I didn't understand that clearly"
```

Twilio provides a confidence score (0.0-1.0):
- 0.9-1.0: Excellent recognition
- 0.7-0.9: Good recognition
- 0.5-0.7: Fair (might need confirmation)
- <0.5: Poor (ask user to repeat)

## 🔊 Text-to-Speech (TTS) Options

### Voice Options
```python
# In TwiML response
response.say(message, voice='alice')  # Female, US English
response.say(message, voice='man')    # Male, robotic
response.say(message, voice='woman')  # Female, robotic
```

### Language Options
```python
response.say(message, language='en-US')   # US English
response.say(message, language='en-GB')   # British English
response.say(message, language='es-ES')   # Spanish
```

### Speech Rate & Pitch
```xml
<!-- Use SSML for advanced control -->
<Say>
    <prosody rate="fast">I'm speaking quickly!</prosody>
    <prosody pitch="+10%">Higher pitch voice!</prosody>
</Say>
```

## 🔧 Advanced Features

### 1. Multi-Turn Conversations
Voice system maintains context across multiple exchanges:

```python
# Store conversation history
conversation_history[call_sid] = {
    'messages': [],
    'last_command': '',
    'drone_state': {}
}

# Add to history
conversation_history[call_sid]['messages'].append({
    'role': 'user',
    'content': speech_result
})
```

### 2. Interrupt Handling
User can interrupt during drone operations:

```python
# ABORT_FLAG is checked every 100ms in all operations
if ABORT_FLAG.is_set():
    return "Stopping current operation!"
```

### 3. Status Announcements
Proactive updates during operations:

```python
# During search
"Checking angle 45 degrees... nothing yet"
"Checking angle 90 degrees... still searching"
"Found target at 135 degrees!"
```

## 📊 Voice System Flow Diagram

```
┌─────────────────────────────────────────────────┐
│           VOICE COMMAND LIFECYCLE               │
└─────────────────────────────────────────────────┘

1. INCOMING CALL
   ↓
2. TWILIO GREETING
   "Grok-Pilot ready. What's your command?"
   ↓
3. LISTEN FOR SPEECH (5 second timeout)
   ↓
4. SPEECH-TO-TEXT CONVERSION
   Audio → Text + Confidence Score
   ↓
5. CONFIDENCE CHECK
   < 0.5? → Ask to repeat
   ≥ 0.5? → Continue
   ↓
6. EMERGENCY CHECK
   "stop/halt/emergency" → ABORT
   Normal command → Continue
   ↓
7. GROK AI PROCESSING
   Text → Tool Selection → Parameters
   ↓
8. TOOL EXECUTION
   Execute each tool in sequence
   Collect results
   ↓
9. RESPONSE GENERATION
   Format results for speech
   Convert to natural language
   ↓
10. TWIML RESPONSE
    XML with <Say> and <Gather>
    ↓
11. TEXT-TO-SPEECH
    Twilio speaks response
    ↓
12. GATHER NEXT COMMAND
    Loop back to step 3
```

## 🚀 Quick Start

### 1. Install Twilio SDK
```bash
pip3 install twilio
```

### 2. Set Environment Variables
```bash
export TWILIO_ACCOUNT_SID=ACxxxxxxxxx
export TWILIO_AUTH_TOKEN=your_token
export TWILIO_PHONE_NUMBER=+15551234567
```

### 3. Start Server with Public URL
```bash
# Start server
python3 main.py

# In another terminal, expose with ngrok
ngrok http 5000

# Note the URL: https://abc123.ngrok.io
```

### 4. Configure Twilio Webhook
- Go to Twilio Console
- Your number → Voice Configuration
- Webhook: `https://abc123.ngrok.io/voice/webhook`
- Method: POST
- Save

### 5. Call and Test!
```
Dial your Twilio number
Say: "Take off"
Listen: "Taking off! Rising to 50cm."
Say: "What do you see?"
Listen: [Grok describes the view]
```

## 🎉 Complete!

You now have a fully voice-controlled AI drone! The system uses:
- **Twilio** for voice calls & STT/TTS
- **grok-4-1-fast-reasoning** for smart command understanding
- **Structured outputs** for reliable parsing
- **Tool calling** for precise drone control
- **Continuous conversation** with context awareness

**This is production-ready AI voice control! 🚁🎤**
