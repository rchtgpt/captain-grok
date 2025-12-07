"""
Image logging utility for Grok vision processing.
Saves images and their analysis outputs in organized folder structure.
"""

import os
import json
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from core.logger import get_logger


class ImageLogger:
    """
    Handles logging of images sent to Grok and their analysis results.
    Creates organized folder structure: logs/vision_logs/run_<timestamp>/image_<n>/
    """
    
    def __init__(self, base_log_dir: Optional[str] = None):
        """
        Initialize the image logger.
        
        Args:
            base_log_dir: Base directory for logs (defaults to 'logs/vision_logs')
        """
        self.log = get_logger('image_logger')
        
        # Set up base directory
        if base_log_dir is None:
            base_log_dir = os.path.join(os.getcwd(), 'logs', 'vision_logs')
        
        self.base_log_dir = Path(base_log_dir)
        
        # Create new run directory with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.run_dir = self.base_log_dir / f'run_{timestamp}'
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        # Counter for images in this run
        self.image_counter = 0
        
        # Create run metadata
        self.run_metadata = {
            'run_id': timestamp,
            'start_time': datetime.now().isoformat(),
            'images_processed': 0
        }
        
        self.log.info(f"📁 Vision logging initialized: {self.run_dir}")
    
    def log_vision_request(
        self,
        frame: np.ndarray,
        prompt: str,
        response: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a vision processing request with image and output.
        
        Args:
            frame: The image that was analyzed (numpy array)
            prompt: The prompt/question asked about the image
            response: The response from Grok (can be string or structured object)
            metadata: Additional metadata to save (model, temperature, etc.)
            
        Returns:
            Path to the created log directory
        """
        # Increment counter
        self.image_counter += 1
        
        # Create directory for this image
        image_dir = self.run_dir / f'image_{self.image_counter:04d}'
        image_dir.mkdir(exist_ok=True)
        
        # Save the image
        image_path = image_dir / 'input_image.jpg'
        try:
            cv2.imwrite(str(image_path), frame)
            self.log.debug(f"💾 Saved image: {image_path}")
        except Exception as e:
            self.log.error(f"Failed to save image: {e}")
        
        # Prepare output data
        output_data = {
            'image_id': self.image_counter,
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt,
            'metadata': metadata or {},
        }
        
        # Handle different response types
        if hasattr(response, 'model_dump'):
            # Pydantic model - convert to dict
            output_data['response'] = response.model_dump()
            output_data['response_type'] = 'structured'
        elif isinstance(response, dict):
            output_data['response'] = response
            output_data['response_type'] = 'dict'
        elif isinstance(response, str):
            output_data['response'] = response
            output_data['response_type'] = 'text'
        else:
            output_data['response'] = str(response)
            output_data['response_type'] = 'unknown'
        
        # Save JSON output
        output_path = image_dir / 'analysis_output.json'
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            self.log.debug(f"💾 Saved analysis: {output_path}")
        except Exception as e:
            self.log.error(f"Failed to save analysis output: {e}")
        
        # Save human-readable text summary
        summary_path = image_dir / 'summary.txt'
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"Vision Analysis #{self.image_counter}\n")
                f.write(f"{'=' * 60}\n\n")
                f.write(f"Timestamp: {output_data['timestamp']}\n")
                f.write(f"Prompt: {prompt}\n\n")
                f.write(f"Response Type: {output_data['response_type']}\n")
                f.write(f"{'=' * 60}\n\n")
                
                if output_data['response_type'] == 'text':
                    f.write(f"Response:\n{response}\n")
                elif output_data['response_type'] == 'structured':
                    f.write("Structured Response:\n")
                    f.write(json.dumps(output_data['response'], indent=2))
                else:
                    f.write(f"Response:\n{json.dumps(output_data['response'], indent=2)}\n")
                
                if metadata:
                    f.write(f"\n{'=' * 60}\n")
                    f.write("Metadata:\n")
                    for key, value in metadata.items():
                        f.write(f"  {key}: {value}\n")
            
            self.log.debug(f"💾 Saved summary: {summary_path}")
        except Exception as e:
            self.log.error(f"Failed to save summary: {e}")
        
        # Update run metadata
        self.run_metadata['images_processed'] = self.image_counter
        self._save_run_metadata()
        
        self.log.success(f"📸 Logged vision request #{self.image_counter} → {image_dir.name}")
        
        return str(image_dir)
    
    def log_search_request(
        self,
        frame: np.ndarray,
        target: str,
        found: bool,
        angle: Optional[int] = None,
        result: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a search request specifically.
        
        Args:
            frame: The image that was searched
            target: What was being searched for
            found: Whether the target was found
            angle: Rotation angle when captured (if applicable)
            result: The search result object
            metadata: Additional metadata
            
        Returns:
            Path to the created log directory
        """
        enriched_prompt = f"SEARCH: Looking for '{target}'"
        if angle is not None:
            enriched_prompt += f" at {angle}°"
        
        enriched_metadata = metadata or {}
        enriched_metadata.update({
            'operation': 'search',
            'target': target,
            'found': found,
            'angle': angle
        })
        
        return self.log_vision_request(
            frame=frame,
            prompt=enriched_prompt,
            response=result,
            metadata=enriched_metadata
        )
    
    def log_panorama_frames(
        self,
        frames: list,
        analysis_result: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log all 8 panorama frames together with their analysis.
        
        Args:
            frames: List of 8 frames from 360° rotation
            analysis_result: The PanoramaAnalysis result from Grok
            metadata: Additional metadata
            
        Returns:
            Path to the panorama log directory
        """
        # Create panorama directory
        self.image_counter += 1
        panorama_dir = self.run_dir / f'panorama_{self.image_counter:04d}'
        panorama_dir.mkdir(exist_ok=True)
        
        directions = ["ahead", "front-right", "right", "back-right", "behind", "back-left", "left", "front-left"]
        
        # Save each frame
        frame_paths = []
        for i, frame in enumerate(frames):
            if frame is not None:
                angle = i * 45
                direction = directions[i]
                filename = f'frame_{i+1}_{angle}deg_{direction}.jpg'
                frame_path = panorama_dir / filename
                try:
                    cv2.imwrite(str(frame_path), frame)
                    frame_paths.append(filename)
                    self.log.debug(f"💾 Saved panorama frame {i+1}: {filename}")
                except Exception as e:
                    self.log.error(f"Failed to save panorama frame {i+1}: {e}")
                    frame_paths.append(None)
            else:
                frame_paths.append(None)
        
        # Save analysis output
        output_data = {
            'panorama_id': self.image_counter,
            'timestamp': datetime.now().isoformat(),
            'num_frames': len(frames),
            'frame_files': frame_paths,
            'metadata': metadata or {},
        }
        
        if analysis_result:
            if hasattr(analysis_result, 'model_dump'):
                output_data['analysis'] = analysis_result.model_dump()
            elif isinstance(analysis_result, dict):
                output_data['analysis'] = analysis_result
            else:
                output_data['analysis'] = str(analysis_result)
        
        output_path = panorama_dir / 'panorama_analysis.json'
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log.error(f"Failed to save panorama analysis: {e}")
        
        # Save summary
        summary_path = panorama_dir / 'summary.txt'
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"360° Panorama Analysis #{self.image_counter}\n")
                f.write(f"{'=' * 60}\n\n")
                f.write(f"Timestamp: {output_data['timestamp']}\n")
                f.write(f"Frames captured: {len([p for p in frame_paths if p])}/8\n\n")
                
                f.write("Frames:\n")
                for i, fp in enumerate(frame_paths):
                    angle = i * 45
                    direction = directions[i]
                    status = "✓" if fp else "✗"
                    f.write(f"  {status} Frame {i+1}: {angle}° ({direction}) - {fp or 'MISSING'}\n")
                
                if analysis_result and hasattr(analysis_result, 'total_people_count'):
                    f.write(f"\n{'=' * 60}\n")
                    f.write("Analysis Results:\n")
                    f.write(f"  Scene: {getattr(analysis_result, 'scene_type', 'unknown')}\n")
                    f.write(f"  Summary: {getattr(analysis_result, 'summary', 'N/A')}\n")
                    f.write(f"  People found: {analysis_result.total_people_count}\n")
                    f.write(f"  Objects found: {getattr(analysis_result, 'total_objects_count', 0)}\n\n")
                    
                    if hasattr(analysis_result, 'unique_people'):
                        f.write("People detected:\n")
                        for person in analysis_result.unique_people:
                            f.write(f"  • {person.person_id}: {person.description}\n")
                            f.write(f"    Frames: {person.frames_visible_in}\n")
                            f.write(f"    Direction: {person.primary_direction}\n")
                            if hasattr(person, 'bounding_boxes') and person.bounding_boxes:
                                f.write(f"    Bounding boxes: {len(person.bounding_boxes)}\n")
                            f.write("\n")
        except Exception as e:
            self.log.error(f"Failed to save panorama summary: {e}")
        
        self.run_metadata['images_processed'] = self.image_counter
        self._save_run_metadata()
        
        self.log.success(f"📸 Logged 360° panorama #{self.image_counter} ({len([p for p in frame_paths if p])} frames) → {panorama_dir.name}")
        
        return str(panorama_dir)
    
    def _save_run_metadata(self):
        """Save metadata for the current run."""
        metadata_path = self.run_dir / 'run_metadata.json'
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.run_metadata, f, indent=2)
        except Exception as e:
            self.log.error(f"Failed to save run metadata: {e}")
    
    def finalize_run(self):
        """Finalize the current run and save final metadata."""
        self.run_metadata['end_time'] = datetime.now().isoformat()
        self._save_run_metadata()
        
        self.log.info(f"✅ Vision logging run finalized: {self.image_counter} images processed")
        
        # Create summary file
        summary_path = self.run_dir / 'RUN_SUMMARY.txt'
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"Grok-Pilot Vision Analysis Run Summary\n")
                f.write(f"{'=' * 60}\n\n")
                f.write(f"Run ID: {self.run_metadata['run_id']}\n")
                f.write(f"Start Time: {self.run_metadata['start_time']}\n")
                f.write(f"End Time: {self.run_metadata.get('end_time', 'N/A')}\n")
                f.write(f"Total Images Processed: {self.run_metadata['images_processed']}\n\n")
                f.write(f"Log Directory: {self.run_dir}\n")
                f.write(f"\nContents:\n")
                f.write(f"  - {self.image_counter} image directories (image_0001, image_0002, ...)\n")
                f.write(f"  - Each contains: input_image.jpg, analysis_output.json, summary.txt\n")
        except Exception as e:
            self.log.error(f"Failed to create run summary: {e}")
    
    def get_run_dir(self) -> str:
        """Get the current run directory path."""
        return str(self.run_dir)
    
    def get_image_count(self) -> int:
        """Get the number of images logged in this run."""
        return self.image_counter
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - finalize the run."""
        self.finalize_run()
        return False


# Global image logger instance
_image_logger: Optional[ImageLogger] = None


def get_image_logger(base_log_dir: Optional[str] = None) -> ImageLogger:
    """
    Get or create the global image logger instance.
    
    Args:
        base_log_dir: Base directory for logs (only used on first call)
        
    Returns:
        ImageLogger instance
    """
    global _image_logger
    if _image_logger is None:
        _image_logger = ImageLogger(base_log_dir)
    return _image_logger


def reset_image_logger():
    """
    Reset the global image logger instance.
    Useful for starting a new run.
    """
    global _image_logger
    if _image_logger is not None:
        _image_logger.finalize_run()
    _image_logger = None
