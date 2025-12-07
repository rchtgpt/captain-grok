/**
 * API client for audio transcription and backend drone commands
 */

import type { 
  TranscriptionResponse, 
  BackendTaskResponse,
  MemoryResponse,
  Person,
  MemoryObject,
  EntitySnapshot,
  MemoryStats,
  DroneStatus,
  SystemStatus,
  ConfidenceLevel,
  FramePosition,
  Target,
  TargetsResponse,
  TargetStatus
} from '@/app/types';

// Backend server URL - the drone command API runs on port 8080
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';

/**
 * Transcribes audio using the local Next.js API route
 * which proxies to the xAI speech-to-text API
 * 
 * @param audioBlob - The recorded audio blob
 * @returns The transcribed text
 */
export async function transcribeAudio(audioBlob: Blob): Promise<string> {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.webm');

  const response = await fetch('/api/transcribe', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Transcription failed');
  }

  const data: TranscriptionResponse = await response.json();
  return data.text;
}

/**
 * Sends the transcribed text to the backend drone command endpoint
 * 
 * @param text - The transcribed command text
 * @returns The backend response with potential stream URLs
 */
export async function sendToBackend(text: string): Promise<BackendTaskResponse> {
  const response = await fetch(`${BACKEND_URL}/command/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Backend command failed');
  }

  return response.json();
}

// ============================================================================
// Memory API - Access drone's spatial memory
// ============================================================================

/**
 * Helper to convert snake_case to camelCase
 */
function toCamelCase(obj: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const key in obj) {
    const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
    const value = obj[key];
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      result[camelKey] = toCamelCase(value as Record<string, unknown>);
    } else if (Array.isArray(value)) {
      result[camelKey] = value.map(item => 
        typeof item === 'object' && item !== null 
          ? toCamelCase(item as Record<string, unknown>) 
          : item
      );
    } else {
      result[camelKey] = value;
    }
  }
  return result;
}

/**
 * Map a raw person object from backend to Person type
 */
function mapPerson(p: Record<string, unknown>): Person {
  const raw = toCamelCase(p) as Record<string, unknown>;
  
  // Map snapshots with full URLs - backend uses snake_case: image_path, thumbnail_path
  const snapshots: EntitySnapshot[] = Array.isArray(raw.snapshots) 
    ? (raw.snapshots as Record<string, unknown>[]).map(s => {
        // Handle both snake_case (from backend) and camelCase
        const imagePath = (s.image_path as string) || (s.imagePath as string) || '';
        const thumbnailPath = (s.thumbnail_path as string) || (s.thumbnailPath as string) || '';
        const framePos = (s.frame_position as string) || (s.framePosition as string) || 'unknown';
        const heading = (s.drone_heading as number) || (s.droneHeading as number) || 0;
        
        return {
          imageUrl: imagePath ? `${BACKEND_URL}/memory/images/${imagePath.split('/').pop()}` : '',
          thumbnailUrl: thumbnailPath ? `${BACKEND_URL}/memory/images/${thumbnailPath.split('/').pop()}` : null,
          timestamp: (s.timestamp as string) || '',
          framePosition: framePos as FramePosition,
          droneHeading: heading
        };
      })
    : [];
  
  // Get thumbnail from first snapshot
  const thumbnailUrl = snapshots.length > 0 
    ? (snapshots[0].thumbnailUrl || snapshots[0].imageUrl || null)
    : null;
  
  return {
    id: (raw.id as string) || '',
    entityType: 'person',
    name: (raw.name as string) || null,
    description: (raw.description as string) || '',
    clothing: (raw.clothing as string) || null,
    hair: (raw.hair as string) || null,
    accessories: Array.isArray(raw.accessories) ? raw.accessories as string[] : [],
    distinctiveFeatures: Array.isArray(raw.distinguishingFeatures) ? raw.distinguishingFeatures as string[] : [],
    faceVisible: Boolean(raw.faceVisible),
    absoluteAngle: (raw.absoluteAngle as number) || 0,
    relativeAngle: (raw.relativeAngle as number) || 0,
    direction: (raw.direction as string) || 'unknown',
    estimatedDistanceCm: (raw.estimatedDistanceCm as number) || 0,
    confidence: (raw.confidence as ConfidenceLevel) || 'medium',
    firstSeen: (raw.firstSeen as string) || '',
    lastSeen: (raw.lastSeen as string) || '',
    sightings: (raw.timesSeen as number) || 1,
    snapshots,
    thumbnailUrl,
    targetId: (raw.targetId as string) || null
  };
}

/**
 * Map a raw object from backend to MemoryObject type
 */
function mapObject(o: Record<string, unknown>): MemoryObject {
  const raw = toCamelCase(o) as Record<string, unknown>;
  
  // Map snapshots with full URLs - backend uses snake_case: image_path, thumbnail_path
  const snapshots: EntitySnapshot[] = Array.isArray(raw.snapshots)
    ? (raw.snapshots as Record<string, unknown>[]).map(s => {
        // Handle both snake_case (from backend) and camelCase
        const imagePath = (s.image_path as string) || (s.imagePath as string) || '';
        const thumbnailPath = (s.thumbnail_path as string) || (s.thumbnailPath as string) || '';
        const framePos = (s.frame_position as string) || (s.framePosition as string) || 'unknown';
        const heading = (s.drone_heading as number) || (s.droneHeading as number) || 0;
        
        return {
          imageUrl: imagePath ? `${BACKEND_URL}/memory/images/${imagePath.split('/').pop()}` : '',
          thumbnailUrl: thumbnailPath ? `${BACKEND_URL}/memory/images/${thumbnailPath.split('/').pop()}` : null,
          timestamp: (s.timestamp as string) || '',
          framePosition: framePos as FramePosition,
          droneHeading: heading
        };
      })
    : [];
  
  const thumbnailUrl = snapshots.length > 0
    ? (snapshots[0].thumbnailUrl || snapshots[0].imageUrl || null)
    : null;
  
  const entityType = (raw.entityType as string) || 'object';
  
  return {
    id: (raw.id as string) || '',
    entityType: entityType as 'object' | 'furniture' | 'location',
    name: (raw.name as string) || null,
    description: (raw.description as string) || '',
    absoluteAngle: (raw.absoluteAngle as number) || 0,
    relativeAngle: (raw.relativeAngle as number) || 0,
    direction: (raw.direction as string) || 'unknown',
    estimatedDistanceCm: (raw.estimatedDistanceCm as number) || 0,
    confidence: (raw.confidence as ConfidenceLevel) || 'medium',
    firstSeen: (raw.firstSeen as string) || '',
    lastSeen: (raw.lastSeen as string) || '',
    sightings: (raw.timesSeen as number) || 1,
    snapshots,
    thumbnailUrl
  };
}

/**
 * Get full memory summary (people, objects, stats)
 */
export async function getMemory(): Promise<MemoryResponse> {
  const response = await fetch(`${BACKEND_URL}/memory/`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch memory');
  }
  
  const data = await response.json();
  
  // Map people and objects with proper type conversion
  const people: Person[] = Array.isArray(data.people) 
    ? data.people.map((p: Record<string, unknown>) => mapPerson(p))
    : [];
  
  const objects: MemoryObject[] = Array.isArray(data.objects)
    ? data.objects.map((o: Record<string, unknown>) => mapObject(o))
    : [];
  
  const stats: MemoryStats = {
    peopleCount: data.stats?.people_count || 0,
    objectsCount: data.stats?.objects_count || 0,
    entityCount: data.stats?.entity_count || 0,
    heading: data.stats?.heading || 0,
    position: data.stats?.position || { x: 0, y: 0, z: 0 }
  };
  
  return { people, objects, stats };
}

/**
 * Get all people in memory
 */
export async function getPeople(): Promise<Person[]> {
  const response = await fetch(`${BACKEND_URL}/memory/people`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch people');
  }
  
  const data = await response.json();
  return data.people.map((p: Record<string, unknown>) => {
    const person = toCamelCase(p) as unknown as Person;
    if (person.snapshots?.length > 0 && person.snapshots[0].thumbnailUrl) {
      person.thumbnailUrl = `${BACKEND_URL}${person.snapshots[0].thumbnailUrl}`;
    }
    return person;
  });
}

/**
 * Get a specific entity by ID
 */
export async function getEntity(entityId: string): Promise<Person | MemoryObject> {
  const response = await fetch(`${BACKEND_URL}/memory/entity/${entityId}`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Entity not found');
  }
  
  const data = await response.json();
  const entity = toCamelCase(data.entity) as unknown as Person | MemoryObject;
  
  // Map image URLs
  if (entity.snapshots) {
    entity.snapshots = entity.snapshots.map(s => ({
      ...s,
      imageUrl: s.imageUrl ? `${BACKEND_URL}${s.imageUrl}` : '',
      thumbnailUrl: s.thumbnailUrl ? `${BACKEND_URL}${s.thumbnailUrl}` : null
    }));
    if (entity.snapshots.length > 0) {
      entity.thumbnailUrl = entity.snapshots[0].thumbnailUrl || entity.snapshots[0].imageUrl;
    }
  }
  
  return entity;
}

/**
 * Get all images for an entity
 */
export async function getEntityImages(entityId: string): Promise<EntitySnapshot[]> {
  const response = await fetch(`${BACKEND_URL}/memory/entity/${entityId}/images`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch images');
  }
  
  const data = await response.json();
  return data.images.map((img: Record<string, unknown>) => ({
    imageUrl: img.image_url ? `${BACKEND_URL}${img.image_url}` : '',
    thumbnailUrl: img.thumbnail_url ? `${BACKEND_URL}${img.thumbnail_url}` : null,
    timestamp: img.timestamp as string,
    framePosition: (img.frame_position as string || 'unknown') as FramePosition,
    droneHeading: img.drone_heading as number
  }));
}

/**
 * Resolve a natural language reference to an entity
 */
export async function resolveReference(reference: string): Promise<{
  resolved: boolean;
  entity?: Person | MemoryObject;
  ambiguous?: boolean;
  matches?: (Person | MemoryObject)[];
  error?: string;
}> {
  const response = await fetch(`${BACKEND_URL}/memory/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reference })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to resolve reference');
  }
  
  const data = await response.json();
  
  if (data.resolved && data.entity) {
    return {
      resolved: true,
      entity: toCamelCase(data.entity) as unknown as Person | MemoryObject
    };
  }
  
  if (data.ambiguous && data.matches) {
    return {
      resolved: false,
      ambiguous: true,
      matches: data.matches.map((m: Record<string, unknown>) => 
        toCamelCase(m) as unknown as Person | MemoryObject
      )
    };
  }
  
  return {
    resolved: false,
    error: data.error
  };
}

