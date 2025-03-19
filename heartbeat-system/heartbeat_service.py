import argparse
from fastapi import FastAPI
from storage_wrapper import StorageFactory
from heartbeat_system import HeartbeatManager

app = FastAPI()
storage = None  # Storage instance (etcd or test)
heartbeat_manager = None  # Heartbeat manager instance

def connect_to_storage(storage_type: str):
    """Initialize the storage backend."""
    global storage, heartbeat_manager
    storage = StorageFactory.create(storage_type)
    heartbeat_manager = HeartbeatManager(storage)

@app.post("/heartbeat")
def send_heartbeat(worker_id: str):
    """Endpoint for workers to send heartbeats."""
    if heartbeat_manager is None:
        return {"error": "Storage not initialized"}

    heartbeat_manager.update_heartbeat(worker_id)
    return {"message": f"Heartbeat received from {worker_id}"}

@app.get("/workers/alive")
def get_alive_workers():
    """Get a list of active (alive) workers."""
    if heartbeat_manager is None:
        return {"error": "Storage not initialized"}

    return {"alive_workers": heartbeat_manager.get_alive_workers()}

@app.get("/workers/dead")
def get_dead_workers():
    """Get a list of dead workers."""
    if heartbeat_manager is None:
        return {"error": "Storage not initialized"}

    return {"dead_workers": heartbeat_manager.get_dead_workers()}

@app.post("/workers/mark-dead")
def mark_worker_dead(worker_id: str):
    """Manually mark a worker as dead."""
    if heartbeat_manager is None:
        return {"error": "Storage not initialized"}

    heartbeat_manager.mark_worker_dead(worker_id)
    return {"message": f"Worker {worker_id} marked as dead"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the Heartbeat Service")
    parser.add_argument("--storage", type=str, choices=["etcd", "test"], required=True, help="Storage backend to use")

    args = parser.parse_args()
    connect_to_storage(args.storage)

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)