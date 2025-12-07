"""
Async Inference Engine - Non-blocking Grok vision inference.
Runs inference in thread pool so drone doesn't wait for AI.
"""

import threading
import time
import numpy as np
from typing import Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from datetime import datetime

from core.logger import get_logger

log = get_logger('inference_engine')


@dataclass
class InferenceTask:
    """A queued inference task."""
    task_id: str
    frame: np.ndarray
    inference_type: str  # "scene", "quick", "person_detail", "search"
    target: Optional[str] = None  # For search tasks
    callback: Optional[Callable] = None
    submitted_at: datetime = None
    
    def __post_init__(self):
        if self.submitted_at is None:
            self.submitted_at = datetime.now()


@dataclass 
class InferenceResult:
    """Result of an inference task."""
    task_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    duration_ms: float = 0
    completed_at: datetime = None
    
    def __post_init__(self):
        if self.completed_at is None:
            self.completed_at = datetime.now()


class AsyncInferenceEngine:
    """
    Non-blocking inference engine with result caching.
    
    Features:
    - Submit inference tasks that run in background
    - Check if results are ready without blocking
    - Optional callbacks when inference completes
    - Result caching for quick lookups
    """
    
    def __init__(self, grok_client, max_workers: int = 3):
        """
        Initialize the inference engine.
        
        Args:
            grok_client: GrokClient instance for making API calls
            max_workers: Max concurrent inference tasks
        """
        self.grok = grok_client
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Task tracking
        self._pending: Dict[str, Future] = {}
        self._results: Dict[str, InferenceResult] = {}
        self._lock = threading.Lock()
        
        # Counters
        self._task_counter = 0
        
        log.info(f"AsyncInferenceEngine initialized with {max_workers} workers")
    
    def submit_scene_analysis(
        self,
        frame: np.ndarray,
        callback: Optional[Callable[[InferenceResult], None]] = None
    ) -> str:
        """
        Submit a full scene analysis task.
        
        Args:
            frame: Image frame to analyze
            callback: Optional callback when complete
            
        Returns:
            Task ID for checking results
        """
        return self._submit_task(
            frame=frame,
            inference_type="scene",
            callback=callback
        )
    
    def submit_quick_check(
        self,
        frame: np.ndarray,
        callback: Optional[Callable[[InferenceResult], None]] = None
    ) -> str:
        """
        Submit a quick obstacle/safety check.
        
        Args:
            frame: Image frame to analyze
            callback: Optional callback when complete
            
        Returns:
            Task ID
        """
        return self._submit_task(
            frame=frame,
            inference_type="quick",
            callback=callback
        )
    
    def submit_person_analysis(
        self,
        frame: np.ndarray,
        callback: Optional[Callable[[InferenceResult], None]] = None
    ) -> str:
        """
        Submit detailed person analysis.
        
        Args:
            frame: Image frame to analyze
            callback: Optional callback when complete
            
        Returns:
            Task ID
        """
        return self._submit_task(
            frame=frame,
            inference_type="person_detail",
            callback=callback
        )
    
    def submit_search(
        self,
        frame: np.ndarray,
        target: str,
        callback: Optional[Callable[[InferenceResult], None]] = None
    ) -> str:
        """
        Submit a target search analysis.
        
        Args:
            frame: Image frame to search in
            target: Description of what to find
            callback: Optional callback when complete
            
        Returns:
            Task ID
        """
        return self._submit_task(
            frame=frame,
            inference_type="search",
            target=target,
            callback=callback
        )
    
    def _submit_task(
        self,
        frame: np.ndarray,
        inference_type: str,
        target: Optional[str] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """Submit a task to the executor."""
        with self._lock:
            self._task_counter += 1
            task_id = f"{inference_type}_{self._task_counter}_{int(time.time()*1000)}"
        
        task = InferenceTask(
            task_id=task_id,
            frame=frame.copy(),  # Copy to avoid mutation
            inference_type=inference_type,
            target=target,
            callback=callback
        )
        
        future = self.executor.submit(self._run_inference, task)
        
        with self._lock:
            self._pending[task_id] = future
        
        log.debug(f"Submitted inference task: {task_id}")
        return task_id
    
    def _run_inference(self, task: InferenceTask) -> InferenceResult:
        """Run the actual inference (in thread pool)."""
        start_time = time.time()
        
        try:
            result = None
            
            if task.inference_type == "scene":
                result = self.grok.analyze_scene_with_entities(task.frame)
            elif task.inference_type == "quick":
                result = self.grok.quick_obstacle_check(task.frame)
            elif task.inference_type == "person_detail":
                result = self.grok.analyze_people_detailed(task.frame)
            elif task.inference_type == "search":
                result = self.grok.search_for_target_structured(
                    task.frame, task.target
                )
            else:
                raise ValueError(f"Unknown inference type: {task.inference_type}")
            
            duration_ms = (time.time() - start_time) * 1000
            
            inference_result = InferenceResult(
                task_id=task.task_id,
                success=True,
                result=result,
                duration_ms=duration_ms
            )
            
            log.debug(f"Inference {task.task_id} completed in {duration_ms:.0f}ms")
            
        except Exception as e:
            log.error(f"Inference {task.task_id} failed: {e}")
            duration_ms = (time.time() - start_time) * 1000
            
            inference_result = InferenceResult(
                task_id=task.task_id,
                success=False,
                result=None,
                error=str(e),
                duration_ms=duration_ms
            )
        
        # Store result
        with self._lock:
            self._results[task.task_id] = inference_result
            if task.task_id in self._pending:
                del self._pending[task.task_id]
        
        # Call callback if provided
        if task.callback:
            try:
                task.callback(inference_result)
            except Exception as e:
                log.error(f"Callback error for {task.task_id}: {e}")
        
        return inference_result
    
    def get_result(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Optional[InferenceResult]:
        """
        Get result for a task.
        
        Args:
            task_id: Task ID from submit
            timeout: Max seconds to wait (None = don't wait)
            
        Returns:
            InferenceResult if ready, None if still pending or not found
        """
        # Check cache first
        with self._lock:
            if task_id in self._results:
                return self._results[task_id]
            
            future = self._pending.get(task_id)
        
        if not future:
            return None
        
        if timeout is None:
            # Non-blocking check
            if future.done():
                return future.result()
            return None
        
        # Wait with timeout
        try:
            return future.result(timeout=timeout)
        except Exception:
            return None
    
    def is_complete(self, task_id: str) -> bool:
        """Check if a task is complete."""
        with self._lock:
            if task_id in self._results:
                return True
            future = self._pending.get(task_id)
            if future:
                return future.done()
        return False
    
    def wait_for_result(
        self,
        task_id: str,
        timeout: float = 10.0
    ) -> Optional[InferenceResult]:
        """
        Wait for a result with timeout.
        
        Args:
            task_id: Task ID
            timeout: Max seconds to wait
            
        Returns:
            InferenceResult or None if timeout
        """
        return self.get_result(task_id, timeout=timeout)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Attempt to cancel a pending task.
        
        Args:
            task_id: Task to cancel
            
        Returns:
            True if cancelled, False if already complete or not found
        """
        with self._lock:
            future = self._pending.get(task_id)
            if future:
                cancelled = future.cancel()
                if cancelled:
                    del self._pending[task_id]
                return cancelled
        return False
    
    def clear_cache(self) -> int:
        """
        Clear result cache.
        
        Returns:
            Number of results cleared
        """
        with self._lock:
            count = len(self._results)
            self._results.clear()
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        with self._lock:
            return {
                "pending_tasks": len(self._pending),
                "cached_results": len(self._results),
                "total_submitted": self._task_counter
            }
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the engine.
        
        Args:
            wait: Whether to wait for pending tasks
        """
        log.info("Shutting down inference engine...")
        self.executor.shutdown(wait=wait)


# Singleton instance
_engine_instance: Optional[AsyncInferenceEngine] = None
_engine_lock = threading.Lock()


def get_inference_engine(grok_client=None) -> AsyncInferenceEngine:
    """
    Get singleton AsyncInferenceEngine instance.
    
    Args:
        grok_client: Required on first call to initialize
    """
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            if grok_client is None:
                raise ValueError("grok_client required for first initialization")
            _engine_instance = AsyncInferenceEngine(grok_client)
        return _engine_instance


def init_inference_engine(grok_client) -> AsyncInferenceEngine:
    """Initialize the inference engine with a Grok client."""
    global _engine_instance
    with _engine_lock:
        _engine_instance = AsyncInferenceEngine(grok_client)
        return _engine_instance
