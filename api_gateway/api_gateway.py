from fastapi import FastAPI, HTTPException, Depends
import httpx
from api_gateway.models.resource_usage import ResourceUsage
from models.specs import Specs
from models.resources import Resources
from models.service import Service
from storage_interface.storage_service_wrapper import EtcdStorage, StorageService
from typing import Dict, Optional, List
import uvicorn
import json
import argparse

app = FastAPI(title="Container Management API")
storage_client = None

def get_storage_client() -> StorageService:
    """Get or initialize storage client"""
    global storage_client
    if storage_client is None:
        # EtcdStorage constructor already handles connection
        storage_client = EtcdStorage(host="127.0.0.1", port=2379)
    return storage_client

@app.post("/api/tasks/deploy")
async def deploy_task(service: Service, storage: StorageService = Depends(get_storage_client)):
    """Deploy a new task to a worker node"""
    try:
        # Run scheduler to determine which workers to deploy to
        worker_names = run_scheduler(service, storage)

        for instance, worker_name in enumerate(worker_names):
            key = service.job_id + "-" + worker_name + "-" + str(instance)
            # Store task information in etcd
            storage.put(f"/workers/{worker_name}/deploy-req/{key}", service)
            
            # Also store in system services
            storage.put(f"/system_services/{service.job_id}", json.dumps(worker_names))

        return {"status": "success", "message": f"Task {service.job_id} deployment initiated on {worker_names}"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/start/{task_name}")
async def start_task(task_name: str, storage: StorageService = Depends(get_storage_client)):
    """Start a deployed task"""
    try:
        # Get task keys
        task_keys = get_task_keys(task_name, storage)

        if not task_keys:
            raise HTTPException(status_code=404, detail=f"Task {task_name} not found on any worker")

        # Fetch worker IPs
        worker_ips = get_worker_ips(storage)

        # Send start command to all workers running this task
        success_count = 0
        for task_key in task_keys:
            try:
                worker_name = task_key.split('-')[1]  # Extract worker name from the key
                if worker_name not in worker_ips:
                    print(f"Warning: No IP found for worker {worker_name}")
                    continue

                worker_ip = worker_ips[worker_name]
                url = f"http://{worker_ip}:8000/api/tasks/start/{task_name}"  # Adjust port if needed

                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json={"task_key": task_key})  # Send task_key in the request body
                    response.raise_for_status()

                success_count += 1
                print(f"Start request sent successfully to {worker_name} for task {task_name}")

                # Changes status in etcd to start_req
                storage.put(f"/workers/{worker_name}/start_req/{task_name}", task_key)

            except httpx.HTTPStatusError as e:
                print(f"Error sending start request to {worker_name} for task {task_name}: {e}")
            except Exception as e:
                print(f"Error processing task {task_name} for worker {worker_name}: {e}")

        return {"status": "success", "message": f"Task {task_name} start initiated on {success_count}/{len(task_keys)} workers"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/stop/{task_name}")
async def stop_task(task_name: str, storage: StorageService = Depends(get_storage_client)):
    """Stop a running task"""
    try:
        # Get workers running this task
        task_keys = get_task_keys(task_name, storage)
        
        if not task_keys:
            raise HTTPException(status_code=404, detail=f"Task {task_name} not found on any worker")
    
         # Fetch worker IPs (assuming you have a worker_ips dictionary)
        worker_ips = get_worker_ips(storage)  # Implement this function to fetch worker IPs

        # Send stop command to all workers running this task
        success_count = 0
        for task_key in task_keys:
            try:
                worker_name = task_key.split('-')[1]  # Extract worker name from the key
                if worker_name not in worker_ips:
                    print(f"Warning: No IP found for worker {worker_name}")
                    continue

                worker_ip = worker_ips[worker_name]
                url = f"http://{worker_ip}:8000/api/tasks/stop/{task_name}"  # Adjust port if needed

                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json={"task_key": task_key})  # Send task_key in the request body
                    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

                success_count += 1
                print(f"Stop request sent successfully to {worker_name} for task {task_name}")

                # Changes status in etcd to stop_req
                storage.put(f"/workers/{worker_name}/stop_req/{task_name}", task_key)

            except httpx.HTTPStatusError as e:
                print(f"Error sending stop request to {worker_name} for task {task_name}: {e}")
            except Exception as e:
                print(f"Error processing task {task_name} for worker {worker_name}: {e}")

        return {"status": "success", "message": f"Task {task_name} stop initiated on {success_count}/{len(task_keys)} workers"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#Helper functions
def get_worker_ips(storage: StorageService) -> Dict[str, str]:
    """Helper function to fetch worker IPs from etcd."""
    worker_ips = {}
    try:
        values = storage.get_prefix("/workers")
        for key, value in values.items():
            parts = key.split('/')
            if len(parts) >= 3:
                worker_name = parts[2]
                worker_ips[worker_name] = value
    except Exception as e:
        print(f"Error fetching worker IPs: {e}")
    return worker_ips

def get_task_keys(task_name: str, storage: StorageService) -> List[str]:
    """Helper function to get all workers running a specific task"""
    try:
        workers_data = storage.get(f"/system_services/{task_name}")
        if not workers_data:
            return []
        return workers_data
    except json.JSONDecodeError:
        print(f"Error decoding JSON for task {task_name}")
        return []
    except Exception as e:
        print(f"Error getting task keys: {e}")
        return []

def run_scheduler(service: Service, storage: StorageService) -> List[str]:
    """Run the scheduler to determine which workers to deploy to"""
    values = storage.get_prefix("/workers")
    worker_names = [metadata.key.decode().split('/')[2] for _, metadata in values]

    workers = {}
    for worker in worker_names:
        total_specs_val = storage.get(f"/workers/{worker}/specs")[0].decode()
        current_usage_val = storage.get(f"/workers/{worker}/current_usage")
        total_specs = Specs.from_dict(json.loads(total_specs_val))
        if not current_usage_val or not current_usage_val[0]:
            usage_dict = {
                "current_usage": {
                    "cpu": 0, 
                    "ram": 0, 
                    "disk": 0
                }
            }
        else:
            usage_dict = json.loads(current_usage_val[0].decode())
        current_usage = ResourceUsage.from_dict(usage_dict)

        available_resources = Resources.from_two_specs(total_specs, current_usage)
        workers[worker] = available_resources
    return worker_names

if __name__ == "__main__":
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description='API Service for Kubernetes-like system')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind the server to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind the server to')
    parser.add_argument('--etcd-host', type=str, default='127.0.0.1', help='Etcd host')
    parser.add_argument('--etcd-port', type=int, default=2379, help='Etcd port')
    
    args = parser.parse_args()
    
    # Start the server
    uvicorn.run(app, host=args.host, port=args.port)