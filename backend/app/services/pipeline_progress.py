"""
Pipeline Progress Tracker

Singleton that tracks the current state of the data sync pipeline
and broadcasts updates to connected SSE clients in real-time.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class PipelineProgress:
    """
    Tracks pipeline progress and broadcasts to SSE clients.
    
    The pipeline has 6 steps:
      1. Initializing Data Sync
      2. Scraping Tweets
      3. Processing Tweet Sentiment
      4. Scraping News Feeds
      5. Processing News Sentiment
      6. Finalizing Sync
    """
    
    TOTAL_STEPS = 6
    
    STEP_LABELS = {
        1: "Initializing Data Sync",
        2: "Scraping Tweets",
        3: "Processing Tweet Sentiment",
        4: "Scraping News Feeds",
        5: "Processing News Sentiment",
        6: "Finalizing Sync",
    }
    
    def __init__(self):
        self._clients: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()
        
        # Current state
        self.status: str = "idle"  # "idle", "running", "completed", "error"
        self.step: int = 0
        self.total_steps: int = self.TOTAL_STEPS
        self.label: str = ""
        self.detail: str = ""
        self.percentage: int = 0
        self.last_completed_at: Optional[str] = None
        self.stats: dict = {}  # summary stats from last run
    
    def get_state(self) -> dict:
        """Get current pipeline state as a dict."""
        return {
            "status": self.status,
            "step": self.step,
            "total_steps": self.total_steps,
            "label": self.label,
            "detail": self.detail,
            "percentage": self.percentage,
            "last_completed_at": self.last_completed_at,
            "stats": self.stats,
        }
    
    async def subscribe(self) -> asyncio.Queue:
        """Subscribe a new SSE client. Returns a queue to read events from."""
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._clients.append(queue)
        logger.info(f"SSE client subscribed. Total clients: {len(self._clients)}")
        # Send current state immediately
        await queue.put(self.get_state())
        return queue
    
    async def unsubscribe(self, queue: asyncio.Queue):
        """Remove an SSE client."""
        async with self._lock:
            if queue in self._clients:
                self._clients.remove(queue)
        logger.info(f"SSE client unsubscribed. Total clients: {len(self._clients)}")
    
    async def _broadcast(self):
        """Broadcast current state to all connected clients."""
        state = self.get_state()
        dead_clients = []
        
        async with self._lock:
            for queue in self._clients:
                try:
                    # Non-blocking put — drop if client is backed up
                    queue.put_nowait(state)
                except asyncio.QueueFull:
                    dead_clients.append(queue)
            
            for client in dead_clients:
                self._clients.remove(client)
    
    async def start_pipeline(self):
        """Mark pipeline as started."""
        self.status = "running"
        self.step = 1
        self.label = self.STEP_LABELS[1]
        self.detail = "Connecting to data sources..."
        self.percentage = 0
        self.stats = {}
        logger.info("[Pipeline] ▶ Started")
        await self._broadcast()
    
    async def update_step(self, step: int, detail: str = "", sub_progress: float = 0.0):
        """
        Update to a specific step with optional detail and sub-progress.
        
        Args:
            step: Step number (1-6)
            detail: Descriptive detail (e.g., "@saylor (3/12 accounts)")
            sub_progress: Progress within this step (0.0 to 1.0)
        """
        self.step = step
        self.label = self.STEP_LABELS.get(step, f"Step {step}")
        self.detail = detail
        
        # Calculate overall percentage
        # Each step is ~16.67%, sub_progress fills within the step
        step_weight = 100.0 / self.total_steps
        base = (step - 1) * step_weight
        self.percentage = min(int(base + sub_progress * step_weight), 100)
        
        logger.info(f"[Pipeline] Step {step}/{self.total_steps} — {self.label}: {detail} ({self.percentage}%)")
        await self._broadcast()
    
    async def complete_pipeline(self, stats: dict = None):
        """Mark pipeline as completed."""
        self.status = "completed"
        self.step = self.total_steps
        self.label = "Sync Complete"
        self.detail = self._format_stats(stats) if stats else "All data synced successfully"
        self.percentage = 100
        self.last_completed_at = datetime.utcnow().isoformat()
        self.stats = stats or {}
        logger.info(f"[Pipeline] ✓ Completed — {self.detail}")
        await self._broadcast()
        
        # After a delay, transition to idle
        await asyncio.sleep(8)
        self.status = "idle"
        self.label = ""
        self.detail = ""
        self.step = 0
        self.percentage = 0
        await self._broadcast()
    
    async def error_pipeline(self, error_msg: str):
        """Mark pipeline as errored."""
        self.status = "error"
        self.detail = error_msg
        logger.error(f"[Pipeline] ✗ Error — {error_msg}")
        await self._broadcast()
        
        # After a delay, transition to idle
        await asyncio.sleep(10)
        self.status = "idle"
        self.label = ""
        self.detail = ""
        self.step = 0
        self.percentage = 0
        await self._broadcast()
    
    def _format_stats(self, stats: dict) -> str:
        """Format stats dict into a readable summary."""
        parts = []
        if stats.get("tweets_saved", 0) > 0:
            parts.append(f"{stats['tweets_saved']} new tweets")
        if stats.get("articles_saved", 0) > 0:
            parts.append(f"{stats['articles_saved']} new articles")
        if stats.get("sentiment_processed", 0) > 0:
            parts.append(f"{stats['sentiment_processed']} analyzed")
        
        if not parts:
            return "All data up to date"
        return "Saved " + ", ".join(parts)


# Singleton instance
pipeline_progress = PipelineProgress()
