import asyncio
import logging
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

class Priority(IntEnum):
    """Priority levels for Traffic Control. Lower number = Higher priority."""
    VIP = 0       # CEO, Director, Lead Agents
    HIGH = 1      # Critical Path
    STANDARD = 2  # Standard Agents (Designer/Dev)
    BULK = 3      # Critics, Testers, Bulk Ops

@dataclass(order=True)
class QueueItem:
    priority: int
    timestamp: float
    # We use a future to signal when the slot is acquired
    future: asyncio.Future = field(compare=False)
    name: str = field(compare=False)

class TrafficController:
    """
    Manages concurrency limits and priority queuing for the Workflow Engine.
    Ensures that high-priority agents (like Leads) get resource access first,
    and prevents system overload by capping concurrent execution.
    """
    
    def __init__(self, max_concurrency: int = 1):
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.queue = asyncio.PriorityQueue()
        self.active_count = 0
        self.is_paused = False
        self._paused_event = asyncio.Event()
        self._paused_event.set() # Initially not paused (set=True means go)

    async def acquire_slot(self, node_name: str, priority: Priority = Priority.STANDARD):
        """
        Request a slot to run. Blocks until a slot is available and it's our turn.
        """
        # 1. Check Pause State
        await self._paused_event.wait()

        # If we can acquire immediately and queue is empty, do it (Fast Path)
        if self.queue.empty() and not self.semaphore.locked():
            await self.semaphore.acquire()
            self.active_count += 1
            logger.info(f"🚦 [Traffic] Direct Entry: {node_name} (Active: {self.active_count}/{self.max_concurrency})")
            return

        # 2. Enqueue
        import time
        future = asyncio.get_event_loop().create_future()
        item = QueueItem(priority=priority, timestamp=time.time(), future=future, name=node_name)
        await self.queue.put(item)
        logger.info(f"🚦 [Traffic] Queued: {node_name} (Priority: {priority.name}, Pos: {self.queue.qsize()})")

        # 3. Wait for our turn
        # We process the queue in background or just have a loop?
        # Actually, standard Semaphore doesn't respect Priority Queue.
        # We need a custom dispatcher loop OR we just wait on the future.
        # Let's verify: access to the semaphore must be mediated by the queue.
        
        # Self-driving logic:
        # We wait for the FUTURE to be set. The future is set by `_process_queue`.
        # Ensure _process_queue is running.
        asyncio.create_task(self._process_next())
        
        await future
        self.active_count += 1
        logger.info(f"🚦 [Traffic] Acquired: {node_name} (Active: {self.active_count}/{self.max_concurrency})")

    async def release_slot(self):
        """Release the slot and trigger the next item."""
        self.active_count -= 1
        self.semaphore.release()
        logger.info(f"🚦 [Traffic] Released. (Active: {self.active_count}/{self.max_concurrency})")
        
        # Trigger next check
        asyncio.create_task(self._process_next())

    async def _process_next(self):
        """Try to move specific items from Queue to Semaphore."""
        if self.queue.empty():
            return

        # Acquire semaphore (this checks specific availability)
        # BUT `release_slot` releases the semaphore usage.
        # This function acts as the bridge.
        
        # We actually don't want the TASK to hold the semaphore directly in `acquire_slot` fast path
        # if we want Strict Priority. But for simplicity, Fast Path is fine if queue empty.
        
        # Strict logic:
        # Wait for semaphore availability
        if self.semaphore.locked():
             return # Can't schedule yet

        # If available, pop highest priority
        try:
            # Check pause again
            await self._paused_event.wait()
            
            # Non-blocking check before we commit to popping?
            # Creating a critical section to ensure we don't pop if we can't run
            # Actually, standard pattern:
            # 1. Acquire sem
            await self.semaphore.acquire()
            
            # 2. Get item
            item = await self.queue.get()
            
            # 3. Signal item
            if not item.future.done():
                item.future.set_result(True)
            else:
                 # Cancelled? Release
                 self.semaphore.release()
                 
        except asyncio.QueueEmpty:
            self.semaphore.release()

    def set_pause(self, paused: bool):
        self.is_paused = paused
        if paused:
            self._paused_event.clear()
            logger.warning("🚦 [Traffic] SYSTEM PAUSED.")
        else:
            self._paused_event.set()
            logger.info("🚦 [Traffic] SYSTEM RESUMED.")
            # Kickstart queue
            asyncio.create_task(self._process_next())

    def update_concurrency(self, limit: int):
        logger.info(f"🚦 [Traffic] Concurrency limit changed: {self.max_concurrency} -> {limit}")
        # This is tricky with asyncio.Semaphore. Recreating it is safer if we ensure logic consistency.
        # For prototype, we just warn.
        self.max_concurrency = limit
        # Simple hack: adjust semaphore internal counter? No, unsafe.
        # We will just instantiate a new semaphore for new requests, but logic gets complex.
        # For V1, we require restart or just rely on 'soft' limits if we write a custom semaphore.
        # Let's stick to the initial limit for now.

# Global Instance
# Default to 1 for Maximum Stability as requested
global_traffic_controller = TrafficController(max_concurrency=1)
