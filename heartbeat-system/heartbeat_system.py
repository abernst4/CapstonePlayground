import time
import threading
from typing import Dict, List
from storage_wrapper import StorageService  # Import the StorageService class from storage-service-wrapper.py


class HeartbeatManager:
    """Manages worker heartbeats and marks nodes as dead after timeout."""

    def __init__(self, storage: StorageService, timeout: int = 30, cleanup_interval: int = 10):
        """
        :param storage: Instance of StorageService (EtcdStorage or TestStorage)
        :param timeout: Time in seconds before marking a worker as dead
        :param cleanup_interval: Interval in seconds for cleanup of dead workers
        """
        self.storage = storage
        self.timeout = timeout

        # Start background thread to clean up dead workers
        self.cleanup_thread = threading.Thread(target=self._cleanup_dead_workers, daemon=True)
        self.cleanup_thread.start()

    def update_heartbeat(self, worker_id: str):
        """Worker sends a heartbeat to indicate it is alive."""
        timestamp = time.time()
        self.storage.put(f"/workers/{worker_id}/heartbeat", timestamp)
        self.storage.put(f"/workers/{worker_id}/status", "alive")

    def get_alive_workers(self) -> List[str]:
        """Retrieve a list of workers that are alive."""
        all_workers = self.storage.get_prefix("/workers")
        alive_workers = [
            worker.split("/")[-1]
            for worker, status in all_workers.items()
            if "/status" in worker and status == "alive"
        ]
        return alive_workers

    def get_dead_workers(self) -> List[str]:
        """Retrieve a list of workers that have timed out."""
        all_workers = self.storage.get_prefix("/workers")
        current_time = time.time()
        dead_workers = [
            worker.split("/")[-1]
            for worker, timestamp in all_workers.items()
            if "/heartbeat" in worker and (current_time - float(timestamp)) >= self.timeout
        ]
        return dead_workers

    def mark_worker_dead(self, worker_id: str):
        """Mark a worker as dead and update its status in storage."""
        self.storage.put(f"/workers/{worker_id}/status", "dead")

    def _cleanup_dead_workers(self):
        """Background task to remove dead workers if they exceed timeout."""
        while True:
            time.sleep(self.timeout)
            dead_workers = self.get_dead_workers()
            for worker in dead_workers:
                self.mark_worker_dead(worker)