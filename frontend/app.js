// API Configuration
const API_BASE_URL = 'http://localhost:3000';
const BACKEND_API_URL = 'https://api.example.com/tasks'; // Placeholder backend URL

// DOM Elements
const recordBtn = document.getElementById('recordBtn');
const btnText = recordBtn.querySelector('.btn-text');
const status = document.getElementById('status');
const transcriptSection = document.getElementById('transcriptSection');
const transcript = document.getElementById('transcript');
const loadingSection = document.getElementById('loadingSection');
const streamSection = document.getElementById('streamSection');
const mjpegStream = document.getElementById('mjpegStream');
const streamError = document.getElementById('streamError');

// State
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let stream = null;
let currentStreamUrl = null;

// Initialize
async function init() {
    recordBtn.addEventListener('click', toggleRecording);
    updateStatus('Ready to record', false);
}

// Toggle recording
async function toggleRecording() {
    if (!isRecording) {
        await startRecording();
    } else {
        await stopRecording();
    }
}

// Start recording
async function startRecording() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });

        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            await processAudio();
        };

        mediaRecorder.start();
        isRecording = true;
        
        recordBtn.classList.add('recording');
        btnText.textContent = 'Stop Recording';
        updateStatus('Recording...', true);
        transcriptSection.classList.add('hidden');
        loadingSection.classList.add('hidden');
    } catch (error) {
        console.error('Error starting recording:', error);
        updateStatus('Error: Could not access microphone', false);
        alert('Please allow microphone access to use this feature.');
    }
}

// Stop recording
async function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        stream.getTracks().forEach(track => track.stop());
        isRecording = false;
        
        recordBtn.classList.remove('recording');
        btnText.textContent = 'Start Recording';
        updateStatus('Processing...', false);
        loadingSection.classList.remove('hidden');
        
        // Optionally stop stream when starting a new recording
        // stopMJPEGStream();
    }
}

// Process audio
async function processAudio() {
    try {
        // Create audio blob
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        
        // Send to backend for transcription (backend will handle format conversion)
        const transcriptionText = await transcribeAudio(audioBlob);
        
        // Display transcription
        transcript.textContent = transcriptionText;
        transcriptSection.classList.remove('hidden');
        loadingSection.classList.add('hidden');
        updateStatus('Transcription complete', false, true);
        
        // Show content grid when transcript is ready
        const contentGrid = document.querySelector('.content-grid');
        if (contentGrid) {
            contentGrid.style.display = 'grid';
        }
        
        // Send to backend API (placeholder)
        await sendToBackend(transcriptionText);
        
    } catch (error) {
        console.error('Error processing audio:', error);
        updateStatus('Error processing audio', false);
        loadingSection.classList.add('hidden');
        alert('Failed to process audio. Please try again.');
    }
}

// Transcribe audio using xAI STT API via backend
async function transcribeAudio(audioBlob) {
    const formData = new FormData();
    // Use appropriate filename based on blob type
    const filename = audioBlob.type.includes('webm') ? 'recording.webm' : 'recording.wav';
    formData.append('file', audioBlob, filename);
    
    const response = await fetch(`${API_BASE_URL}/api/transcribe`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Transcription failed');
    }
    
    const result = await response.json();
    return result.text;
}

// Send transcription to backend API and handle MJPEG stream
async function sendToBackend(text) {
    try {
        // This is a placeholder - you can replace with your actual backend URL
        const response = await fetch(BACKEND_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                task: text,
                timestamp: new Date().toISOString()
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('Task sent to backend successfully');
            
            // Check if backend returned an MJPEG stream URL
            if (data.stream_url || data.mjpeg_url || data.streamUrl) {
                const streamUrl = data.stream_url || data.mjpeg_url || data.streamUrl;
                displayMJPEGStream(streamUrl);
            }
        } else {
            console.warn('Backend API call failed (this is expected with placeholder URL)');
        }
    } catch (error) {
        // Silently fail for placeholder URL
        console.log('Backend API call skipped (placeholder URL)');
    }
}

// Display MJPEG stream
function displayMJPEGStream(streamUrl) {
    if (!streamUrl) {
        console.error('No stream URL provided');
        return;
    }
    
    // Stop any existing stream
    stopMJPEGStream();
    
    // Hide placeholder
    const streamPlaceholder = document.getElementById('streamPlaceholder');
    if (streamPlaceholder) {
        streamPlaceholder.classList.add('hidden');
    }
    
    // Add cache-busting parameter to ensure stream updates
    const separator = streamUrl.includes('?') ? '&' : '?';
    const streamUrlWithCache = `${streamUrl}${separator}_t=${Date.now()}`;
    
    currentStreamUrl = streamUrlWithCache;
    
    // Set up error handling
    mjpegStream.onerror = () => {
        console.error('Error loading MJPEG stream');
        streamError.classList.remove('hidden');
        mjpegStream.classList.add('hidden');
        if (streamPlaceholder) {
            streamPlaceholder.classList.add('hidden');
        }
    };
    
    mjpegStream.onload = () => {
        streamError.classList.add('hidden');
        mjpegStream.classList.remove('hidden');
        if (streamPlaceholder) {
            streamPlaceholder.classList.add('hidden');
        }
    };
    
    // Start the stream
    mjpegStream.src = streamUrlWithCache;
    mjpegStream.classList.remove('hidden');
    
    console.log('MJPEG stream started:', streamUrl);
}

// Stop MJPEG stream
function stopMJPEGStream() {
    if (mjpegStream.src) {
        mjpegStream.src = '';
        currentStreamUrl = null;
    }
    mjpegStream.classList.add('hidden');
    streamError.classList.add('hidden');
    
    // Show placeholder again
    const streamPlaceholder = document.getElementById('streamPlaceholder');
    if (streamPlaceholder) {
        streamPlaceholder.classList.remove('hidden');
    }
}

// Update status message
function updateStatus(message, isRecording, isSuccess = false) {
    status.textContent = message;
    status.classList.remove('hidden', 'recording', 'success');
    
    if (isRecording) {
        status.classList.add('recording');
    } else if (isSuccess) {
        status.classList.add('success');
    }
}

// Initialize on load
init();

// Export function to manually set stream URL (useful for testing or direct stream access)
window.setMJPEGStream = function(streamUrl) {
    displayMJPEGStream(streamUrl);
};

// Export function to stop stream
window.stopMJPEGStream = stopMJPEGStream;

