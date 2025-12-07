"""
xAI Grok API client for text generation and vision analysis.
Supports structured outputs and extended thinking/reasoning.
"""

import requests
import json
import base64
from copy import deepcopy
from io import BytesIO
from typing import Optional, List, Dict, Any, Type, TypeVar
import numpy as np
from PIL import Image
from pydantic import BaseModel

from core.logger import get_logger
from core.exceptions import GrokAPIError
from config.settings import Settings
from utils.image_logger import get_image_logger
from .prompts import (
    DRONE_PILOT_SYSTEM_PROMPT,
    VISION_ANALYSIS_PROMPT,
    CODE_GENERATION_PROMPT,
    SEARCH_PROMPT_TEMPLATE,
    CLEARANCE_CHECK_PROMPT,
    OBSTACLE_DETECTION_PROMPT
)
from .schemas import (
    VisionAnalysis,
    SearchResult,
    CommandResponse,
    ReasoningTrace,
    ClearanceCheckResult,
    SceneAnalysis,
    TargetSearchResult,
    WhatsThatResult,
    PersonAnalysis,
    ObjectAnalysis,
    PanoramaAnalysis
)

T = TypeVar('T', bound=BaseModel)


class GrokClient:
    """
    Client for xAI Grok API.
    Handles text generation, vision analysis, and tool calling.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize Grok client.
        
        Args:
            settings: Application settings (will create if None)
        """
        if settings is None:
            from config.settings import get_settings
            settings = get_settings()
        
        self.settings = settings
        self.log = get_logger('grok')
        
        # API configuration
        self.api_key = settings.XAI_API_KEY
        self.api_base = settings.XAI_API_BASE
        self.model = settings.XAI_MODEL
        self.vision_model = settings.XAI_VISION_MODEL
        
        # Request headers
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        self.log.info(f"Grok client initialized (model: {self.model})")
        
        # Track reasoning traces for logging
        self.last_reasoning: Optional[str] = None
        
        # Image logging
        self.enable_image_logging = settings.ENABLE_IMAGE_LOGGING
        if self.enable_image_logging:
            self.image_logger = get_image_logger(settings.VISION_LOG_DIR)
            self.log.info("📸 Image logging enabled")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to self.model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            Response text
            
        Raises:
            GrokAPIError: If API request fails
        """
        endpoint = f'{self.api_base}/chat/completions'
        
        payload = {
            'model': model or self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        try:
            self.log.debug(f"Sending chat request ({len(messages)} messages)")
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            self.log.debug(f"Received response ({len(content)} chars)")
            return content
        
        except requests.exceptions.RequestException as e:
            self.log.error(f"API request failed: {e}")
            raise GrokAPIError(f"Grok API request failed: {e}")
    
    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a chat request with tool calling enabled.
        
        Args:
            messages: List of message dicts
            tools: List of tool definitions (OpenAI function format)
            model: Model to use
            
        Returns:
            Dict with 'response', 'tool_calls', and 'finish_reason'
        """
        endpoint = f'{self.api_base}/chat/completions'
        
        payload = {
            'model': model or self.model,
            'messages': messages,
            'tools': tools,
            'tool_choice': 'auto'
        }
        
        try:
            self.log.debug(f"Sending tool-enabled chat request ({len(tools)} tools)")
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            choice = result['choices'][0]
            message = choice['message']
            
            # Extract response and tool calls
            response_data = {
                'response': message.get('content', ''),
                'tool_calls': [],
                'finish_reason': choice['finish_reason']
            }
            
            # Parse tool calls if present
            if 'tool_calls' in message:
                for tool_call in message['tool_calls']:
                    response_data['tool_calls'].append({
                        'id': tool_call['id'],
                        'name': tool_call['function']['name'],
                        'arguments': json.loads(tool_call['function']['arguments'])
                    })
            
            self.log.debug(f"Response: {len(response_data['tool_calls'])} tool calls")
            return response_data
        
        except requests.exceptions.RequestException as e:
            self.log.error(f"Tool-enabled API request failed: {e}")
            raise GrokAPIError(f"Grok API request failed: {e}")
    
    def generate_drone_code(self, command: str) -> str:
        """
        Generate Python drone control code from natural language.
        
        Args:
            command: Natural language command
            
        Returns:
            Python code string
        """
        self.log.info(f"Generating code for: {command}")
        
        messages = [
            {'role': 'system', 'content': CODE_GENERATION_PROMPT},
            {'role': 'user', 'content': command}
        ]
        
        code = self.chat(messages, temperature=0.3)
        
        # Strip markdown formatting if present
        code = self._strip_markdown(code)
        
        self.log.success(f"Generated {len(code)} chars of code")
        return code
    
    def analyze_image(
        self,
        frame: np.ndarray,
        prompt: str = "What do you see?",
        detailed: bool = False
    ) -> str:
        """
        Analyze an image using Grok Vision.
        
        Args:
            frame: Image as numpy array (BGR format from OpenCV)
            prompt: Question to ask about the image
            detailed: Whether to request detailed analysis
            
        Returns:
            Analysis text
        """
        self.log.debug(f"Analyzing image: {prompt}")
        
        # Convert frame to base64
        image_base64 = self._frame_to_base64(frame)
        
        # Build system prompt
        system_prompt = VISION_ANALYSIS_PROMPT
        if detailed:
            system_prompt += "\nProvide a detailed analysis with specific observations."
        
        # Build messages with vision
        messages = [
            {'role': 'system', 'content': system_prompt},
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{image_base64}'
                        }
                    }
                ]
            }
        ]
        
        result = self.chat(messages, model=self.vision_model, max_tokens=500)
        
        # Log the image and result
        if self.enable_image_logging:
            self.image_logger.log_vision_request(
                frame=frame,
                prompt=prompt,
                response=result,
                metadata={
                    'model': self.vision_model,
                    'detailed': detailed,
                    'method': 'analyze_image'
                }
            )
        
        self.log.debug(f"Vision analysis complete")
        return result
    
    def search_for_target(
        self,
        frame: np.ndarray,
        target_description: str
    ) -> tuple[bool, str]:
        """
        Search for a specific target in an image.
        
        Args:
            frame: Image to analyze
            target_description: What to look for
            
        Returns:
            Tuple of (found: bool, description: str)
        """
        prompt = SEARCH_PROMPT_TEMPLATE.format(target=target_description)
        
        result = self.analyze_image(frame, prompt)
        
        # Check if target was found
        found = result.upper().startswith('YES')
        
        # Log search specifically
        if self.enable_image_logging:
            self.image_logger.log_search_request(
                frame=frame,
                target=target_description,
                found=found,
                result=result,
                metadata={
                    'model': self.vision_model,
                    'method': 'search_for_target'
                }
            )
        
        return found, result
    
    def _frame_to_base64(self, frame: np.ndarray) -> str:
        """
        Convert OpenCV frame to base64-encoded JPEG.
        
        Args:
            frame: BGR image from OpenCV
            
        Returns:
            Base64 encoded string
        """
        # Convert BGR to RGB
        import cv2
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(frame_rgb)
        
        # Resize if too large (to save bandwidth)
        max_size = 1024
        if max(pil_image.size) > max_size:
            pil_image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Encode as JPEG
        buffer = BytesIO()
        pil_image.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        
        # Encode to base64
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        return image_base64
    
    def _strip_markdown(self, code: str) -> str:
        """
        Strip markdown code block formatting from generated code.
        
        Args:
            code: Code string possibly wrapped in markdown
            
        Returns:
            Clean code
        """
        code = code.strip()
        
        # Remove markdown code blocks
        if code.startswith('```'):
            lines = code.split('\n')
            # Remove first line (```python or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            code = '\n'.join(lines)
        
        return code.strip()
    
    def _strip_json_markdown(self, content: str) -> str:
        """
        Strip markdown code block formatting and trailing text from JSON responses.
        
        The API sometimes returns:
        - JSON wrapped in ```json ... ``` blocks
        - Extra text/explanation after the JSON
        
        Args:
            content: Response content possibly wrapped in markdown or with trailing text
            
        Returns:
            Clean JSON string
        """
        content = content.strip()
        
        # Check for markdown code blocks
        if content.startswith('```'):
            lines = content.split('\n')
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            content = '\n'.join(lines)
        
        content = content.strip()
        
        # Handle trailing text after JSON object
        # Find the last closing brace that completes the JSON
        if content.startswith('{'):
            brace_count = 0
            json_end = 0
            for i, char in enumerate(content):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            if json_end > 0:
                content = content[:json_end]
        
        # Handle trailing text after JSON array
        elif content.startswith('['):
            bracket_count = 0
            json_end = 0
            for i, char in enumerate(content):
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        json_end = i + 1
                        break
            if json_end > 0:
                content = content[:json_end]
        
        return content.strip()
    
    def _repair_json(self, content: str) -> str:
        """
        Attempt to repair common JSON syntax errors from LLM responses.
        
        Common issues:
        - Unquoted keys
        - Trailing commas
        - Single quotes instead of double quotes
        - NaN/Infinity values
        
        Args:
            content: Potentially malformed JSON string
            
        Returns:
            Repaired JSON string
        """
        import re
        
        # Replace single quotes with double quotes (but not inside strings)
        # This is a simple approach - handle apostrophes carefully
        content = re.sub(r"'([^']*)':", r'"\1":', content)
        content = re.sub(r":\s*'([^']*)'", r': "\1"', content)
        
        # Fix unquoted keys - match word characters followed by colon
        # But be careful not to break URLs or already quoted strings
        content = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', content)
        
        # Remove trailing commas before } or ]
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        
        # Replace NaN with null
        content = re.sub(r'\bNaN\b', 'null', content)
        
        # Replace Infinity with null
        content = re.sub(r'\bInfinity\b', 'null', content)
        content = re.sub(r'-Infinity\b', 'null', content)
        
        # Fix boolean case issues
        content = re.sub(r'\bTrue\b', 'true', content)
        content = re.sub(r'\bFalse\b', 'false', content)
        content = re.sub(r'\bNone\b', 'null', content)
        
        return content
    
    def chat_with_structured_output(
        self,
        messages: List[Dict[str, Any]],
        response_format: Type[T],
        model: Optional[str] = None,
        temperature: float = 0.7,
        timeout: int = 60
    ) -> T:
        """
        Send a chat request with structured output using Pydantic schema.
        
        Args:
            messages: List of message dicts
            response_format: Pydantic model class for response structure
            model: Model to use (defaults to self.model)
            temperature: Sampling temperature
            timeout: Request timeout in seconds (default 60, use higher for multi-image)
            
        Returns:
            Parsed Pydantic object matching response_format
            
        Raises:
            GrokAPIError: If API request fails
        """
        endpoint = f'{self.api_base}/chat/completions'
        
        # Convert Pydantic model to JSON schema
        schema = response_format.model_json_schema()
        
        payload = {
            'model': model or self.model,
            'messages': messages,
            'temperature': temperature,
            'response_format': {
                'type': 'json_schema',
                'json_schema': {
                    'name': response_format.__name__,
                    'schema': schema,
                    'strict': True
                }
            }
        }
        
        try:
            self.log.debug(f"Sending structured output request (format: {response_format.__name__}, timeout: {timeout}s)")
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            
            result = response.json()
            choice = result['choices'][0]
            content = choice['message']['content']
            
            # Extract reasoning if present (for extended thinking models)
            if 'extended_thinking' in result and result['extended_thinking']:
                self.last_reasoning = result['extended_thinking']
                self.log.info("📊 Extended Thinking Detected")
                self._log_reasoning(result['extended_thinking'])
            
            # Strip markdown code blocks if present (API sometimes wraps JSON in ```json ... ```)
            content = self._strip_json_markdown(content)
            
            # Try to parse JSON content into Pydantic model
            try:
                parsed = response_format.model_validate_json(content)
            except Exception as parse_error:
                # If parsing fails, try to repair the JSON
                self.log.warning(f"Initial JSON parse failed, attempting repair: {parse_error}")
                
                # Log the problematic content for debugging (first 500 chars)
                self.log.debug(f"Problematic JSON content: {content[:500]}...")
                
                repaired_content = self._repair_json(content)
                
                try:
                    parsed = response_format.model_validate_json(repaired_content)
                    self.log.info("JSON repair successful!")
                except Exception as repair_error:
                    # Log more context about the failure
                    self.log.error(f"JSON repair also failed: {repair_error}")
                    self.log.error(f"Original content (first 1000 chars): {content[:1000]}")
                    
                    # As a last resort, try using Python's json module to get better error info
                    try:
                        import json as json_module
                        json_module.loads(content)
                    except json_module.JSONDecodeError as json_err:
                        self.log.error(f"JSON decode error at position {json_err.pos}: {json_err.msg}")
                        # Show context around the error
                        start = max(0, json_err.pos - 50)
                        end = min(len(content), json_err.pos + 50)
                        self.log.error(f"Context: ...{content[start:end]}...")
                    
                    raise parse_error
            
            self.log.success(f"Parsed structured output: {response_format.__name__}")
            return parsed
        
        except requests.exceptions.RequestException as e:
            self.log.error(f"Structured output API request failed: {e}")
            raise GrokAPIError(f"Grok API request failed: {e}")
        except GrokAPIError:
            raise
        except Exception as e:
            self.log.error(f"Failed to parse structured output: {e}")
            raise GrokAPIError(f"Failed to parse response: {e}")
    
    def analyze_image_structured(
        self,
        frame: np.ndarray,
        prompt: str = "Analyze what you see in detail.",
        detailed: bool = True
    ) -> VisionAnalysis:
        """
        Analyze an image using Grok Vision with structured output.
        
        Args:
            frame: Image as numpy array (BGR format from OpenCV)
            prompt: Question to ask about the image
            detailed: Whether to request detailed analysis
            
        Returns:
            VisionAnalysis object with structured data
        """
        self.log.debug(f"Analyzing image (structured): {prompt}")
        
        # Convert frame to base64
        image_base64 = self._frame_to_base64(frame)
        
        # Build system prompt
        system_prompt = VISION_ANALYSIS_PROMPT
        if detailed:
            system_prompt += "\nProvide a detailed analysis with specific observations."
        
        # Build messages with vision
        messages = [
            {'role': 'system', 'content': system_prompt},
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{image_base64}'
                        }
                    }
                ]
            }
        ]
        
        result = self.chat_with_structured_output(
            messages,
            VisionAnalysis,
            model=self.vision_model
        )
        
        # Log the image and structured result
        if self.enable_image_logging:
            self.image_logger.log_vision_request(
                frame=frame,
                prompt=prompt,
                response=result,
                metadata={
                    'model': self.vision_model,
                    'detailed': detailed,
                    'method': 'analyze_image_structured',
                    'objects_detected': len(result.objects_detected)
                }
            )
        
        self.log.debug(f"Vision analysis complete: {len(result.objects_detected)} objects detected")
        return result
    
    def search_for_target_structured(
        self,
        frame: np.ndarray,
        target_description: str,
        angle: Optional[int] = None
    ) -> SearchResult:
        """
        Search for a specific target in an image with structured output.
        
        Args:
            frame: Image to analyze
            target_description: What to look for
            
        Returns:
            SearchResult object with structured data
        """
        prompt = SEARCH_PROMPT_TEMPLATE.format(target=target_description)
        
        # Convert frame to base64
        image_base64 = self._frame_to_base64(frame)
        
        messages = [
            {'role': 'system', 'content': VISION_ANALYSIS_PROMPT},
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{image_base64}'
                        }
                    }
                ]
            }
        ]
        
        result = self.chat_with_structured_output(
            messages,
            SearchResult,
            model=self.vision_model
        )
        
        # Log search with structured result
        if self.enable_image_logging:
            self.image_logger.log_search_request(
                frame=frame,
                target=target_description,
                found=result.found,
                angle=angle,
                result=result,
                metadata={
                    'model': self.vision_model,
                    'method': 'search_for_target_structured',
                    'confidence': result.confidence
                }
            )
        
        return result
    
    def _log_reasoning(self, reasoning: str) -> None:
        """
        Log extended thinking/reasoning in a nicely formatted way.
        
        Args:
            reasoning: The reasoning text to log
        """
        self.log.info("=" * 80)
        self.log.info("🧠 GROK EXTENDED THINKING (REASONING TRACE)")
        self.log.info("=" * 80)
        
        # Split into lines and log each one
        for line in reasoning.split('\n'):
            if line.strip():
                self.log.info(f"  {line}")
        
        self.log.info("=" * 80)
    
    def check_clearance(
        self,
        frame: np.ndarray,
        maneuver_type: str = "general",
        required_clearance_cm: int = 100
    ) -> ClearanceCheckResult:
        """
        Check clearance using vision to detect obstacles and estimate distances.
        
        This is a CRITICAL safety function that should be called before risky maneuvers.
        
        Args:
            frame: Image as numpy array (BGR format from OpenCV)
            maneuver_type: Type of maneuver planned (flip, forward, lateral, vertical, general)
            required_clearance_cm: Minimum clearance required in cm
            
        Returns:
            ClearanceCheckResult with detailed obstacle analysis and safety assessment
        """
        self.log.info(f"🛡️ Checking clearance for {maneuver_type} (need {required_clearance_cm}cm)")
        
        # Convert frame to base64
        image_base64 = self._frame_to_base64(frame)
        
        # Build the clearance check prompt
        system_prompt = CLEARANCE_CHECK_PROMPT.format(
            maneuver_type=maneuver_type,
            required_clearance_cm=required_clearance_cm
        )
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': f"Analyze this drone camera image for obstacle clearance. The drone wants to perform: {maneuver_type}. Required clearance: {required_clearance_cm}cm. Carefully estimate distances to all obstacles and determine if this maneuver is safe."
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{image_base64}'
                        }
                    }
                ]
            }
        ]
        
        result = self.chat_with_structured_output(
            messages,
            ClearanceCheckResult,
            model=self.vision_model
        )
        
        # Log the clearance check result
        if self.enable_image_logging:
            self.image_logger.log_vision_request(
                frame=frame,
                prompt=f"Clearance check for {maneuver_type}",
                response=result,
                metadata={
                    'model': self.vision_model,
                    'method': 'check_clearance',
                    'maneuver_type': maneuver_type,
                    'required_clearance_cm': required_clearance_cm,
                    'is_clear': result.is_clear,
                    'safety_score': result.overall_safety_score,
                    'obstacles_count': len(result.obstacles)
                }
            )
        
        # Log summary
        if result.is_clear:
            self.log.success(f"✅ Clearance OK! Safety score: {result.overall_safety_score}/100")
        else:
            self.log.warning(f"⚠️ Clearance BLOCKED! Safety score: {result.overall_safety_score}/100")
            for warning in result.warnings[:3]:  # Log first 3 warnings
                self.log.warning(f"   • {warning}")
        
        return result
    
    def quick_obstacle_check(self, frame: np.ndarray) -> dict:
        """
        Quick obstacle check - faster than full clearance check.
        Returns basic safety info without full structured analysis.
        
        Args:
            frame: Image as numpy array
            
        Returns:
            Dict with 'safe', 'obstacles', and 'warning' keys
        """
        self.log.debug("🔍 Quick obstacle check...")
        
        image_base64 = self._frame_to_base64(frame)
        
        messages = [
            {'role': 'system', 'content': OBSTACLE_DETECTION_PROMPT},
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': "Quickly scan for nearby obstacles. Is it safe to continue forward? Answer with SAFE or DANGER, then list any obstacles within 1 meter."
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{image_base64}'
                        }
                    }
                ]
            }
        ]
        
        response = self.chat(messages, model=self.vision_model, max_tokens=200)
        
        is_safe = response.upper().startswith('SAFE')
        
        return {
            'safe': is_safe,
            'response': response,
            'warning': None if is_safe else response
        }
    
    # ==================== ENHANCED ENTITY EXTRACTION ====================
    
    def analyze_scene_with_entities(self, frame: np.ndarray) -> SceneAnalysis:
        """
        Analyze a scene with full entity extraction for memory.
        Detects all people and objects with detailed descriptions.
        
        Args:
            frame: Image as numpy array (BGR format)
            
        Returns:
            SceneAnalysis with people, objects, and spatial info
        """
        self.log.debug("🔍 Analyzing scene with entity extraction...")
        
        image_base64 = self._frame_to_base64(frame)
        
        system_prompt = """You are a search and rescue drone's vision system. Your PRIMARY MISSION is to detect ALL PEOPLE in the scene.

## CRITICAL: COUNT EVERY PERSON VISIBLE
- Even if they're partially visible, facing away, or in the background - COUNT THEM
- Even if you can only see their back, arm, or leg - COUNT THEM as a person
- People sitting at tables, standing, or in ANY position - COUNT THEM ALL
- If you see 4 people, you MUST return 4 PersonAnalysis entries

## For EACH PERSON you see, provide:
- position_in_frame: far_left, left, center, right, far_right (estimate based on where they are in the image)
- estimated_distance: very_close (<50cm), close (50-100cm), medium (100-200cm), far (200-400cm), very_far (>400cm)
- description: Full description including what they're doing
- clothing: Detailed description with COLORS (e.g., "dark blue hoodie, gray pants")
- hair: Color, length, style if visible, or "not visible" if facing away
- accessories: glasses, hat, bag, laptop, phone, etc.
- face_visible: true ONLY if you can see their face; false if back is turned
- posture: standing, sitting, lying_down, crouching, walking
- appears_conscious: true/false (important for search & rescue!)
- bounding_box: MUST provide x, y, width, height as percentages (0-1) for EACH person

## IMPORTANT BOUNDING BOX RULES:
- x=0 means left edge of image, x=1 means right edge
- y=0 means top of image, y=1 means bottom
- A person on the left side of the image should have x around 0.0-0.3
- A person in center should have x around 0.3-0.7
- A person on the right should have x around 0.7-1.0
- Width and height should be reasonable (typically 0.1-0.4 for a person)
- DO NOT return x=0, y=0 unless the person is actually in the top-left corner

## For OBJECTS:
Note significant objects: laptops, monitors, tables, chairs, doors, windows, whiteboards, etc.

## Region descriptions:
Describe what's in each region: left, center, right - including ALL people in each region.

BE THOROUGH - this is life-saving search and rescue! Miss NOTHING!"""
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': """Analyze this scene carefully for search and rescue.

