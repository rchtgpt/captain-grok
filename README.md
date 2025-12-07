# captain-grok 

Voice-to-text web app using xAI's Speech-to-Text API with real-time MJPEG stream display.

## Quick Start

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Configure environment:
   Create a `.env` file in the root directory:
   ```
   XAI_API_KEY=your_api_key_here
   ```

3. Start server:
   ```bash
   cd frontend
   npm start
   ```

4. Open `http://localhost:3000`

## Usage

1. Click "Start Recording"
2. Speak your task
3. Click "Stop Recording"
4. Transcription is sent to backend API
5. MJPEG stream displays automatically if returned by backend

## Configuration

**Backend API URL** - Edit `frontend/app.js`:
```javascript
const BACKEND_API_URL = 'https://your-api.com/tasks';
```

**Backend Response** - Should include stream URL:
```json
{
  "stream_url": "http://your-backend.com/stream.mjpeg"
}
```

**Port** - Set `PORT` environment variable:
```bash
PORT=8080 npm start
```

## API

**POST `/api/transcribe`**
- Body: Audio file (multipart/form-data)
- Response: `{ "text": "transcribed text" }`

## Project Structure

```
frontend/
├── index.html
├── styles.css
├── app.js
├── server.js
├── package.json
└── package-lock.json
```

## Requirements

- Node.js 18+
- xAI API key
- Microphone permissions