/**
 * Get conversation history
 */
export async function getConversation(): Promise<Array<{ role: string; content: string }>> {
  const response = await fetch(`${BACKEND_URL}/memory/conversation`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch conversation');
  }
  
  const data = await response.json();
  return data.conversation;
}

/**
 * Reset memory (new session)
 */
export async function resetMemory(): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/memory/reset`, {
    method: 'POST'
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to reset memory');
  }
}

// ============================================================================
// Drone Control API - Status and Emergency Controls
// ============================================================================

/**
 * Get current drone and system status
 */
export async function getDroneStatus(): Promise<SystemStatus> {
  const response = await fetch(`${BACKEND_URL}/status/`);
  
  if (!response.ok) {
    // Return offline status if backend unavailable
    return {
      drone: {
        connected: false,
        flying: false,
        battery: 0,
        height: 0,
        temperature: 0,
        state: 'grounded'
      },
      system: {
        abortFlag: false,
        videoRunning: false,
        toolsCount: 0
      }
    };
  }
  
  const data = await response.json();
  
  return {
    drone: {
      connected: data.drone?.connected ?? false,
      flying: data.drone?.flying ?? false,
      battery: data.drone?.battery ?? 0,
      height: data.drone?.height ?? 0,
      temperature: data.drone?.temperature ?? 0,
      state: (data.drone?.state?.toLowerCase() ?? 'grounded') as SystemStatus['drone']['state']
    },
    system: {
      abortFlag: data.system?.abort_flag ?? false,
      videoRunning: data.system?.video_running ?? false,
      toolsCount: data.system?.tools_count ?? 0
    }
  };
}

/**
 * TAKEOFF - Launch the drone and rise to eye level
 */
export async function takeoff(): Promise<{ status: string; message: string; battery?: number }> {
  const response = await fetch(`${BACKEND_URL}/status/takeoff`, {
    method: 'POST'
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Takeoff failed');
  }
  
  return response.json();
}

/**
 * LAND - Land the drone safely (internal land command)
 */
export async function land(): Promise<{ status: string; message: string }> {
  const response = await fetch(`${BACKEND_URL}/status/land`, {
    method: 'POST'
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Land failed');
  }
  
  return response.json();
}

/**
 * EMERGENCY LAND - Land immediately wherever the drone is!
 * This is the panic button - lands RIGHT NOW.
 */
export async function emergencyLand(): Promise<{ status: string; message: string }> {
  const response = await fetch(`${BACKEND_URL}/status/emergency/land`, {
    method: 'POST'
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Emergency land failed');
  }
  
  return response.json();
}

/**
 * EMERGENCY STOP - Stop all movement and hover in place
 * Use this to abort current operation without landing.
 */
export async function emergencyStop(): Promise<{ status: string; message: string }> {
  const response = await fetch(`${BACKEND_URL}/status/abort`, {
    method: 'POST'
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Emergency stop failed');
  }
  
  return response.json();
}

/**
 * RETURN HOME - Fly back to takeoff position and land safely
 */
export async function returnHome(): Promise<{ status: string; message: string; distance_traveled?: number }> {
  const response = await fetch(`${BACKEND_URL}/status/return-home`, {
    method: 'POST'
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Return home failed');
  }
  
  return response.json();
}

/**
 * Clear abort flag to resume normal operations
 */
export async function clearAbort(): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/status/clear`, {
    method: 'POST'
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to clear abort');
  }
}