CRITICAL: Count and describe EVERY person visible in this image:
1. First, count how many people you can see (including those facing away or partially visible)
2. Then describe each person with position, clothing, and bounding box
3. Note significant objects (laptops, tables, chairs, etc.)
4. Describe what's in each region (left, center, right)

Remember: Missing a person could cost lives! Be thorough."""
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{image_base64}'
                        }
                    }
                ]
            }
        ]
        
        result = self.chat_with_structured_output(
            messages,
            SceneAnalysis,
            model=self.vision_model
        )
        
        # Log the analysis
        if self.enable_image_logging:
            self.image_logger.log_vision_request(
                frame=frame,
                prompt="Scene analysis with entity extraction",
                response=result,
                metadata={
                    'model': self.vision_model,
                    'method': 'analyze_scene_with_entities',
                    'people_count': len(result.people),
                    'objects_count': len(result.objects)
                }
            )
        
        self.log.info(f"Scene analysis: {len(result.people)} people, {len(result.objects)} objects")
        return result
    
    def analyze_people_detailed(self, frame: np.ndarray) -> SceneAnalysis:
        """
        Detailed person analysis - focuses specifically on people.
        Use when you need thorough person descriptions for memory.
        
        Args:
            frame: Image as numpy array
            
        Returns:
            SceneAnalysis focused on people
        """
        self.log.debug("🔍 Detailed person analysis...")
        
        image_base64 = self._frame_to_base64(frame)
        
        system_prompt = """You are analyzing an image to identify and describe ALL people visible. This is CRITICAL for search and rescue.

