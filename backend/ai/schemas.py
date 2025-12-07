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
