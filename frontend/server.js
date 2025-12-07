/**
 * Backend server for Voice Task Assistant
 * Proxies audio transcription requests to xAI STT API
 */

const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });
const express = require('express');
const multer = require('multer');
const FormData = require('form-data');
const axios = require('axios');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;
const XAI_API_KEY = process.env.XAI_API_KEY || '';
const XAI_API_URL = process.env.XAI_API_URL || 'https://api.x.ai/v1/audio/transcriptions';

// Middleware
app.use(cors());
app.use(express.json());

// Serve static files from current directory (frontend folder)
app.use(express.static(__dirname));

// Configure multer for file uploads
const upload = multer({
    storage: multer.memoryStorage(),
    limits: {
        fileSize: 25 * 1024 * 1024 // 25MB limit
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'ok', service: 'Voice Task Assistant Backend' });
});

// Transcription endpoint
app.post('/api/transcribe', upload.single('file'), async (req, res) => {
    try {
        if (!XAI_API_KEY) {
            return res.status(500).json({ 
                error: 'XAI_API_KEY not configured. Please set it in your .env file.' 
            });
        }

        if (!req.file) {
            return res.status(400).json({ error: 'No audio file provided' });
        }

        console.log(`📝 Transcribing audio file: ${req.file.originalname} (${req.file.size} bytes)`);

        // Create form data for xAI API
        const formData = new FormData();
        formData.append('file', req.file.buffer, {
            filename: req.file.originalname || 'audio.wav',
            contentType: req.file.mimetype || 'audio/wav'
        });

        // Optional: Add model parameter if needed
        // formData.append('model', 'whisper-1');

        // Make request to xAI API
        const response = await axios.post(XAI_API_URL, formData, {
            headers: {
                'Authorization': `Bearer ${XAI_API_KEY}`,
                ...formData.getHeaders()
            }
        });

        const transcription = response.data.text;
        console.log(`✅ Transcription complete: ${transcription.substring(0, 50)}...`);

        res.json({ text: transcription });
    } catch (error) {
        console.error('❌ Transcription error:', error.response?.data || error.message);
        
        if (error.response) {
            res.status(error.response.status).json({ 
                error: error.response.data?.error?.message || 'Transcription failed',
                details: error.response.data 
            });
        } else {
            res.status(500).json({ 
                error: 'Internal server error',
                details: error.message 
            });
        }
    }
});

// Serve index.html for root route
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Start server
app.listen(PORT, () => {
    console.log('='.repeat(60));
    console.log('🚀 Voice Task Assistant Backend');
    console.log('='.repeat(60));
    console.log(`🌐 Server running on http://localhost:${PORT}`);
    console.log(`🔑 API Key: ${XAI_API_KEY ? '✅ Configured' : '❌ Missing (set XAI_API_KEY in .env)'}`);
    console.log(`📡 xAI API: ${XAI_API_URL}`);
    console.log('='.repeat(60));
    
    if (!XAI_API_KEY) {
        console.log('\n⚠️  WARNING: XAI_API_KEY not set!');
        console.log('   Create a .env file with: XAI_API_KEY=your_api_key_here\n');
    }
});