## FIRST: COUNT ALL PEOPLE
Look carefully at EVERY part of the image. Count all humans visible:
- People fully visible
- People partially visible (even just a shoulder or arm)
- People facing away from camera
- People sitting at tables
- People in the background

## FOR EACH PERSON (you MUST create one entry per person):

1. LOCATION:
   - position_in_frame: far_left, left, center, right, far_right
   - estimated_distance: very_close (<50cm), close (50-100cm), medium (100-200cm), far (200-400cm), very_far (>400cm)
   - bounding_box: REQUIRED - provide x, y, width, height as percentages (0-1)
     * x: horizontal position (0=left edge, 1=right edge)
     * y: vertical position (0=top, 1=bottom)
     * width/height: size of bounding box (typically 0.1-0.4 for a person)
     * DO NOT default to x=0, y=0 - calculate actual position

2. APPEARANCE (be VERY specific - this helps re-identify them):
   - clothing: Full description with colors ("dark blue hoodie, gray pants")
   - hair: Color, length, style ("short black curly hair", "not visible - facing away")
   - accessories: ALL visible items (glasses, laptop, phone, watch, hat, bag, jewelry, headphones)
   - distinguishing_features: Beard, tattoos, scars, unique items

3. STATE:
   - posture: standing, sitting, lying_down, crouching, walking
   - face_visible: true ONLY if you can see their face; false if back is turned or obscured
   - appears_conscious: true/false (important for search & rescue!)

