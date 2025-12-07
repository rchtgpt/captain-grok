"""
Dual Verification System for high-confidence face matching.

Combines:
1. CV-based face_recognition library (local, fast)
2. Grok Vision API (cloud, contextual understanding)

Both run in parallel for maximum accuracy.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional, Tuple, List, TYPE_CHECKING
import numpy as np

from core.logger import get_logger

if TYPE_CHECKING:
    from core.face_recognition_service import FaceRecognitionService
    from core.targets import Target
    from ai.grok_client import GrokClient

log = get_logger('dual_verification')


@dataclass
class VerificationResult:
    """Result of dual verification."""
    is_match: bool
    confidence: float
    confidence_level: str  # 'high', 'medium', 'low'
    cv_matched: bool
    cv_confidence: float
    grok_matched: bool
    grok_confidence: float
    grok_description: str  # What Grok saw
    bbox: Optional[dict] = None  # Bounding box if face detected


class DualVerifier:
    """
    Parallel CV + Grok verification for high-confidence face matching.
    
    Confidence Levels:
    - HIGH: Both CV and Grok agree on match (most reliable)
    - MEDIUM: Only CV matches with very high confidence (> 0.75)
    - LOW: No agreement or low confidence (ignored)
    
    Thresholds:
    - CV match: face_recognition distance < 0.5 (default)
    - Grok match: explicit "yes" response with confidence
    """
    
    # Thresholds
    CV_MATCH_THRESHOLD = 0.5  # face_recognition distance (lower = better match)
    CV_HIGH_CONFIDENCE_THRESHOLD = 0.25  # Very confident CV match (can stand alone)
    GROK_CONFIDENCE_THRESHOLD = 0.7  # Grok must be this confident
    
    def __init__(
        self, 
        face_service: 'FaceRecognitionService',
        grok_client: 'GrokClient'
    ):
        """
        Initialize dual verifier.
        
        Args:
            face_service: Face recognition service for CV-based matching
            grok_client: Grok client for vision API calls
        """
        self.face_service = face_service
        self.grok = grok_client
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        log.info("DualVerifier initialized (parallel CV + Grok)")
    
    def verify(
        self, 
        frame: np.ndarray, 
        target: 'Target',
        bbox: Optional[dict] = None
    ) -> VerificationResult:
        """
        Verify if a face in the frame matches the target.
        Runs CV and Grok checks in parallel.
        
        Args:
            frame: BGR image from camera
            target: Target to match against (must have face_embeddings)
            bbox: Optional bounding box to focus on specific face
            
        Returns:
            VerificationResult with match status and confidence
        """
        if not target.face_embeddings:
            log.warning(f"Target '{target.name}' has no face embeddings")
            return VerificationResult(
                is_match=False,
                confidence=0.0,
                confidence_level='low',
                cv_matched=False,
                cv_confidence=0.0,
                grok_matched=False,
                grok_confidence=0.0,
                grok_description="No face data for target"
            )
        
        # Run both checks in parallel
        cv_future = self._executor.submit(
            self._cv_check, frame, target, bbox
        )
        grok_future = self._executor.submit(
            self._grok_check, frame, target
        )
        
        # Wait for both to complete
        cv_result = cv_future.result()
        grok_result = grok_future.result()
        
        # Combine results
        return self._combine_results(cv_result, grok_result, bbox)
    
    def verify_quick(
        self,
        frame: np.ndarray,
        target: 'Target',
        bbox: Optional[dict] = None
    ) -> VerificationResult:
        """
        Quick CV-only verification (for tailing/real-time use).
        Faster but less accurate than full dual verification.
        
        Args:
            frame: BGR image
            target: Target to match
            bbox: Optional bounding box
            
        Returns:
            VerificationResult (Grok fields will be empty)
        """
        cv_matched, cv_confidence, detected_bbox = self._cv_check(frame, target, bbox)
        
        # Determine confidence level based on CV alone
        if cv_matched and cv_confidence > 0.75:
            confidence_level = 'high'
        elif cv_matched and cv_confidence > 0.5:
            confidence_level = 'medium'
        else:
            confidence_level = 'low'
        
        return VerificationResult(
            is_match=cv_matched,
            confidence=cv_confidence,
            confidence_level=confidence_level,
            cv_matched=cv_matched,
            cv_confidence=cv_confidence,
            grok_matched=False,
            grok_confidence=0.0,
            grok_description="Quick verification (CV only)",
            bbox=detected_bbox or bbox
        )
    
    def _cv_check(
        self, 
        frame: np.ndarray, 
        target: 'Target',
        bbox: Optional[dict] = None
    ) -> Tuple[bool, float, Optional[dict]]:
        """
        CV-based face recognition check.
        
        Returns:
            (is_match, confidence, detected_bbox)
        """
        try:
            if not self.face_service.is_available:
                log.warning("Face service not available")
                return False, 0.0, None
            
            # If bbox provided, crop to that region
            if bbox:
                h, w = frame.shape[:2]
                x1 = int(bbox['x'] * w)
                y1 = int(bbox['y'] * h)
                x2 = int((bbox['x'] + bbox['width']) * w)
                y2 = int((bbox['y'] + bbox['height']) * h)
                frame_region = frame[y1:y2, x1:x2]
            else:
                frame_region = frame
            
            # Extract face embedding from frame
            detections = self.face_service.extract_all_faces(frame_region)
            
            if not detections:
                return False, 0.0, None
            
            # Check each detected face against target's embeddings
            best_match_distance = float('inf')
            best_bbox = None
            
            for detection in detections:
                if detection.embedding is None:
                    continue
                
                # Compare against all target embeddings
                for target_embedding in target.face_embeddings:
                    distance = self.face_service.compare_embeddings(
                        detection.embedding,
                        target_embedding
                    )
                    
                    if distance < best_match_distance:
                        best_match_distance = distance
                        # Adjust bbox if we cropped
                        if bbox:
                            # Convert back to full frame coordinates
                            h, w = frame.shape[:2]
                            bx = bbox['x'] + detection.bbox['x'] * bbox['width']
                            by = bbox['y'] + detection.bbox['y'] * bbox['height']
                            bw = detection.bbox['width'] * bbox['width']
                            bh = detection.bbox['height'] * bbox['height']
                            best_bbox = {'x': bx, 'y': by, 'width': bw, 'height': bh}
                        else:
                            best_bbox = detection.bbox
            
            # Convert distance to confidence (0 = perfect match, 1 = no match)
            # distance of 0.5 = threshold, so confidence = 1 - (distance / 0.5) capped at 0-1
            if best_match_distance < self.CV_MATCH_THRESHOLD:
                confidence = 1.0 - (best_match_distance / self.CV_MATCH_THRESHOLD)
                confidence = min(1.0, max(0.0, confidence))
                log.debug(f"CV match: distance={best_match_distance:.3f}, confidence={confidence:.2%}")
                return True, confidence, best_bbox
            else:
                confidence = max(0.0, 1.0 - best_match_distance)
                return False, confidence, best_bbox
                
        except Exception as e:
            log.error(f"CV check error: {e}")
            return False, 0.0, None
    
    def _grok_check(
        self, 
        frame: np.ndarray, 
        target: 'Target'
    ) -> Tuple[bool, float, str]:
        """
        Grok Vision API check.
        
        Returns:
            (is_match, confidence, description)
        """
        try:
            # Build prompt for Grok
            prompt = self._build_grok_prompt(target)
            
            # Call Grok Vision
            response = self.grok.analyze_image(
                frame,
                prompt,
                json_response=True
            )
            
            # Parse response
            return self._parse_grok_response(response, target)
            
        except Exception as e:
            log.error(f"Grok check error: {e}")
            return False, 0.0, f"Error: {str(e)}"
    
    def _build_grok_prompt(self, target: 'Target') -> str:
        """Build the prompt for Grok vision analysis."""
        prompt = f"""Analyze this image for facial recognition verification.

