from fastapi import FastAPI, HTTPException
import httpx
from models.current_usage import CurrentUsage
from models.job_deployed import JobDeployed
from models.resources import Resources
from models.specs import Specs
from models.workers_running_service import WorkersRunningService
from typing import Dict, Optional, List
import uvicorn
from storage_classes.etcd_implementation import EtcdClient
import json
import argparse

app = FastAPI(title="Container Management API")
etcd_client = None

def connect_to_etcd():
    """Connect to etcd server"""
    global etcd_client
    if not etcd_client:
        etcd_client = EtcdClient()
        etcd_client.connect(host="127.0.0.1", port=2379)
    return etcd_client

@app.post("/api/tasks/deploy")
async def deploy_task(job: JobDeployed):
    """Deploy a new task to a worker node"""
    try:
        # Ensure we're connected to etcd
        if not etcd_client:
            connect_to_etcd()
            
        # Run scheduler to determine which workers to deploy to
        worker_names = run_scheduler(job)

        for instance, worker_name in enumerate(worker_names):
            key = job.job_id + "-" + worker_name + "-" + str(instance)
            # Store task information in etcd
            etcd_path = f"/workers/{worker_name}/deploy-req/{key}"
            etcd_client.put(etcd_path, json.dumps(job))
            
            # Also store in system services
            etcd_client.put(f"/system_services/{job.job_id}", json.dumps(worker_names))

        return {"status": "success", "message": f"Task {job.job_id} deployment initiated on {worker_names}"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/start/{task_name}")
async def start_task(task_name: str):
    """Start a deployed task"""
    try:
        # Ensure we're connected to etcd
        if not etcd_client:
            connect_to_etcd()

        # Get task keys
        task_keys = get_task_keys(task_name)

        if not task_keys:
            raise HTTPException(status_code=404, detail=f"Task {task_name} not found on any worker")

        # Fetch worker IPs
        worker_ips = get_worker_ips()

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
                etcd_path = f"/workers/{worker_name}/start_req/{task_name}"

            except httpx.HTTPStatusError as e:
                print(f"Error sending start request to {worker_name} for task {task_name}: {e}")
            except Exception as e:
                print(f"Error processing task {task_name} for worker {worker_name}: {e}")

        return {"status": "success", "message": f"Task {task_name} start initiated on {success_count}/{len(task_keys)} workers"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/stop/{task_name}")
async def stop_task(task_name: str):
    """Stop a running task"""
    try:
        # Ensure we're connected to etcd
        if not etcd_client:
            connect_to_etcd()
            
        # Get workers running this task
        task_keys = get_task_keys(task_name)
        
        if not task_keys:
            raise HTTPException(status_code=404, detail=f"Task {task_name} not found on any worker")
    
         # Fetch worker IPs (assuming you have a worker_ips dictionary)
        worker_ips = get_worker_ips()  # Implement this function to fetch worker IPs

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
                etcd_path = f"/workers/{worker_name}/stop_req/{task_name}"

            except httpx.HTTPStatusError as e:
                print(f"Error sending stop request to {worker_name} for task {task_name}: {e}")
            except Exception as e:
                print(f"Error processing task {task_name} for worker {worker_name}: {e}")

        return {"status": "success", "message": f"Task {task_name} stop initiated on {success_count}/{len(task_keys)} workers"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_worker_ips() -> Dict[str, str]:
    """
    Helper function to fetch worker IPs from etcd.
    Replace this with your actual implementation.
    """
    worker_ips = {}
    values = etcd_client.get_prefix("/workers")
    for value, metadata in values:
        worker_name = metadata.key.decode().split('/')[2]
        worker_ip = value.decode()  # Assuming the value stored is the IP address
        worker_ips[worker_name] = worker_ip
    return worker_ips

@app.get("/api/workers/{worker_name}/tasks")
async def list_worker_tasks(worker_name: str):
    """List all tasks for a worker"""
    try:
        # Ensure we're connected to etcd
        if not etcd_client:
            connect_to_etcd()
            
        tasks = etcd_client.get_prefix(f"/workers/{worker_name}/tasks")
        task_list = {}
        
        for value, key in tasks:
            task_name = key.split('/')[-1]
            if value:
                task_list[task_name] = json.loads(value)
                
        return task_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/{task_name}/workers")
async def get_task_workers(task_name: str):
    """Get all workers running a specific task"""
    try:
        # Ensure we're connected to etcd
        if not etcd_client:
            connect_to_etcd()
            
        workers = get_workers_running_task(task_name)
        
        if not workers:
            raise HTTPException(status_code=404, detail=f"Task {task_name} not found on any worker")
            
        return WorkersRunningService(worker_list=workers).to_json_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workers")
async def list_workers():
    """List all registered workers"""
    try:
        # Ensure we're connected to etcd
        if not etcd_client:
            connect_to_etcd()
            
        values = etcd_client.get_prefix("/workers")
        worker_names = list(set([val[1].split('/')[2] for val in values]))
        
        return {"workers": worker_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_task_keys(task_name: str) -> List[str]:
    """Helper function to get all workers running a specific task"""
    # Check system services first
    workers = etcd_client.get(f"/system_services/{task_name}")
    if not workers:
        return []
        
    return workers

def run_scheduler(JobDeployed:JobDeployed) -> List[str]:
    """Run the scheduler to determine which workers to deploy to"""
    values = etcd_client.get_prefix("/workers")
    worker_names = [metadata.key.decode().split('/')[2] for _, metadata in values]

    workers = {}
    for worker in worker_names:
        total_specs_val = etcd_client.get(f"/workers/{worker}/specs")[0].decode()
        current_usage_val = etcd_client.get(f"/workers/{worker}/current_usage")
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
        current_usage = CurrentUsage.from_dict(usage_dict)

        available_resources = Resources.from_two_specs(total_specs, current_usage)
        workers[worker] = available_resources
    return worker_names

if __name__ == "__main__":
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description='API Service for Kubernetes-like system')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind the server to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind the server to')
    
    args = parser.parse_args()
    
    # Connect to etcd at startup
    connect_to_etcd()
    
    # Start the server
    uvicorn.run(app, host=args.host, port=args.port)