## IMPORTANT:
- If you see 4 people, you MUST return 4 PersonAnalysis entries
- Even if someone's face isn't visible, still include them!
- BE THOROUGH - missing a person could cost lives in search & rescue!"""
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': """CRITICAL TASK: Identify and describe ALL people visible in this image.

Step 1: Count every person in the image (including those facing away, sitting at tables, partially visible)
Step 2: For EACH person, provide detailed description with:
   - Position in frame (left/center/right) and bounding box coordinates
   - Clothing (with colors!)
   - Hair (if visible) or note "facing away"
   - Accessories (laptop, phone, glasses, etc.)

THIS IS SEARCH AND RESCUE - do not miss anyone!"""
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{image_base64}'
                        }
                    }
                ]
            }
        ]
        
        result = self.chat_with_structured_output(
            messages,
            SceneAnalysis,
            model=self.vision_model
        )
        
        self.log.info(f"Detailed person analysis: {len(result.people)} people found")
        return result
    
    def search_with_memory(
        self,
        frame: np.ndarray,
        target_description: str,
        angle: int = 0
    ) -> TargetSearchResult:
        """
        Search for a target while also extracting other entities for memory.
        
        Args:
            frame: Image to search
            target_description: What to look for
            angle: Current rotation angle (for logging)
            
        Returns:
            TargetSearchResult with target info AND other entities seen
        """
        self.log.debug(f"🔍 Searching for: {target_description} (angle: {angle}°)")
        
        image_base64 = self._frame_to_base64(frame)
        
        system_prompt = f"""You are a search and rescue drone searching for: {target_description}

