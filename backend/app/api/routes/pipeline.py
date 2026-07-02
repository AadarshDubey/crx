"""
Pipeline progress SSE stream and status endpoints.

Provides real-time pipeline progress updates to the frontend
via Server-Sent Events (SSE).
"""

import asyncio
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services.pipeline_progress import pipeline_progress

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def get_pipeline_status():
    """Get current pipeline status snapshot."""
    return pipeline_progress.get_state()


@router.get("/stream")
async def stream_pipeline_progress(request: Request):
    """
    SSE endpoint that streams pipeline progress events.
    
    The frontend connects to this via EventSource and receives
    real-time updates as the pipeline progresses through steps.
    """
    
    async def event_generator():
        queue = await pipeline_progress.subscribe()
        
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                try:
                    # Wait for next event with timeout
                    state = await asyncio.wait_for(queue.get(), timeout=30.0)
                    data = json.dumps(state)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await pipeline_progress.unsubscribe(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",
        },
    )