// ============================================================================
// Targets API - Facial recognition targets for search & rescue
// ============================================================================

/**
 * Map raw target from backend to Target type
 */
function mapTarget(t: Record<string, unknown>): Target {
  return {
    id: (t.id as string) || '',
    name: (t.name as string) || '',
    description: (t.description as string) || '',
    referencePhotos: Array.isArray(t.reference_photos) 
      ? (t.reference_photos as string[]).map(p => `${BACKEND_URL}/targets/${t.id}/reference/${p.split('/').pop()}`)
      : [],
    status: (t.status as TargetStatus) || 'searching',
    foundEntityId: (t.found_entity_id as string) || null,
    matchedPhotos: Array.isArray(t.matched_photos)
      ? (t.matched_photos as string[]).map(p => `${BACKEND_URL}/targets/${t.id}/matched/${p.split('/').pop()}`)
      : [],
    matchConfidence: (t.match_confidence as number) || 0,
    createdAt: (t.created_at as string) || '',
    foundAt: (t.found_at as string) || null
  };
}

/**
 * Get all targets
 */
export async function getTargets(): Promise<TargetsResponse> {
  const response = await fetch(`${BACKEND_URL}/targets/`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch targets');
  }
  
  const data = await response.json();
  
  return {
    targets: Array.isArray(data.targets) 
      ? data.targets.map((t: Record<string, unknown>) => mapTarget(t))
      : [],
    stats: {
      total: data.stats?.total || 0,
      found: data.stats?.found || 0,
      searching: data.stats?.searching || 0
    }
  };
}

