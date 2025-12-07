/**
 * Type definitions for Voice Task Assistant
 */

export type RecordingState = 'idle' | 'recording' | 'processing' | 'complete' | 'error';

export interface TranscriptionResponse {
  text: string;
}

export interface TranscriptionError {
  error: string;
  details?: string;
}

export interface BackendTaskResponse {
  stream_url?: string;
  mjpeg_url?: string;
  streamUrl?: string;
  [key: string]: unknown;
}

export interface AudioRecorderState {
  isRecording: boolean;
  recordingState: RecordingState;
  transcript: string;
  error: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
}

export interface VideoStreamState {
  streamUrl: string | null;
  isLoading: boolean;
  hasError: boolean;
  setStreamUrl: (url: string | null) => void;
  clearStream: () => void;
}

export interface StatusMessage {
  text: string;
  type: 'idle' | 'recording' | 'processing' | 'success' | 'error';
}

// ============================================================================
// SSE Streaming Types for Real-Time Command Execution
// ============================================================================

/** SSE event types emitted by the backend */
export type SSEEventType = 
  | 'command_received' 
  | 'ai_response' 
  | 'tool_start' 
  | 'tool_complete' 
  | 'found' 
  | 'error' 
  | 'done';

/** A tool call planned by Grok */
export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
}

/** Status of a tool during execution */
export type ToolStatus = 'pending' | 'executing' | 'success' | 'error';

/** Live execution state for a single tool */
export interface ToolExecution {
  index: number;
  total: number;
  tool: string;
  arguments: Record<string, unknown>;
  status: ToolStatus;
  message?: string;
  data?: Record<string, unknown>;
}

/** Found target information from search operations */
export interface FoundTarget {
  target: string;
  imageUrl: string | null;
  description: string;
  confidence: string;
  angle?: number;
}

/** Complete state for a command execution (current or historical) */
export interface CommandExecution {
  id: string;
  timestamp: Date;
  command: string;
  aiResponse?: string;
  toolCalls: ToolCall[];
  toolExecutions: ToolExecution[];
  foundTarget?: FoundTarget;
  status: 'processing' | 'complete' | 'error';
  error?: string;
}

/** SSE Event Payloads */
export interface SSECommandReceivedPayload {
  command: string;
}

export interface SSEAiResponsePayload {
  response: string;
  tool_calls: ToolCall[];
}

export interface SSEToolStartPayload {
  index: number;
  total: number;
  tool: string;
  arguments: Record<string, unknown>;
}

export interface SSEToolCompletePayload {
  index: number;
  tool: string;
  success: boolean;
  message: string;
  data: Record<string, unknown> | null;
}

export interface SSEFoundPayload {
  target: string;
  imageUrl: string | null;
  description: string;
  confidence: string;
  angle?: number;
}

export interface SSEErrorPayload {
  message: string;
}

export interface SSEDonePayload {
  status: 'success' | 'error';
  total_tools?: number;
  successful?: number;
  error?: string;
}

/** Hook return type for command streaming */
export interface CommandStreamState {
  history: CommandExecution[];
  currentExecution: CommandExecution | null;
  foundTarget: FoundTarget | null;
  showFoundModal: boolean;
  setShowFoundModal: (show: boolean) => void;
  executeCommand: (text: string) => Promise<void>;
  isExecuting: boolean;
  viewFoundTarget: (target: FoundTarget) => void;
}

// ============================================================================
// Chat Types - Real-time conversation with the drone
// ============================================================================

/** Role of the message sender */
export type ChatRole = 'user' | 'drone' | 'system';

/** Type of chat message for styling */
export type ChatMessageType = 
  | 'command'      // User voice command
  | 'thinking'     // Drone processing
  | 'action'       // Tool execution
  | 'response'     // Drone verbal response
  | 'found'        // Target found alert
  | 'error'        // Error message
  | 'memory'       // Memory-related info
  | 'navigation';  // Navigation update