PRIMARY TASK: Determine if the target is in this image.
SECONDARY TASK: Note ALL other people and objects visible (for memory).

If you find the target:
- Set found=true
- Describe exactly what you see that matches
- Give precise position (far_left, left, center, right, far_right)
- Estimate distance

ALSO note other people/objects even if not the target - we want to remember everything!"""
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': f"Search this image for: {target_description}\n\nIs the target visible? Also list any other people or objects you see."
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{image_base64}'
                        }
                    }
                ]
            }
        ]
        
        result = self.chat_with_structured_output(
            messages,
            TargetSearchResult,
            model=self.vision_model
        )
        
        # Log the search
        if self.enable_image_logging:
            self.image_logger.log_search_request(
                frame=frame,
                target=target_description,
                found=result.found,
                angle=angle,
                result=result,
                metadata={
                    'model': self.vision_model,
                    'method': 'search_with_memory',
                    'confidence': result.confidence,
                    'other_people': len(result.other_people_seen),
                    'objects_seen': len(result.objects_seen)
                }
            )
        
        if result.found:
            self.log.success(f"✅ Found target! Confidence: {result.confidence}")
        else:
            self.log.debug(f"Target not found at angle {angle}°")
        
        return result
    
    def whats_that(self, frame: np.ndarray) -> WhatsThatResult:
        """
        Analyze what's in the center of the frame ("What's that?").
        Used when user points at something or asks about what's in front.
        
        Args:
            frame: Image to analyze
            
        Returns:
            WhatsThatResult describing the center of frame
        """
        self.log.debug("🔍 Analyzing center of frame ('what's that?')...")
        
        image_base64 = self._frame_to_base64(frame)
        
        system_prompt = """The user is asking "what's that?" about something in the CENTER of this image.