/**
 * Get a single target by ID
 */
export async function getTarget(targetId: string): Promise<Target> {
  const response = await fetch(`${BACKEND_URL}/targets/${targetId}`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Target not found');
  }
  
  const data = await response.json();
  return mapTarget(data.target);
}

/**
 * Get a target by name
 */
export async function getTargetByName(name: string): Promise<Target | null> {
  const response = await fetch(`${BACKEND_URL}/targets/by-name/${encodeURIComponent(name)}`);
  
  if (!response.ok) {
    if (response.status === 404) return null;
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch target');
  }
  
  const data = await response.json();
  return mapTarget(data.target);
}

/**
 * Create a new target with reference photos
 */
export async function createTarget(
  name: string, 
  description: string, 
  photos: File[]
): Promise<Target> {
  const formData = new FormData();
  formData.append('name', name);
  formData.append('description', description);
  
  photos.forEach((photo) => {
    formData.append('photos', photo);
  });
  
  const response = await fetch(`${BACKEND_URL}/targets/`, {
    method: 'POST',
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to create target');
  }
  
  const data = await response.json();
  return mapTarget(data.target);
}

/**
 * Update a target
 */
export async function updateTarget(
  targetId: string,
  updates: { name?: string; description?: string; status?: TargetStatus }
): Promise<Target> {
  const response = await fetch(`${BACKEND_URL}/targets/${targetId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to update target');
  }
  
  const data = await response.json();
  return mapTarget(data.target);
}

/**
 * Delete a target
 */
export async function deleteTarget(targetId: string): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/targets/${targetId}`, {
    method: 'DELETE'
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to delete target');
  }
}

/**
 * Add more reference photos to a target
 */
export async function addTargetPhotos(targetId: string, photos: File[]): Promise<Target> {
  const formData = new FormData();
  
  photos.forEach((photo) => {
    formData.append('photos', photo);
  });
  
  const response = await fetch(`${BACKEND_URL}/targets/${targetId}/photos`, {
    method: 'POST',
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to add photos');
  }
  
  const data = await response.json();
  return mapTarget(data.target);
}

// ============================================================================
// Memory Naming API - Name entities from memory
// ============================================================================

/**
 * Name an entity in memory
 */
export async function nameEntity(entityId: string, name: string): Promise<Person | MemoryObject> {
  const response = await fetch(`${BACKEND_URL}/memory/entity/${entityId}/name`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to name entity');
  }
  
  const data = await response.json();
  const entity = toCamelCase(data.entity) as Record<string, unknown>;
  
  // Return as Person or MemoryObject based on entity_type
  if (entity.entityType === 'person') {
    return mapPerson(data.entity);
  }
  return mapObject(data.entity);
}

/**
 * Get an entity by name
 */
export async function getEntityByName(name: string): Promise<Person | MemoryObject | null> {
  const response = await fetch(`${BACKEND_URL}/memory/entity/by-name/${encodeURIComponent(name)}`);
  
  if (!response.ok) {
    if (response.status === 404) return null;
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch entity');
  }
  
  const data = await response.json();
  const entity = toCamelCase(data.entity) as Record<string, unknown>;
  
  if (entity.entityType === 'person') {
    return mapPerson(data.entity);
  }
  return mapObject(data.entity);
}

// ============================================================================
// Session API - Video recording sessions
// ============================================================================

export interface SessionStatus {
  recording: boolean;
  sessionId: string | null;
  manualMode: boolean;
  durationSeconds: number;
  frameCount: number;
  targetsFoundCount: number;
}

export interface SessionMetadata {
  sessionId: string;
  startTime: string;
  endTime: string;
  durationSeconds: number;
  frameCount: number;
  fps: number;
  resolution: [number, number];
  targetsFound: Array<{
    targetId: string;
    targetName: string;
    confidence: number;
    timestamp: string;
    frameNumber: number;
    thumbnail: string | null;
  }>;
  events: Array<{
    type: string;
    timestamp: string;
    frameNumber: number;
    data: Record<string, unknown>;
  }>;
  videoFile: string;
}

/**
 * Get current session recording status
 */
export async function getSessionStatus(): Promise<SessionStatus> {
  const response = await fetch(`${BACKEND_URL}/session/status`);
  
  if (!response.ok) {
    return {
      recording: false,
      sessionId: null,
      manualMode: false,
      durationSeconds: 0,
      frameCount: 0,
      targetsFoundCount: 0
    };
  }
  
  const data = await response.json();
  
  return {
    recording: data.recording || false,
    sessionId: data.session_id || null,
    manualMode: data.manual_mode || false,
    durationSeconds: data.duration_seconds || 0,
    frameCount: data.frame_count || 0,
    targetsFoundCount: data.targets_found_count || 0
  };
}

/**
 * Start a new recording session
 */
export async function startSession(manual: boolean = false): Promise<string> {
  const response = await fetch(`${BACKEND_URL}/session/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ manual })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to start session');
  }
  
  const data = await response.json();
  return data.session_id;
}

/**
 * Stop the current recording session
 */
export async function stopSession(): Promise<SessionMetadata | null> {
  const response = await fetch(`${BACKEND_URL}/session/stop`, {
    method: 'POST'
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to stop session');
  }
  
  const data = await response.json();
  if (!data.session) return null;
  
  const s = data.session;
  return {
    sessionId: s.session_id,
    startTime: s.start_time,
    endTime: s.end_time,
    durationSeconds: s.duration_seconds,
    frameCount: s.frame_count,
    fps: s.fps,
    resolution: s.resolution,
    targetsFound: s.targets_found || [],
    events: s.events || [],
    videoFile: s.video_file
  };
}

/**
 * List all recorded sessions
 */
export async function listSessions(): Promise<SessionMetadata[]> {
  const response = await fetch(`${BACKEND_URL}/sessions`);
  
  if (!response.ok) {
    return [];
  }
  
  const data = await response.json();
  
  return (data.sessions || []).map((s: Record<string, unknown>) => ({
    sessionId: s.session_id,
    startTime: s.start_time,
    endTime: s.end_time,
    durationSeconds: s.duration_seconds,
    frameCount: s.frame_count,
    fps: s.fps,
    resolution: s.resolution,
    targetsFound: s.targets_found || [],
    events: s.events || [],
    videoFile: s.video_file
  }));
}

/**
 * Get a single session by ID
 */
export async function getSession(sessionId: string): Promise<SessionMetadata | null> {
  const response = await fetch(`${BACKEND_URL}/session/${sessionId}`);
  
  if (!response.ok) {
    return null;
  }
  
  const data = await response.json();
  if (!data.session) return null;
  
  const s = data.session;
  return {
    sessionId: s.session_id,
    startTime: s.start_time,
    endTime: s.end_time,
    durationSeconds: s.duration_seconds,
    frameCount: s.frame_count,
    fps: s.fps,
    resolution: s.resolution,
    targetsFound: s.targets_found || [],
    events: s.events || [],
    videoFile: s.video_file
  };
}

/**
 * Get URL for session video download
 */
export function getSessionVideoUrl(sessionId: string): string {
  return `${BACKEND_URL}/session/${sessionId}/video`;
}

/**
 * Delete a session
 */
export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/session/${sessionId}`, {
    method: 'DELETE'
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to delete session');
  }
}

/**
 * Delete all sessions
 */
export async function deleteAllSessions(): Promise<number> {
  const response = await fetch(`${BACKEND_URL}/sessions`, {
    method: 'DELETE'
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to delete sessions');
  }
  
  const data = await response.json();
  return data.deleted_count || 0;
}

// ============================================================================
// Tailing API - Real-time person following
// ============================================================================

export interface TailingStatus {
  active: boolean;
  targetId: string | null;
  targetName: string | null;
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  } | null;
  confidence: number;
  lastSeen: number;
  framesTracked: number;
  framesLost: number;
}

/**
 * Get current tailing status
 */
export async function getTailingStatus(): Promise<TailingStatus> {
  const response = await fetch(`${BACKEND_URL}/tail/status`);
  
  if (!response.ok) {
    return {
      active: false,
      targetId: null,
      targetName: null,
      bbox: null,
      confidence: 0,
      lastSeen: 0,
      framesTracked: 0,
      framesLost: 0
    };
  }
  
  const data = await response.json();
  
  return {
    active: data.active || false,
    targetId: data.target_id || null,
    targetName: data.target_name || null,
    bbox: data.bbox || null,
    confidence: data.confidence || 0,
    lastSeen: data.last_seen || 0,
    framesTracked: data.frames_tracked || 0,
    framesLost: data.frames_lost || 0
  };
}

/**
 * Start tailing a target
 */
export async function startTailing(targetId: string): Promise<{ targetName: string }> {
  const response = await fetch(`${BACKEND_URL}/tail/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_id: targetId })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to start tailing');
  }
  
  const data = await response.json();
  return { targetName: data.target_name };
}

/**
 * Stop tailing
 */
export async function stopTailing(): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/tail/stop`, {
    method: 'POST'
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to stop tailing');
  }
}
