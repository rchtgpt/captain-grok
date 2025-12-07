# ⚡ Quick Reference Card

## 🚀 Start Server
```bash
python3 main.py --mock              # Mock drone (safe testing)
python3 main.py                     # Real drone
python3 main.py --mock --no-window  # No video window
```

## 🎤 Voice Setup (Twilio)
```bash
# 1. Expose server (default port: 8080)
ngrok http 8080

# 2. Configure Twilio webhook
https://YOUR-NGROK-URL.ngrok.io/voice/webhook

# 3. Call your Twilio number and speak!
```

## 🧠 Models (Update .env)
```bash
# BEST (reasoning + smart)
XAI_MODEL=grok-4-1-fast-reasoning
XAI_VISION_MODEL=grok-2-vision-1212

# FASTEST (no reasoning)
XAI_MODEL=grok-4-1-fast-non-reasoning
XAI_VISION_MODEL=grok-2-vision-1212
```

## 📡 API Endpoints
```bash
# Command execution (default port: 8080)
POST http://localhost:8080/command/
Body: {"text": "take off"}

# Status
GET http://localhost:8080/status/

# Emergency stop
POST http://localhost:8080/status/abort/

# Voice webhook (Twilio)
POST http://localhost:8080/voice/webhook/

# Video stream
GET http://localhost:8080/video/stream/
```

## 🛠️ Tool Categories

**Flight** (6): takeoff, land, move, rotate, flip, hover
**Vision** (4): look, analyze, search, look_around
**System** (5): get_status, wait, emergency_stop, say, clear_abort

## 💬 Example Commands

**Via REST API:**
```bash
# Correct format: single curly braces {} and trailing slash
curl -X POST http://localhost:8080/command/ \
  -H 'Content-Type: application/json' \
  -d '{"text": "take off and look around"}'

# Common mistakes:
# ❌ {{"text": ...}}  - Double braces (invalid JSON)
# ❌ /command         - Missing trailing slash
# ✅ {"text": ...}    - Single braces (correct)
# ✅ /command/        - With trailing slash
```

**Via Voice Call:**
- "Take off"
- "What do you see?"
- "Search for a person wearing red"
- "Fly forward 50 centimeters"
- "STOP!" (emergency)

## 📊 Structured Output Example
```python
# Vision analysis returns:
VisionAnalysis(
    summary="Person ahead, building behind",
    objects_detected=[
        VisionObject(
            name="person",
            description="Red jacket",
            estimated_distance="3 meters",
            confidence="high"
        )
    ],
    hazards=[],
    lighting_conditions="bright"
)
```

## 🔍 Watch Logs For

```
📊 Extended Thinking Detected    # AI reasoning visible
🧠 GROK EXTENDED THINKING        # Thought process
🔍 Analyzing scene              # Vision analysis
✅ SUCCESS                       # Operations succeed
❌ ERROR                         # Problems
```

## ⚠️ Safety Limits

- Max height: 200cm
- Movement: 20-100cm per move
- Battery warning: <20%
- ABORT_FLAG: Checked every 100ms

## 📚 Documentation Files

1. **FINAL_SUMMARY.md** - Complete overview (START HERE!)
2. **VOICE_SYSTEM.md** - Voice control guide
3. **STRUCTURED_OUTPUTS_GUIDE.md** - Schema details
4. **README.md** - Project documentation
5. **QUICK_REFERENCE.md** - This file!

## 🎯 Common Tasks

### Test Function Calling
```bash
# 1. Start server
python3 main.py --mock

# 2. Send command (use single braces {} and trailing slash)
curl -X POST http://localhost:8080/command/ \
  -H 'Content-Type: application/json' \
  -d '{"text": "take off and move forward 30 centimeters"}'

# 3. Check logs - should see:
# - Tool calls: takeoff(), wait(), move()
# - Extended thinking (if using reasoning model)
```

### Test Voice
```bash
# 1. Expose server (default port: 8080)
ngrok http 8080
# Copy URL: https://abc123.ngrok.io

# 2. Configure Twilio
# Webhook: https://abc123.ngrok.io/voice/webhook

# 3. Call Twilio number
# Say: "Take off and tell me what you see"
```

### Test Structured Outputs
```bash
# Check ai/schemas.py for all 11 schemas
# Vision tools automatically return structured data
curl -X POST http://localhost:8080/command/ \
  -H 'Content-Type: application/json' \
  -d '{"text": "what do you see?"}'

# Response includes structured VisionAnalysis object!
```

## 🏆 Production Checklist

- [x] grok-4-1-fast-reasoning model configured
- [x] Structured outputs implemented (11 schemas)
- [x] Extended thinking support added
- [x] Voice control ready (Twilio)
- [x] 15 tools registered
- [x] System prompt optimized
- [x] Safety checks in place
- [x] Documentation complete

## 🔥 Demo Commands

**Show Intelligence:**
```
"take off and fly in a square pattern"
→ Chains multiple tools: takeoff + 4x(move + rotate)
```

**Show Vision:**
```
"take off and tell me what you see"
→ Structured VisionAnalysis with objects, hazards, etc.
```

**Show Search:**
```
"search for a person wearing red"
→ 360° rotation + vision analysis at each angle
```

**Show Reasoning (with grok-4-1-fast-reasoning):**
```
Any command → Check logs for "🧠 GROK EXTENDED THINKING"
→ See AI's step-by-step thought process!
```

## ⚡ That's It!

**Everything you need to know in one page!**

For details, see:
- FINAL_SUMMARY.md (complete overview)
- VOICE_SYSTEM.md (Twilio setup)
- STRUCTURED_OUTPUTS_GUIDE.md (schemas)
