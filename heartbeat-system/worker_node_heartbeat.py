import argparse
import time
import threading
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
import uvicorn

app = FastAPI()

# Global variable for the cluster manager URL (to which heartbeats are sent)
CLUSTER_MANAGER_URL = None

# Define a model for the heartbeat data (includes node metrics and any pod info)
class HeartbeatData(BaseModel):
    worker_id: str
    cpu_usage: float         # e.g., in percentage
    ram_usage: float         # e.g., in MB
    disk_usage: float        # e.g., in MB or GB
    additional_info: Dict[str, Any] = {}  # e.g., number of pods running, pod statuses, etc.

# (Optional) Endpoint to receive pod status updates on the worker node;
# these could update local state and later be incorporated in the heartbeat.
class PodStatusUpdate(BaseModel):
    job_id: str
    pod_id: str
    status: str  # "running", "completed", "failed", etc.
    logs: str
    additional_info: Dict[str, Any]

@app.post("/pod-status")
def receive_pod_status(update: PodStatusUpdate):
    print(f"Worker received pod update from {update.pod_id}: {update.status}")
    # Here you might update local metrics or state based on pod info.
    return {"message": "Pod status processed"}

def send_heartbeat(heartbeat_data: HeartbeatData):
    """Send a heartbeat to the cluster manager."""
    if not CLUSTER_MANAGER_URL:
        print("Cluster Manager URL not configured.")
        return
    try:
        response = requests.post(f"{CLUSTER_MANAGER_URL}/heartbeat", json=heartbeat_data.dict())
        print(f"Heartbeat sent from {heartbeat_data.worker_id}, response status: {response.status_code}")
    except Exception as e:
        print(f"Error sending heartbeat: {e}")

def aggregate_and_send_heartbeat(worker_id: str):
    """
    Gather node metrics (and any aggregated pod info) and send a heartbeat.
    In a production system, replace these simulated metrics with actual measurements.
    """
    # Simulated metrics
    cpu_usage = 42.0             # Replace with real CPU usage
    ram_usage = 2048.0           # Replace with real RAM usage in MB
    disk_usage = 50000.0         # Replace with real Disk usage (MB or GB)
    additional_info = {
        "pod_count": 3,
        "timestamp": time.time()
    }
    heartbeat = HeartbeatData(
        worker_id=worker_id,
        cpu_usage=cpu_usage,
        ram_usage=ram_usage,
        disk_usage=disk_usage,
        additional_info=additional_info
    )
    send_heartbeat(heartbeat)

@app.get("/trigger-heartbeat")
def trigger_heartbeat(worker_id: str):
    """Endpoint to manually trigger a heartbeat (for testing purposes)."""
    aggregate_and_send_heartbeat(worker_id)
    return {"message": f"Heartbeat triggered for {worker_id}"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the Worker Node Heartbeat Service")
    parser.add_argument("--cluster-manager-url", type=str, required=True, help="URL of the cluster manager heartbeat service")
    parser.add_argument("--worker-id", type=str, required=True, help="Unique worker node ID")
    args = parser.parse_args()
    
    CLUSTER_MANAGER_URL = args.cluster_manager_url
    worker_id = args.worker_id

    # Start a background thread to periodically send heartbeats (e.g., every 10 seconds)
    def heartbeat_loop():
        while True:
            aggregate_and_send_heartbeat(worker_id)
            time.sleep(10)
    
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    
    uvicorn.run(app, host="0.0.0.0", port=8003)