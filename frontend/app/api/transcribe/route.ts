/**
 * Next.js API Route for audio transcription
 * Proxies requests to xAI STT API
 */

import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

const XAI_API_KEY = process.env.XAI_API_KEY || '';
const XAI_API_URL = process.env.XAI_API_URL || 'https://api.x.ai/v1/audio/transcriptions';

export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    // Check for API key
    if (!XAI_API_KEY) {
      return NextResponse.json(
        { error: 'XAI_API_KEY not configured. Please set it in your .env.local file.' },
        { status: 500 }
      );
    }

    // Parse form data
    const formData = await request.formData();
    const file = formData.get('file') as File | null;

    if (!file) {
      return NextResponse.json(
        { error: 'No audio file provided' },
        { status: 400 }
      );
    }

    console.log(`📝 Transcribing audio file: ${file.name} (${file.size} bytes)`);

    // Convert File to Buffer
    const buffer = Buffer.from(await file.arrayBuffer());

    // Create form data for xAI API
    const xaiFormData = new FormData();
    const blob = new Blob([buffer], { type: file.type });
    xaiFormData.append('file', blob, file.name);

    // Make request to xAI API
    const response = await axios.post(XAI_API_URL, xaiFormData, {
      headers: {
        'Authorization': `Bearer ${XAI_API_KEY}`,
        'Content-Type': 'multipart/form-data',
      },
    });

    const transcription = response.data.text;
    console.log(`✅ Transcription complete: ${transcription.substring(0, 50)}...`);

    return NextResponse.json({ text: transcription });
  } catch (error) {
    console.error('❌ Transcription error:', error);

    if (axios.isAxiosError(error) && error.response) {
      return NextResponse.json(
        {
          error: error.response.data?.error?.message || 'Transcription failed',
          details: error.response.data,
        },
        { status: error.response.status }
      );
    }

    return NextResponse.json(
      {
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
