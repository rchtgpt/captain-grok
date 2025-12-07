"""
xAI Grok API client for text generation and vision analysis.
Supports structured outputs and extended thinking/reasoning.
"""

import requests
import json
import base64
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
    SEARCH_PROMPT_TEMPLATE
)
from .schemas import (
    VisionAnalysis,
    SearchResult,
    CommandResponse,
    ReasoningTrace
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
    
    def chat_with_structured_output(
        self,
        messages: List[Dict[str, Any]],
        response_format: Type[T],
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> T:
        """
        Send a chat request with structured output using Pydantic schema.
        
        Args:
            messages: List of message dicts
            response_format: Pydantic model class for response structure
            model: Model to use (defaults to self.model)
            temperature: Sampling temperature
            
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
            self.log.debug(f"Sending structured output request (format: {response_format.__name__})")
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=60
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
            
            # Parse JSON content into Pydantic model
            parsed = response_format.model_validate_json(content)
            
            self.log.success(f"Parsed structured output: {response_format.__name__}")
            return parsed
        
        except requests.exceptions.RequestException as e:
            self.log.error(f"Structured output API request failed: {e}")
            raise GrokAPIError(f"Grok API request failed: {e}")
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
    
    def __repr__(self) -> str:
        """String representation."""
        return f"GrokClient(model={self.model}, vision_model={self.vision_model})"