Focus on what's in the CENTER of the frame (that's what they're pointing at/asking about).

Provide:
- A clear description of what's in the center
- Whether it's a person, object, furniture, or location feature
- If it's a person: their clothing, accessories, posture
- Estimated distance from the drone

Be conversational in your description."""
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': "What's that? (Describe what's in the CENTER of this image)"
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{image_base64}'
                        }
                    }
                ]
            }
        ]
        
        result = self.chat_with_structured_output(
            messages,
            WhatsThatResult,
            model=self.vision_model
        )
        
        self.log.info(f"'What's that' result: {result.entity_type} - {result.description[:50]}...")
        return result
    
    def analyze_panorama(self, frames: List[np.ndarray]) -> PanoramaAnalysis:
        """
        Analyze a 360° panorama from multiple frames with CAREFUL DEDUPLICATION.
        
        This is the KEY method for surveying - it sends all 8 frames at once
        and asks Grok to identify UNIQUE people/objects, deduplicating ONLY
        when the same person appears in ADJACENT frames.
        
        Args:
            frames: List of 8 frames from 360° rotation (45° apart)
            
        Returns:
            PanoramaAnalysis with deduplicated people and objects
        """
        self.log.info(f"🔄 Analyzing 360° panorama ({len(frames)} frames)...")
        
        # Frame metadata for clear labeling
        frame_info = [
            {"num": 1, "angle": 0,   "direction": "AHEAD (North)",      "adjacent": [8, 2]},
            {"num": 2, "angle": 45,  "direction": "FRONT-RIGHT (NE)",   "adjacent": [1, 3]},
            {"num": 3, "angle": 90,  "direction": "RIGHT (East)",       "adjacent": [2, 4]},
            {"num": 4, "angle": 135, "direction": "BACK-RIGHT (SE)",    "adjacent": [3, 5]},
            {"num": 5, "angle": 180, "direction": "BEHIND (South)",     "adjacent": [4, 6]},
            {"num": 6, "angle": 225, "direction": "BACK-LEFT (SW)",     "adjacent": [5, 7]},
            {"num": 7, "angle": 270, "direction": "LEFT (West)",        "adjacent": [6, 8]},
            {"num": 8, "angle": 315, "direction": "FRONT-LEFT (NW)",    "adjacent": [7, 1]},
        ]
        
        # Log each frame being processed
        for i, frame in enumerate(frames):
            info = frame_info[i]
            self.log.info(f"   📷 Frame {info['num']}/8: {info['angle']}° ({info['direction']}) - {frame.shape[1]}x{frame.shape[0]}")
        
        # Convert all frames to base64
        self.log.info("   Converting frames to base64...")
        images_base64 = [self._frame_to_base64(frame) for frame in frames]
        self.log.info(f"   ✓ All {len(images_base64)} frames encoded, sending to Grok...")
        
        # Build the prompt with all images - CRITICAL: Be very explicit about deduplication rules
        system_prompt = """You are a search and rescue drone analyzing a complete 360° panorama view.

## FRAME LAYOUT (8 frames, 45° apart, completing a full circle):

```
                    Frame 1 (0° - AHEAD/North)
                           ↑
    Frame 8 (315° - NW)    |    Frame 2 (45° - NE)
                    \\      |      /
                     \\     |     /
    Frame 7 (270° - West) ← DRONE → Frame 3 (90° - East)
                     /     |     \\
                    /      |      \\
    Frame 6 (225° - SW)    |    Frame 4 (135° - SE)
                           ↓
                    Frame 5 (180° - BEHIND/South)
```

## ⚠️ CRITICAL DEDUPLICATION RULES ⚠️

A person can ONLY appear in ADJACENT frames due to camera field of view overlap!

**ADJACENT FRAME PAIRS (where the SAME person might appear twice):**
- Frame 1 ↔ Frame 2 (person on front-right edge)
- Frame 2 ↔ Frame 3 (person on right edge)
- Frame 3 ↔ Frame 4 (person on back-right edge)
- Frame 4 ↔ Frame 5 (person on back edge)
- Frame 5 ↔ Frame 6 (person on back-left edge)
- Frame 6 ↔ Frame 7 (person on left edge)
- Frame 7 ↔ Frame 8 (person on front-left edge)
- Frame 8 ↔ Frame 1 (person on front edge, wrapping around)

**NON-ADJACENT FRAMES = DIFFERENT PEOPLE!**
- Person in Frame 1 and Frame 3 = TWO DIFFERENT PEOPLE (not adjacent!)
- Person in Frame 2 and Frame 5 = TWO DIFFERENT PEOPLE (opposite sides!)
- Person in Frame 1 and Frame 5 = TWO DIFFERENT PEOPLE (opposite directions!)

