from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime, timedelta
import threading
import time
import uvicorn

app = FastAPI()

# Timeout after which a worker is considered dead (in seconds)
HEARTBEAT_TIMEOUT = 30

# In-memory registry to store heartbeat information
# Structure: {worker_id: {"timestamp": datetime, "cpu_usage": float, "ram_usage": float, "disk_usage": float, "additional_info": dict, "status": "alive" or "dead"}}
heartbeats: Dict[str, Dict[str, Any]] = {}

# Pydantic model for heartbeat data sent by worker nodes
class HeartbeatData(BaseModel):
    worker_id: str
    cpu_usage: float
    ram_usage: float
    disk_usage: float
    additional_info: Dict[str, Any] = {}

@app.post("/heartbeat")
def receive_heartbeat(update: HeartbeatData):
    """Receive a heartbeat update from a worker node."""
    now = datetime.utcnow()
    heartbeats[update.worker_id] = {
        "timestamp": now,
        "cpu_usage": update.cpu_usage,
        "ram_usage": update.ram_usage,
        "disk_usage": update.disk_usage,
        "additional_info": update.additional_info,
        "status": "alive"
    }
    return {"message": f"Heartbeat received from {update.worker_id} at {now.isoformat()}"}

def evaluate_heartbeats():
    """Cycle through stored heartbeats and mark workers as dead if the last heartbeat is too old."""
    now = datetime.utcnow()
    for worker_id, info in heartbeats.items():
        last_time = info.get("timestamp")
        if last_time and (now - last_time).total_seconds() > HEARTBEAT_TIMEOUT:
            info["status"] = "dead"
        else:
            info["status"] = "alive"

@app.get("/workers/alive")
def get_alive_workers():
    """Return a list of workers currently marked as alive."""
    evaluate_heartbeats()
    alive_workers = {wid: info for wid, info in heartbeats.items() if info["status"] == "alive"}
    return {"alive_workers": alive_workers}

@app.get("/workers/dead")
def get_dead_workers():
    """Return a list of workers currently marked as dead."""
    evaluate_heartbeats()
    dead_workers = {wid: info for wid, info in heartbeats.items() if info["status"] == "dead"}
    return {"dead_workers": dead_workers}

@app.post("/workers/mark-dead")
def mark_worker_dead(worker_id: str):
    """Manually mark a worker as dead."""
    if worker_id in heartbeats:
        heartbeats[worker_id]["status"] = "dead"
        return {"message": f"Worker {worker_id} manually marked as dead"}
    else:
        raise HTTPException(status_code=404, detail="Worker not found")

def heartbeat_monitor_loop():
    """Background loop that periodically evaluates heartbeats."""
    while True:
        evaluate_heartbeats()
        time.sleep(HEARTBEAT_TIMEOUT / 2)  # Adjust the frequency as needed

# Start the heartbeat monitor in a background thread
threading.Thread(target=heartbeat_monitor_loop, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)