TARGET PERSON: {target.name}
DESCRIPTION: {target.description or 'No description provided'}

TASK: Determine if the target person "{target.name}" is visible in this image.

RESPOND IN JSON FORMAT:
{{
    "person_visible": true/false,
    "is_target": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "person_description": "what you see"
}}

GUIDELINES:
- Look for facial features, not just clothing
- Consider the description if provided
- Be conservative - only say "is_target: true" if confident
- confidence should reflect how certain you are
"""
        return prompt
    
    def _parse_grok_response(
        self, 
        response: dict, 
        target: 'Target'
    ) -> Tuple[bool, float, str]:
        """Parse Grok's JSON response."""
        try:
            # Handle different response formats
            if isinstance(response, str):
                import json
                response = json.loads(response)
            
            person_visible = response.get('person_visible', False)
            is_target = response.get('is_target', False)
            confidence = float(response.get('confidence', 0.0))
            description = response.get('person_description', response.get('reasoning', ''))
            
            if not person_visible:
                return False, 0.0, "No person visible"
            
            if is_target and confidence >= self.GROK_CONFIDENCE_THRESHOLD:
                log.debug(f"Grok match: confidence={confidence:.2%}, desc={description}")
                return True, confidence, description
            else:
                return False, confidence, description
                
        except Exception as e:
            log.error(f"Error parsing Grok response: {e}")
            # Try to extract any useful info
            if isinstance(response, dict):
                desc = response.get('error', str(response))
            else:
                desc = str(response)
            return False, 0.0, desc
    
    def _combine_results(
        self,
        cv_result: Tuple[bool, float, Optional[dict]],
        grok_result: Tuple[bool, float, str],
        original_bbox: Optional[dict]
    ) -> VerificationResult:
        """
        Combine CV and Grok results into final verification.
        
        Confidence levels:
        - HIGH: Both agree on match
        - MEDIUM: Only CV with very high confidence
        - LOW: No match or disagreement
        """
        cv_matched, cv_confidence, detected_bbox = cv_result
        grok_matched, grok_confidence, grok_description = grok_result
        
        # Determine final result
        if cv_matched and grok_matched:
            # Both agree - HIGH confidence
            combined_confidence = (cv_confidence + grok_confidence) / 2
            return VerificationResult(
                is_match=True,
                confidence=combined_confidence,
                confidence_level='high',
                cv_matched=True,
                cv_confidence=cv_confidence,
                grok_matched=True,
                grok_confidence=grok_confidence,
                grok_description=grok_description,
                bbox=detected_bbox or original_bbox
            )
        
        elif cv_matched and cv_confidence > 0.75:
            # CV very confident alone - MEDIUM confidence
            return VerificationResult(
                is_match=True,
                confidence=cv_confidence,
                confidence_level='medium',
                cv_matched=True,
                cv_confidence=cv_confidence,
                grok_matched=False,
                grok_confidence=grok_confidence,
                grok_description=grok_description,
                bbox=detected_bbox or original_bbox
            )
        
        else:
            # No match or low confidence
            return VerificationResult(
                is_match=False,
                confidence=max(cv_confidence, grok_confidence) * 0.5,
                confidence_level='low',
                cv_matched=cv_matched,
                cv_confidence=cv_confidence,
                grok_matched=grok_matched,
                grok_confidence=grok_confidence,
                grok_description=grok_description,
                bbox=detected_bbox or original_bbox
            )
    
    def shutdown(self):
        """Shutdown the executor."""
        self._executor.shutdown(wait=False)


# Singleton instance
_verifier: Optional[DualVerifier] = None
_verifier_lock = threading.Lock()


def get_dual_verifier(
    face_service: Optional['FaceRecognitionService'] = None,
    grok_client: Optional['GrokClient'] = None
) -> Optional[DualVerifier]:
    """
    Get the singleton DualVerifier instance.
    
    On first call, must provide face_service and grok_client.
    """
    global _verifier
    with _verifier_lock:
        if _verifier is None:
            if face_service is None or grok_client is None:
                log.warning("DualVerifier not initialized - need face_service and grok_client")
                return None
            _verifier = DualVerifier(face_service, grok_client)
        return _verifier


def init_dual_verifier(
    face_service: 'FaceRecognitionService',
    grok_client: 'GrokClient'
) -> DualVerifier:
    """Initialize the dual verifier with required dependencies."""
    global _verifier
    with _verifier_lock:
        _verifier = DualVerifier(face_service, grok_client)
        return _verifier