/** A single chat message */
export interface ChatMessage {
  id: string;
  role: ChatRole;
  type: ChatMessageType;
  content: string;
  timestamp: Date;
  toolName?: string;        // If action type, which tool
  toolSuccess?: boolean;    // Tool result
  entityId?: string;        // Associated entity
  imageUrl?: string;        // Associated image
}

/** Chat state for hook */
export interface ChatState {
  messages: ChatMessage[];
  isThinking: boolean;
  addMessage: (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  clearChat: () => void;
}

// ============================================================================
// Drone Status Types - Real-time drone state
// ============================================================================

/** Drone flight state */
export type DroneState = 'grounded' | 'taking_off' | 'hovering' | 'flying' | 'landing' | 'error';

/** Real-time drone status */
export interface DroneStatus {
  connected: boolean;
  flying: boolean;
  battery: number;
  height: number;
  temperature: number;
  state: DroneState;
}

/** System status including drone and video */
export interface SystemStatus {
  drone: DroneStatus;
  system: {
    abortFlag: boolean;
    videoRunning: boolean;
    toolsCount: number;
  };
}

// ============================================================================
// Memory Types - Entities remembered by the drone
// ============================================================================

/** Position in frame (for bounding box) */
export type FramePosition = 'left' | 'center' | 'right' | 'unknown';

/** Confidence level - backend returns string */
export type ConfidenceLevel = 'low' | 'medium' | 'high';

/** Entity snapshot - a single sighting */
export interface EntitySnapshot {
  imageUrl: string;
  thumbnailUrl: string | null;
  timestamp: string;
  framePosition: FramePosition;
  droneHeading: number;
}

/** A remembered person */
export interface Person {
  id: string;
  entityType: 'person';
  name: string | null;
  description: string;
  clothing: string | null;
  hair: string | null;
  accessories: string[];
  distinctiveFeatures: string[];
  faceVisible: boolean;
  absoluteAngle: number;
  relativeAngle: number;
  direction: string;
  estimatedDistanceCm: number;
  confidence: ConfidenceLevel;
  firstSeen: string;
  lastSeen: string;
  sightings: number;
  snapshots: EntitySnapshot[];
  thumbnailUrl: string | null;
  targetId: string | null;  // Links to Target if matched via facial recognition
}

/** A remembered object */
export interface MemoryObject {
  id: string;
  entityType: 'object' | 'furniture' | 'location';
  name: string | null;
  description: string;
  absoluteAngle: number;
  relativeAngle: number;
  direction: string;
  estimatedDistanceCm: number;
  confidence: ConfidenceLevel;
  firstSeen: string;
  lastSeen: string;
  sightings: number;
  snapshots: EntitySnapshot[];
  thumbnailUrl: string | null;
}

/** Memory stats */
export interface MemoryStats {
  peopleCount: number;
  objectsCount: number;
  entityCount: number;
  heading: number;
  position: { x: number; y: number; z: number };
}

/** Full memory response */
export interface MemoryResponse {
  people: Person[];
  objects: MemoryObject[];
  stats: MemoryStats;
}

// ============================================================================
// Target Types - People to search for with facial recognition
// ============================================================================

/** Target search status */
export type TargetStatus = 'searching' | 'found' | 'confirmed';

/** A target to search for using facial recognition */
export interface Target {
  id: string;
  name: string;
  description: string;
  referencePhotos: string[];
  status: TargetStatus;
  foundEntityId: string | null;
  matchedPhotos: string[];
  matchConfidence: number;
  createdAt: string;
  foundAt: string | null;
}

/** Response when listing targets */
export interface TargetsResponse {
  targets: Target[];
  stats: {
    total: number;
    found: number;
    searching: number;
  };
}

/** SSE event when a target is found via facial recognition */
export interface SSETargetFoundPayload {
  target: Target;
  entity: Person | null;
  confidence: number;
  matchedPhotoUrl: string | null;
}

/** Memory state for hook */
export interface MemoryState {
  people: Person[];
  objects: MemoryObject[];
  stats: MemoryStats | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  selectedEntity: Person | MemoryObject | null;
  selectEntity: (entity: Person | MemoryObject | null) => void;
}
