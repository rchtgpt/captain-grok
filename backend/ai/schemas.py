"""
Pydantic schemas for structured outputs from Grok AI.
Ensures type-safe, validated responses.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Direction(str, Enum):
    """Movement directions for drone."""
    FORWARD = "forward"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"


class DroneState(str, Enum):
    """Possible drone states."""
    CONNECTED = "connected"
    FLYING = "flying"
    HOVERING = "hovering"
    LANDING = "landing"
    LANDED = "landed"
    ERROR = "error"


class VisionObject(BaseModel):
    """A detected object in vision analysis."""
    name: str = Field(description="Name or type of the object")
    description: str = Field(description="Detailed description of the object")
    estimated_distance: Optional[str] = Field(None, description="Estimated distance (e.g. '2 meters', 'far away')")
    relative_position: Optional[str] = Field(None, description="Position relative to drone (e.g. 'center', 'left', 'above')")
    confidence: Optional[str] = Field(None, description="Confidence level (high, medium, low)")


class VisionAnalysis(BaseModel):
    """Structured vision analysis from Grok Vision."""
    summary: str = Field(description="Brief summary of what the drone sees")
    objects_detected: List[VisionObject] = Field(description="List of detected objects")
    scene_description: str = Field(description="Overall scene description")
    hazards: List[str] = Field(default_factory=list, description="Any potential hazards or obstacles")
    lighting_conditions: Optional[str] = Field(None, description="Lighting conditions (bright, dim, dark, etc.)")
    weather_visible: Optional[str] = Field(None, description="Visible weather conditions if outdoors")


class SearchResult(BaseModel):
    """Result from searching for a specific target."""
    found: bool = Field(description="Whether the target was found")
    confidence: str = Field(description="Confidence level: high, medium, low")
    description: str = Field(description="Description of what was found or not found")
    estimated_angle: Optional[int] = Field(None, description="Estimated angle to target in degrees (0-360)")
    estimated_distance: Optional[str] = Field(None, description="Estimated distance to target")
    recommended_action: Optional[str] = Field(None, description="Recommended next action")


class ToolExecutionPlan(BaseModel):
    """Plan for executing tools based on user command."""
    reasoning: str = Field(description="Explanation of why these tools were chosen")
    tools_to_execute: List[str] = Field(description="Ordered list of tool names to execute")
    parameters: Dict[str, Dict[str, Any]] = Field(description="Parameters for each tool call")
    expected_outcome: str = Field(description="What the user should expect to happen")
    safety_notes: List[str] = Field(default_factory=list, description="Important safety considerations")


class DroneStatus(BaseModel):
    """Structured drone status information."""
    state: DroneState = Field(description="Current drone state")
    battery_percent: int = Field(description="Battery level (0-100)", ge=0, le=100)
    height_cm: int = Field(description="Current height in centimeters", ge=0)
    temperature: int = Field(description="Drone temperature in Celsius")
    is_flying: bool = Field(description="Whether drone is currently flying")
    wifi_signal: Optional[str] = Field(None, description="WiFi signal strength")


class SafetyCheck(BaseModel):
    """Safety validation for a command."""
    is_safe: bool = Field(description="Whether the command is safe to execute")
    safety_score: int = Field(description="Safety score from 0 (dangerous) to 100 (very safe)", ge=0, le=100)
    concerns: List[str] = Field(default_factory=list, description="List of safety concerns")
    recommendations: List[str] = Field(default_factory=list, description="Safety recommendations")
    should_proceed: bool = Field(description="Final recommendation on whether to proceed")


class ReasoningTrace(BaseModel):
    """Extended thinking/reasoning trace from the model."""
    thought_process: str = Field(description="The model's internal reasoning")
    key_considerations: List[str] = Field(description="Key factors considered")
    alternatives_considered: List[str] = Field(default_factory=list, description="Alternative approaches considered")
    confidence_level: str = Field(description="Overall confidence in the decision")
    final_decision: str = Field(description="The final decision made")


class CommandResponse(BaseModel):
    """Complete structured response to a user command."""
    reasoning: ReasoningTrace = Field(description="The AI's reasoning process")
    response_text: str = Field(description="Natural language response to the user")
    actions_taken: List[str] = Field(description="List of actions that were executed")
    status: str = Field(description="Overall status: success, partial_success, failed")
    error_message: Optional[str] = Field(None, description="Error message if status is failed")
    next_steps: List[str] = Field(default_factory=list, description="Suggested next steps")


class EmergencyAssessment(BaseModel):
    """Assessment of an emergency situation."""
    is_emergency: bool = Field(description="Whether this is a true emergency")
    severity: str = Field(description="Severity level: critical, high, medium, low")
    immediate_actions: List[str] = Field(description="Actions to take immediately")
    explanation: str = Field(description="Explanation of the situation")


class ObstacleInfo(BaseModel):
    """Information about a detected obstacle."""
    name: str = Field(description="Type/name of obstacle (wall, person, furniture, etc.)")
    position: str = Field(description="Position relative to drone: front, left, right, above, below")
    estimated_distance_cm: int = Field(description="Estimated distance in centimeters (rough estimate)")
    danger_level: str = Field(description="Danger level: high, medium, low")
    description: str = Field(description="Brief description of the obstacle")


# ==================== ENHANCED ENTITY DETECTION ====================

class FramePosition(str, Enum):
    """Position within the camera frame."""
    FAR_LEFT = "far_left"
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    FAR_RIGHT = "far_right"


class EstimatedDistance(str, Enum):
    """Estimated distance from drone."""
    VERY_CLOSE = "very_close"  # < 50cm
    CLOSE = "close"            # 50-100cm
    MEDIUM = "medium"          # 100-200cm
    FAR = "far"                # 200-400cm
    VERY_FAR = "very_far"      # > 400cm


class BoundingBox(BaseModel):
    """Bounding box as percentages of frame dimensions."""
    x: float = Field(ge=0, le=1, description="Left edge as percentage (0-1)")
    y: float = Field(ge=0, le=1, description="Top edge as percentage (0-1)")
    width: float = Field(ge=0, le=1, description="Width as percentage (0-1)")
    height: float = Field(ge=0, le=1, description="Height as percentage (0-1)")


class PersonAnalysis(BaseModel):
    """Detailed analysis of a person in the frame."""
    # Location
    position_in_frame: str = Field(description="far_left, left, center, right, far_right")
    estimated_distance: str = Field(description="very_close, close, medium, far, very_far")
    bounding_box: Optional[BoundingBox] = Field(None, description="Bounding box if detectable")
    
    # Physical description
    description: str = Field(description="Full description: 'adult in red shirt sitting down'")
    clothing: str = Field(description="Clothing description: 'red t-shirt, blue jeans'")
    hair: Optional[str] = Field(None, description="Hair description: 'short brown hair', 'bald'")
    accessories: List[str] = Field(default_factory=list, description="glasses, hat, backpack, etc.")
    distinguishing_features: List[str] = Field(default_factory=list, description="beard, tattoo, etc.")
    
    # State
    face_visible: bool = Field(description="Whether the face is visible")
    posture: Optional[str] = Field(None, description="standing, sitting, lying down, crouching")
    appears_conscious: bool = Field(default=True, description="Does the person appear conscious/alert")
    
    # Confidence
    confidence: str = Field(description="low, medium, high")


class ObjectAnalysis(BaseModel):
    """Analysis of an object in the frame."""
    name: str = Field(description="Object type: laptop, chair, table, door, etc.")
    description: str = Field(description="Detailed description")
    position_in_frame: str = Field(description="far_left, left, center, right, far_right")
    estimated_distance: str = Field(description="very_close, close, medium, far, very_far")
    bounding_box: Optional[BoundingBox] = Field(None, description="Bounding box if detectable")
    confidence: str = Field(description="low, medium, high")


class SceneAnalysis(BaseModel):
    """Full scene analysis with entity extraction for memory."""
    # Summary
    summary: str = Field(description="1-2 sentence summary of the scene")
    scene_type: str = Field(description="office, room, hallway, outdoor, etc.")
    
    # Entities
    people: List[PersonAnalysis] = Field(default_factory=list, description="All people detected")
    objects: List[ObjectAnalysis] = Field(default_factory=list, description="Notable objects")
    
    # Frame regions (what's in each part)
    region_left: str = Field(description="What's on the left side of frame")
    region_center: str = Field(description="What's in the center of frame")
    region_right: str = Field(description="What's on the right side of frame")
    
    # Safety
    hazards: List[str] = Field(default_factory=list, description="Any hazards detected")
    obstacles_nearby: bool = Field(description="Are there obstacles close to the drone")
    
    # Lighting
    lighting: str = Field(description="bright, dim, dark, mixed")


class TargetSearchResult(BaseModel):
    """Result from searching for a specific target with entity memory."""
    found: bool = Field(description="Whether the target was found")
    confidence: str = Field(description="low, medium, high")
    
    # If found
    target_description: Optional[str] = Field(None, description="Description of what was found")
    position_in_frame: Optional[str] = Field(None, description="far_left, left, center, right, far_right")
    estimated_distance: Optional[str] = Field(None, description="very_close, close, medium, far, very_far")
    bounding_box: Optional[BoundingBox] = Field(None, description="Bounding box if detectable")
    
    # Person-specific (if target is a person)
    clothing: Optional[str] = Field(None, description="Clothing if person")
    accessories: List[str] = Field(default_factory=list, description="Visible accessories")
    face_visible: bool = Field(default=False, description="Is face visible")
    
    # Action
    recommended_action: str = Field(description="What to do next")
    
    # What else was seen (for memory)
    other_people_seen: List[PersonAnalysis] = Field(default_factory=list, description="Other people visible")
    objects_seen: List[ObjectAnalysis] = Field(default_factory=list, description="Objects visible")


class WhatsThatResult(BaseModel):
    """Result from analyzing what's in the center of frame ('what's that?')."""
    description: str = Field(description="Description of what's in center of frame")
    entity_type: str = Field(description="person, object, furniture, location, unknown")
    
    # Details
    detailed_description: str = Field(description="More detailed description")
    
    # If person
    clothing: Optional[str] = Field(None)
    accessories: List[str] = Field(default_factory=list)
    
    # Position
    estimated_distance: str = Field(description="very_close, close, medium, far, very_far")
    
    confidence: str = Field(description="low, medium, high")


class ClearanceCheckResult(BaseModel):
    """Result of vision-based clearance check for drone safety."""
    is_clear: bool = Field(description="Whether the area is clear for the intended maneuver")
    overall_safety_score: int = Field(description="Safety score 0-100 (100 = completely safe)", ge=0, le=100)
    
    # Clearance in each direction (estimated in cm, -1 if unknown)
    front_clearance_cm: int = Field(description="Estimated clearance in front (-1 if cannot determine)")
    left_clearance_cm: int = Field(description="Estimated clearance to the left (-1 if cannot determine)")
    right_clearance_cm: int = Field(description="Estimated clearance to the right (-1 if cannot determine)")
    above_clearance_cm: int = Field(description="Estimated clearance above (-1 if cannot determine)")
    below_clearance_cm: int = Field(description="Estimated clearance below (-1 if cannot determine)")
    
    obstacles: List[ObstacleInfo] = Field(default_factory=list, description="List of detected obstacles")
    hazards: List[str] = Field(default_factory=list, description="Immediate hazards that require attention")
    
    safe_for_flip: bool = Field(description="Is there enough clearance for a flip maneuver (needs ~2m all around)")
    safe_for_forward_movement: bool = Field(description="Is it safe to move forward")
    safe_for_lateral_movement: bool = Field(description="Is it safe to move left/right")
    safe_for_vertical_movement: bool = Field(description="Is it safe to move up/down")
    
    recommended_action: str = Field(description="What the drone should do next for safety")
    warnings: List[str] = Field(default_factory=list, description="Safety warnings to consider")


# ==================== PANORAMA ANALYSIS ====================

class PersonBoundingBox(BaseModel):
    """Bounding box for a person in a specific frame."""
    frame_number: int = Field(description="Frame number (1-8)")
    x: float = Field(ge=0, le=1, description="Left edge as percentage (0-1)")
    y: float = Field(ge=0, le=1, description="Top edge as percentage (0-1)")
    width: float = Field(ge=0, le=1, description="Width as percentage (0-1)")
    height: float = Field(ge=0, le=1, description="Height as percentage (0-1)")


class UniquePerson(BaseModel):
    """A unique person identified across multiple panorama frames."""
    # Identity tracking
    person_id: str = Field(description="Unique ID like 'person_1', 'person_2' to track across frames")
    frames_visible_in: List[int] = Field(description="Which frame numbers (1-8) this person appears in")
    
    # Bounding boxes for each frame they appear in
    bounding_boxes: List[PersonBoundingBox] = Field(
        default_factory=list, 
        description="Bounding box in each frame where person is visible"
    )
    
    # Best frame for this person (clearest view)
    best_frame: int = Field(description="Frame number with the clearest view of this person (1-8)")
    
    # Best position (from clearest view)
    primary_direction: str = Field(description="ahead, to_my_left, to_my_right, behind_me_left, behind_me_right, behind_me")
    estimated_distance: str = Field(description="very_close, close, medium, far, very_far")
    
    # Physical description (combine all views for best description)
    description: str = Field(description="Full description combining all views")
    clothing: str = Field(description="Clothing description from best view")
    hair: Optional[str] = Field(None, description="Hair if visible in any frame")
    accessories: List[str] = Field(default_factory=list, description="All accessories seen across frames")
    distinguishing_features: List[str] = Field(default_factory=list, description="Unique features")
    
    # State
    face_visible: bool = Field(description="Was face visible in any frame")
    posture: Optional[str] = Field(None, description="standing, sitting, lying_down, etc.")
    
    confidence: str = Field(description="low, medium, high")


class UniqueObject(BaseModel):
    """A unique object identified across multiple panorama frames."""
    object_id: str = Field(description="Unique ID like 'object_A', 'object_B'")
    frames_visible_in: List[int] = Field(description="Which frame numbers (1-8) this object appears in")
    
    name: str = Field(description="Object type: desk, chair, door, window, etc.")
    description: str = Field(description="Detailed description")
    primary_direction: str = Field(description="ahead, to_my_left, to_my_right, behind_me")
    estimated_distance: str = Field(description="very_close, close, medium, far, very_far")
    
    confidence: str = Field(description="low, medium, high")


class PanoramaAnalysis(BaseModel):
    """
    Analysis of a 360° panorama from 8 frames.
    CRITICAL: Deduplicates entities - same person/object seen from multiple angles = ONE entry.
    """
    # Summary
    summary: str = Field(description="1-2 sentence summary of the full 360° view")
    scene_type: str = Field(description="office, conference_room, hallway, living_room, etc.")
    
    # UNIQUE people (deduplicated across all 8 frames)
    unique_people: List[UniquePerson] = Field(
        default_factory=list, 
        description="All UNIQUE people seen - same person in multiple frames = ONE entry"
    )
    
    # UNIQUE objects (deduplicated, only significant ones)
    unique_objects: List[UniqueObject] = Field(
        default_factory=list,
        description="Significant UNIQUE objects - same object in multiple frames = ONE entry"
    )
    
    # Spatial layout
    total_people_count: int = Field(description="Total number of UNIQUE people in the 360° view")
    total_objects_count: int = Field(description="Total number of significant UNIQUE objects")
    
    # What's in each direction (from drone's starting orientation)
    direction_ahead: str = Field(description="What's ahead (frame 1)")
    direction_right: str = Field(description="What's to the right (frames 2-3)")
    direction_behind: str = Field(description="What's behind (frames 4-5)")
    direction_left: str = Field(description="What's to the left (frames 6-7)")
    
    # Safety
    obstacles_detected: List[str] = Field(default_factory=list, description="Nearby obstacles")
    hazards: List[str] = Field(default_factory=list, description="Any hazards")


# ==================== TARGET MATCHING ====================

class TargetNameMatch(BaseModel):
    """Result of fuzzy matching a user query to registered targets."""
    matched: bool = Field(description="Whether a target was matched")
    target_name: Optional[str] = Field(None, description="The exact name of the matched target (from the available list)")
    confidence: float = Field(ge=0, le=1, description="Confidence score 0-1")
    reasoning: str = Field(description="Brief explanation of why this was matched or not")