**TO MERGE AS SAME PERSON, ALL must be true:**
1. Appears in ADJACENT frames only (e.g., frames 2,3 or frames 5,6)
2. SAME clothing colors and style
3. SAME approximate position (if in frame 2 they're on RIGHT edge, in frame 3 they should be on LEFT edge)
4. SAME posture (both sitting, both standing, etc.)

**WHEN IN DOUBT, COUNT AS SEPARATE PEOPLE!**
It's better to count 3 people who might be 2, than to merge 3 different people into 1.

## YOUR TASK:

**STEP 1: List people in EACH frame separately**
Go frame by frame. For each frame, list:
- How many people visible
- Brief description of each (clothing, position in frame)

**STEP 2: Check for duplicates ONLY in adjacent frames**
Look at each adjacent pair. Does the same person appear in both?
- Check: Same clothes? Same posture? Position makes sense (right edge → left edge)?

**STEP 3: Output unique people**
Each unique person gets ONE entry with:
- `person_id`: "person_1", "person_2", etc.
- `frames_visible_in`: ONLY adjacent frame numbers where they appear [e.g., [2,3] or [5,6]]
- `bounding_boxes`: Bounding box for EACH frame they appear in
- `best_frame`: Frame with clearest view
- `primary_direction`: Based on which frames they're in
- Full description, clothing, accessories, etc.

## DIRECTION MAPPING:
- Frames 1,2,8 → "ahead" or nearby
- Frames 2,3,4 → "to_my_right" 
- Frames 4,5,6 → "behind_me"
- Frames 6,7,8 → "to_my_left"

## REMEMBER:
- total_people_count MUST equal len(unique_people)
- People in non-adjacent frames are DIFFERENT people
- When uncertain, keep them as separate entries"""

        # Build content array with all images and clear per-frame instructions
        content = [
            {
                'type': 'text',
                'text': """Analyze this 360° panorama. I will show you 8 frames taken while rotating 360°.

YOUR TASK:
1. Count ALL people in each frame
2. ONLY merge people if they appear in ADJACENT frames (1↔2, 2↔3, 3↔4, 4↔5, 5↔6, 6↔7, 7↔8, 8↔1)
3. People in NON-ADJACENT frames are DIFFERENT PEOPLE even if they look similar!

For example:
- Person in frames [2,3] = ONE person (adjacent frames, could be same person)
- Person in frames [1,3] = TWO people (not adjacent, must be different!)
- Person in frames [1,5] = TWO people (opposite directions!)

Now analyzing each frame:"""
            }
        ]
        
        # Add all 8 frames with VERY clear labels
        for i, img_base64 in enumerate(images_base64):
            info = frame_info[i]
            adjacent_str = f"Adjacent to frames {info['adjacent'][0]} and {info['adjacent'][1]}"
            
            content.append({
                'type': 'text',
                'text': f"""

════════════════════════════════════════════════════════════════
FRAME {info['num']} of 8 | {info['angle']}° | {info['direction']}
{adjacent_str}
════════════════════════════════════════════════════════════════
List all people visible in this frame. Note their position (left/center/right of frame)."""
            })
            content.append({
                'type': 'image_url',
                'image_url': {
                    'url': f'data:image/jpeg;base64,{img_base64}'
                }
            })
        
        # Final instruction after all frames
        content.append({
            'type': 'text',
            'text': """

════════════════════════════════════════════════════════════════
NOW PROVIDE YOUR ANALYSIS
════════════════════════════════════════════════════════════════

Based on the 8 frames above:
1. How many UNIQUE people are there in total?
2. For each person, which frame(s) are they in?
3. Remember: ONLY merge if in ADJACENT frames AND same appearance!

Provide the structured PanoramaAnalysis output now."""
        })
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': content}
        ]
        
        # Use longer timeout for 8-image panorama analysis
        result = self.chat_with_structured_output(
            messages,
            PanoramaAnalysis,
            model=self.vision_model,
            timeout=120  # 2 minutes for processing 8 images
        )
        
        # POST-PROCESS: Validate and fix any incorrect merges
        result = self._validate_panorama_deduplication(result)
        
        # Log detailed results
        self.log.info(f"   📊 Grok Response:")
        self.log.info(f"      Scene: {result.scene_type} - {result.summary[:80]}...")
        self.log.info(f"      Total people: {result.total_people_count}")
        self.log.info(f"      Total objects: {result.total_objects_count}")
        
        for person in result.unique_people:
            bbox_count = len(person.bounding_boxes) if hasattr(person, 'bounding_boxes') else 0
            best = getattr(person, 'best_frame', '?')
            self.log.info(f"      👤 {person.person_id}: frames={person.frames_visible_in}, best={best}, bboxes={bbox_count}")
            self.log.info(f"         {person.description[:60]}...")
            if hasattr(person, 'bounding_boxes') and person.bounding_boxes:
                for bb in person.bounding_boxes:
                    self.log.debug(f"         bbox@frame{bb.frame_number}: x={bb.x:.2f} y={bb.y:.2f} w={bb.width:.2f} h={bb.height:.2f}")
        
        # Log all panorama frames and analysis
        if self.enable_image_logging:
            self.image_logger.log_panorama_frames(
                frames=frames,
                analysis_result=result,
                metadata={
                    'model': self.vision_model,
                    'method': 'analyze_panorama',
                    'unique_people': len(result.unique_people),
                    'unique_objects': len(result.unique_objects)
                }
            )
        
        self.log.success(f"✅ Panorama analysis: {result.total_people_count} unique people, {result.total_objects_count} unique objects")
        return result
    
    def _validate_panorama_deduplication(self, result: PanoramaAnalysis) -> PanoramaAnalysis:
        """
        Post-process panorama results to fix any incorrect merges.
        
        If a person is listed as appearing in non-adjacent frames,
        split them into separate people entries.
        """
        # Adjacent frame pairs (both directions)
        adjacent_pairs = {
            1: {8, 2}, 2: {1, 3}, 3: {2, 4}, 4: {3, 5},
            5: {4, 6}, 6: {5, 7}, 7: {6, 8}, 8: {7, 1}
        }
        
        def are_all_adjacent(frames: List[int]) -> bool:
            """Check if all frames in list are adjacent to each other."""
            if len(frames) <= 1:
                return True
            frames_sorted = sorted(frames)
            for i in range(len(frames_sorted) - 1):
                f1, f2 = frames_sorted[i], frames_sorted[i + 1]
                # Special case: 8 and 1 are adjacent (wrap around)
                if f2 not in adjacent_pairs.get(f1, set()):
                    # Check wrap-around case
                    if not (f1 == 1 and f2 == 8) and not (f1 == 8 and f2 == 1):
                        return False
            return True
        
        new_people = []
        person_counter = 1
        
        for person in result.unique_people:
            frames = person.frames_visible_in
            
            if are_all_adjacent(frames):
                # Valid - keep as is but renumber
                person.person_id = f"person_{person_counter}"
                new_people.append(person)
                person_counter += 1
            else:
                # Invalid merge! Split into separate people
                self.log.warning(f"⚠️ Splitting incorrectly merged person across non-adjacent frames: {frames}")
                
                # Group frames into adjacent clusters
                clusters = []
                for frame in sorted(frames):
                    added = False
                    for cluster in clusters:
                        if any(frame in adjacent_pairs.get(f, set()) for f in cluster):
                            cluster.append(frame)
                            added = True
                            break
                    if not added:
                        clusters.append([frame])
                
                # Create a new person entry for each cluster
                for cluster in clusters:
                    new_person = deepcopy(person)
                    new_person.person_id = f"person_{person_counter}"
                    new_person.frames_visible_in = cluster
                    new_person.best_frame = cluster[0]  # Use first frame of cluster
                    
                    # Filter bounding boxes to only include frames in this cluster
                    if hasattr(new_person, 'bounding_boxes') and new_person.bounding_boxes:
                        new_person.bounding_boxes = [
                            bb for bb in new_person.bounding_boxes 
                            if bb.frame_number in cluster
                        ]
                    
                    # Update direction based on cluster
                    new_person.primary_direction = self._frames_to_direction(cluster)
                    
                    new_people.append(new_person)
                    person_counter += 1
                    self.log.info(f"   Created split person_{person_counter-1} for frames {cluster}")
        
        # Update result
        result.unique_people = new_people
        result.total_people_count = len(new_people)
        
        return result
    
    def _frames_to_direction(self, frames: List[int]) -> str:
        """Convert frame numbers to a direction string."""
        avg_frame = sum(frames) / len(frames)
        
        if avg_frame <= 1.5 or avg_frame >= 7.5:
            return "ahead"
        elif 1.5 < avg_frame <= 3.5:
            return "to_my_right"
        elif 3.5 < avg_frame <= 5.5:
            return "behind_me"
        else:
            return "to_my_left"
    
    def describe_person(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Get a description of a person from a cropped image.
        
        Args:
            image: Cropped image of the person (BGR format)
            
        Returns:
            Dict with description, clothing, hair, accessories
        """
        try:
            img_base64 = self._frame_to_base64(image)
            
            messages = [
                {
                    'role': 'system',
                    'content': """You are describing a person for search and rescue identification.
Provide a brief but detailed description focusing on identifying features.
Be concise - max 2 sentences for description."""
                },
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': """Describe this person briefly:
1. Overall description (age range, gender if apparent, distinguishing features)
2. Clothing (colors, type)
3. Hair (color, style, length)
4. Accessories (glasses, hat, jewelry, etc.)

Keep it concise and factual."""
                        },
                        {
                            'type': 'image_url',
                            'image_url': {'url': f'data:image/jpeg;base64,{img_base64}'}
                        }
                    ]
                }
            ]
            
            response = requests.post(
                f'{self.api_base}/chat/completions',
                headers=self.headers,
                json={
                    'model': self.vision_model,
                    'messages': messages,
                    'max_tokens': 300
                },
                timeout=30
            )
            response.raise_for_status()
            text = response.json()['choices'][0]['message']['content']
            
            # Parse the response into structured data
            description = text.strip()
            clothing = ''
            hair = ''
            accessories = []
            
            # Simple parsing - look for keywords
            lines = text.lower().split('\n')
            for line in lines:
                if 'clothing' in line or 'wearing' in line or 'shirt' in line or 'pants' in line:
                    clothing = line.strip()
                elif 'hair' in line:
                    hair = line.strip()
                elif 'accessories' in line or 'glasses' in line or 'hat' in line:
                    accessories = [a.strip() for a in line.split(',') if a.strip()]
            
            return {
                'description': description[:200] if description else 'Person',
                'clothing': clothing[:100] if clothing else '',
                'hair': hair[:50] if hair else '',
                'accessories': accessories[:5] if accessories else []
            }
            
        except Exception as e:
            self.log.warning(f"Could not describe person: {e}")
            return {
                'description': 'Person',
                'clothing': '',
                'hair': '',
                'accessories': []
            }
    
    def __repr__(self) -> str:
        """String representation."""
        return f"GrokClient(model={self.model}, vision_model={self.vision_model})"
