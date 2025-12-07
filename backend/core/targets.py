"""
Target Management System for Search & Rescue.
Manages targets (people to find) with facial recognition support.
"""

import threading
import json
import uuid
import shutil
import cv2
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Literal, Tuple, Any
from pathlib import Path

from core.logger import get_logger
from core.face_recognition_service import get_face_service, FaceDetection

log = get_logger('targets')


@dataclass
class Target:
    """A person to search for."""
    id: str
    name: str
    description: str
    reference_photos: List[str]  # File paths to uploaded photos
    face_embeddings: List[List[float]]  # Face embeddings from photos
    status: Literal['searching', 'found', 'confirmed']
    found_entity_id: Optional[str]  # Links to Entity when found
    matched_photos: List[str]  # Photos from drone when found
    match_confidence: float
    created_at: str
    found_at: Optional[str]
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "reference_photos": self.reference_photos,
            "face_embeddings": self.face_embeddings,
            "status": self.status,
            "found_entity_id": self.found_entity_id,
            "matched_photos": self.matched_photos,
            "match_confidence": self.match_confidence,
            "created_at": self.created_at,
            "found_at": self.found_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Target':
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            reference_photos=data.get('reference_photos', []),
            face_embeddings=data.get('face_embeddings', []),
            status=data.get('status', 'searching'),
            found_entity_id=data.get('found_entity_id'),
            matched_photos=data.get('matched_photos', []),
            match_confidence=data.get('match_confidence', 0.0),
            created_at=data.get('created_at', datetime.now().isoformat()),
            found_at=data.get('found_at')
        )


@dataclass
class TargetMatch:
    """Result of matching a face to a target."""
    target: Target
    confidence: float
    bbox: Dict[str, float]
    matched_photo_path: Optional[str] = None


class TargetManager:
    """
    Manages search targets with facial recognition.
    
    Features:
    - Add/remove targets with reference photos
    - Extract face embeddings from photos
    - Match faces during drone search
    - Persist targets to JSON
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            # Use absolute path relative to the backend directory
            backend_dir = Path(__file__).parent.parent
            data_dir = backend_dir / "data" / "targets"
        
        self.data_dir = Path(data_dir).resolve()  # Always use absolute path
        self.photos_dir = self.data_dir / "photos"
        self.matched_dir = self.data_dir / "matched"
        
        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.photos_dir.mkdir(exist_ok=True)
        self.matched_dir.mkdir(exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Targets storage
        self._targets: Dict[str, Target] = {}
        self._name_index: Dict[str, str] = {}  # lowercase name -> target_id
        
        # Face service
        self._face_service = get_face_service()
        
        # Load existing targets
        self.load()
        
        log.info(f"TargetManager initialized. Data dir: {self.data_dir}, Targets: {len(self._targets)}")
    
    # ==================== CRUD Operations ====================
    
    def add_target(
        self, 
        name: str, 
        description: str = "",
        photo_paths: Optional[List[str]] = None
    ) -> Target:
        """
        Add a new target to search for.
        
        Args:
            name: Name of the person
            description: Optional description (clothing, features)
            photo_paths: Optional list of reference photo paths
            
        Returns:
            Created Target
        """
        with self._lock:
            # Generate ID
            target_id = f"target_{uuid.uuid4().hex[:8]}"
            
            # Process photos and extract embeddings
            saved_photos = []
            embeddings = []
            
            if photo_paths:
                for photo_path in photo_paths:
                    try:
                        # Copy photo to targets directory
                        src = Path(photo_path)
                        if src.exists():
                            dest = self.photos_dir / f"{target_id}_{len(saved_photos)}{src.suffix}"
                            shutil.copy(src, dest)
                            # Always store absolute paths
                            saved_photos.append(str(dest.resolve()))
                            
                            # Extract face embedding
                            img = cv2.imread(str(dest))
                            if img is not None:
                                embedding = self._face_service.extract_embedding(img)
                                if embedding:
                                    embeddings.append(embedding)
                                    log.info(f"Extracted embedding from {src.name}")
                                else:
                                    log.warning(f"No face found in {src.name}")
                    except Exception as e:
                        log.error(f"Error processing photo {photo_path}: {e}")
            
            # Create target
            target = Target(
                id=target_id,
                name=name,
                description=description,
                reference_photos=saved_photos,
                face_embeddings=embeddings,
                status='searching',
                found_entity_id=None,
                matched_photos=[],
                match_confidence=0.0,
                created_at=datetime.now().isoformat(),
                found_at=None
            )
            
            self._targets[target_id] = target
            self._name_index[name.lower()] = target_id
            
            self.save()
            
            log.info(f"Added target: {name} (id={target_id}, {len(embeddings)} face embeddings)")
            return target
    
    def get_target(self, target_id: str) -> Optional[Target]:
        """Get target by ID."""
        with self._lock:
            return self._targets.get(target_id)
    
    def get_target_by_name(self, name: str, use_fuzzy: bool = True) -> Optional[Target]:
        """
        Get target by name (case-insensitive).
        
        If exact match fails and use_fuzzy=True, uses LLM to fuzzy match
        the query to available target names (handles typos like "Ratchet" -> "Rachit").
        """
        with self._lock:
            # Try exact match first
            target_id = self._name_index.get(name.lower())
            if target_id:
                return self._targets.get(target_id)
            
            # Try fuzzy matching with LLM
            if use_fuzzy and self._targets:
                matched_name = self._fuzzy_match_name(name)
                if matched_name:
                    target_id = self._name_index.get(matched_name.lower())
                    if target_id:
                        log.info(f"Fuzzy matched '{name}' -> '{matched_name}'")
                        return self._targets.get(target_id)
            
            return None
    
    def _fuzzy_match_name(self, query: str) -> Optional[str]:
        """
        Use LLM to fuzzy match a user query to available target names.
        Handles typos, phonetic similarities, nicknames, etc.
        """
        try:
            from ai.grok_client import GrokClient
            from ai.schemas import TargetNameMatch
            from config.settings import get_settings
            
            # Get list of target names
            target_names = [t.name for t in self._targets.values()]
            if not target_names:
                return None
            
            # Create a simple Grok client for this query
            grok = GrokClient(get_settings())
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a name matching assistant. Match user queries to target names, handling typos and phonetic similarities."
                },
                {
                    "role": "user",
                    "content": f"The user is looking for: '{query}'\n\nAvailable targets: {target_names}\n\nDoes the query match any target? Consider typos (e.g., 'Ratchet' matches 'Rachit'), nicknames, and phonetic similarities."
                }
            ]
            
            result = grok.chat_with_structured_output(
                messages=messages,
                response_format=TargetNameMatch,
                temperature=0.1,
                timeout=10
            )
            
            if result.matched and result.target_name and result.confidence >= 0.6:
                log.info(f"LLM fuzzy match: '{query}' -> '{result.target_name}' ({result.confidence:.0%} confidence, reason: {result.reasoning})")
                return result.target_name
            else:
                log.debug(f"No fuzzy match for '{query}': {result.reasoning}")
                return None
                
        except Exception as e:
            log.warning(f"Fuzzy matching failed: {e}")
            return None
    
    def get_all_targets(self) -> List[Target]:
        """Get all targets."""
        with self._lock:
            return list(self._targets.values())
    
    def update_target(self, target_id: str, **kwargs) -> Optional[Target]:
        """Update target fields."""
        with self._lock:
            target = self._targets.get(target_id)
            if not target:
                return None
            
            # Update name index if name changed
            if 'name' in kwargs and kwargs['name'] != target.name:
                del self._name_index[target.name.lower()]
                self._name_index[kwargs['name'].lower()] = target_id
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(target, key):
                    setattr(target, key, value)
            
            self.save()
            return target
    
    def delete_target(self, target_id: str) -> bool:
        """Delete a target and its photos."""
        with self._lock:
            target = self._targets.get(target_id)
            if not target:
                return False
            
            # Remove from indexes
            del self._targets[target_id]
            if target.name.lower() in self._name_index:
                del self._name_index[target.name.lower()]
            
            # Delete photos
            for photo_path in target.reference_photos + target.matched_photos:
                try:
                    Path(photo_path).unlink(missing_ok=True)
                except Exception as e:
                    log.warning(f"Could not delete photo {photo_path}: {e}")
            
            self.save()
            log.info(f"Deleted target: {target.name}")
            return True
    
    def add_photos(self, target_id: str, photo_paths: List[str]) -> Optional[Target]:
        """Add more reference photos to a target."""
        with self._lock:
            target = self._targets.get(target_id)
            if not target:
                return None
            
            for photo_path in photo_paths:
                try:
                    src = Path(photo_path)
                    if src.exists():
                        dest = self.photos_dir / f"{target_id}_{len(target.reference_photos)}{src.suffix}"
                        shutil.copy(src, dest)
                        # Always store absolute paths
                        target.reference_photos.append(str(dest.resolve()))
                        
                        # Extract face embedding
                        img = cv2.imread(str(dest))
                        if img is not None:
                            embedding = self._face_service.extract_embedding(img)
                            if embedding:
                                target.face_embeddings.append(embedding)
                                log.info(f"Added embedding from {src.name}")
                except Exception as e:
                    log.error(f"Error adding photo {photo_path}: {e}")
            
            self.save()
            return target
    
    def add_photo_from_bytes(self, target_id: str, photo_data: bytes, filename: str) -> Optional[Target]:
        """Add a photo from raw bytes (for API uploads)."""
        with self._lock:
            target = self._targets.get(target_id)
            if not target:
                return None
            
            try:
                # Save photo
                ext = Path(filename).suffix or '.jpg'
                dest = self.photos_dir / f"{target_id}_{len(target.reference_photos)}{ext}"
                
                with open(dest, 'wb') as f:
                    f.write(photo_data)
                
                # Always store absolute paths
                target.reference_photos.append(str(dest.resolve()))
                
                # Extract face embedding
                img = cv2.imread(str(dest))
                if img is not None:
                    embedding = self._face_service.extract_embedding(img)
                    if embedding:
                        target.face_embeddings.append(embedding)
                        log.info(f"Added embedding from uploaded photo")
                
                self.save()
                return target
                
            except Exception as e:
                log.error(f"Error adding photo from bytes: {e}")
                return None
    
    # ==================== Face Matching ====================
    
    def match_frame(self, frame: np.ndarray) -> List[TargetMatch]:
        """
        Match faces in a frame against all targets.
        
        Args:
            frame: BGR image from drone camera
            
        Returns:
            List of TargetMatch objects for matches found
        """
        if not self._face_service.is_available:
            return []
        
        with self._lock:
            # Get all targets with embeddings
            targets_with_embeddings = [
                (t.id, t.face_embeddings) 
                for t in self._targets.values() 
                if t.face_embeddings and t.status == 'searching'
            ]
            
            if not targets_with_embeddings:
                return []
            
            # Detect faces in frame
            face_detections = self._face_service.extract_all_faces(frame)
            
            if not face_detections:
                return []
            
            matches = []
            
            for detection in face_detections:
                # Find best matching target
                result = self._face_service.find_best_match(
                    detection.embedding,
                    targets_with_embeddings
                )
                
                if result:
                    target_id, confidence = result
                    target = self._targets.get(target_id)
                    
                    if target:
                        matches.append(TargetMatch(
                            target=target,
                            confidence=confidence,
                            bbox=detection.bbox
                        ))
                        log.info(f"Matched target '{target.name}' with {confidence:.1%} confidence")
            
            return matches
    
    def mark_found(
        self, 
        target_id: str, 
        entity_id: str, 
        frame: Optional[np.ndarray] = None,
        confidence: float = 0.0
    ) -> Optional[Target]:
        """
        Mark a target as found and link to entity.
        
        Args:
            target_id: Target ID
            entity_id: Entity ID in memory
            frame: Optional frame to save as matched photo
            confidence: Match confidence (0-1)
        """
        with self._lock:
            target = self._targets.get(target_id)
            if not target:
                return None
            
            target.status = 'found'
            target.found_entity_id = entity_id
            target.found_at = datetime.now().isoformat()
            target.match_confidence = max(target.match_confidence, confidence)
            
            # Save matched photo
            if frame is not None:
                try:
                    photo_path = self.matched_dir / f"{target_id}_match_{len(target.matched_photos)}.jpg"
                    cv2.imwrite(str(photo_path), frame)
                    target.matched_photos.append(str(photo_path))
                    log.info(f"Saved matched photo for target '{target.name}'")
                except Exception as e:
                    log.error(f"Error saving matched photo: {e}")
            
            self.save()
            log.success(f"Target '{target.name}' marked as FOUND (entity={entity_id}, confidence={confidence:.1%})")
            return target
    
    def save_matched_photo(
        self,
        target_id: str,
        frame: np.ndarray,
        bbox: Optional[Dict[str, float]] = None
    ) -> Optional[str]:
        """Save a matched photo, optionally cropping to face bbox."""
        with self._lock:
            target = self._targets.get(target_id)
            if not target:
                return None
            
            try:
                # Crop to face if bbox provided
                if bbox:
                    h, w = frame.shape[:2]
                    x = int(bbox['x'] * w)
                    y = int(bbox['y'] * h)
                    bw = int(bbox['width'] * w)
                    bh = int(bbox['height'] * h)
                    
                    # Add padding
                    padding = int(min(bw, bh) * 0.3)
                    x = max(0, x - padding)
                    y = max(0, y - padding)
                    bw = min(w - x, bw + 2 * padding)
                    bh = min(h - y, bh + 2 * padding)
                    
                    frame = frame[y:y+bh, x:x+bw]
                
                # Save photo
                photo_path = self.matched_dir / f"{target_id}_match_{len(target.matched_photos)}.jpg"
                cv2.imwrite(str(photo_path), frame)
                # Always store absolute paths
                abs_path = str(photo_path.resolve())
                target.matched_photos.append(abs_path)
                
                self.save()
                return abs_path
                
            except Exception as e:
                log.error(f"Error saving matched photo: {e}")
                return None
    
    # ==================== Persistence ====================
    
    def save(self) -> None:
        """Save targets to JSON file."""
        with self._lock:
            data = {
                "targets": {tid: t.to_dict() for tid, t in self._targets.items()},
                "name_index": self._name_index
            }
            
            targets_file = self.data_dir / "targets.json"
            with open(targets_file, 'w') as f:
                json.dump(data, f, indent=2)
    
    def load(self) -> None:
        """Load targets from JSON file."""
        targets_file = self.data_dir / "targets.json"
        
        if not targets_file.exists():
            log.info("No existing targets file found")
            return
        
        try:
            with open(targets_file, 'r') as f:
                data = json.load(f)
            
            self._targets = {
                tid: Target.from_dict(tdata) 
                for tid, tdata in data.get('targets', {}).items()
            }
            self._name_index = data.get('name_index', {})
            
            log.info(f"Loaded {len(self._targets)} targets from disk")
            
        except Exception as e:
            log.error(f"Error loading targets: {e}")
    
    # ==================== Stats ====================
    
    @property
    def total_count(self) -> int:
        with self._lock:
            return len(self._targets)
    
    @property
    def found_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._targets.values() if t.status in ('found', 'confirmed'))
    
    @property
    def searching_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._targets.values() if t.status == 'searching')


# Singleton instance
_target_manager: Optional[TargetManager] = None
_target_manager_lock = threading.Lock()


def get_target_manager() -> TargetManager:
    """Get the singleton TargetManager instance."""
    global _target_manager
    with _target_manager_lock:
        if _target_manager is None:
            _target_manager = TargetManager()
        return _target_manager


def init_target_manager(data_dir: Optional[Path] = None) -> TargetManager:
    """Initialize the target manager with a specific data directory."""
    global _target_manager
    with _target_manager_lock:
        _target_manager = TargetManager(data_dir)
        return _target_manager
