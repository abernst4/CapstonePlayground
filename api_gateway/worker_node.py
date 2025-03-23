import json
import os
import signal
import sys
import argparse
from enum import Enum
from typing import Dict, Any, Optional, List

# Fix imports
import sys
import os
# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import uvicorn
from storage_interface.storage_service_wrapper import EtcdStorage, StorageService

# Import existing models
from models.service import Service
from models.service_instance import ServiceInstance, Status
from models.resources import Resources
from models.specs import Specs
from models.resource_usage import ResourceUsage

class WorkerNode:
    def __init__(self, worker_name, storage_type="etcd", storage_host="127.0.0.1", storage_port=2379, **storage_kwargs):
        self.worker_name = worker_name
        self.services: Dict[str, ServiceInstance] = {}
        self.api_port = None
        # Connect to storage
        self.storage = EtcdStorage(host="127.0.0.1", port=2379)
        print(f"Worker node {worker_name} initialized and connected to storage")
        
        # Register with storage
        self.register_with_storage()

    def register_with_storage(self):
        """Register this worker with storage"""
        try:
            # Set default specs if not already set
            specs_path = f"/workers/{self.worker_name}/specs"
            specs_exists = self.storage.get(specs_path)
            
            if not specs_exists:
                default_specs = {
                    "specs": {
                        "cpu": 4,
                        "ram": 8,
                        "disk": 100
                    }
                }
                self.storage.put(specs_path, json.dumps(default_specs))
                print(f"Registered worker {self.worker_name} with default specs")
            else:
                print(f"Worker {self.worker_name} already registered")
                
            # Initialize current usage if not set
            usage_path = f"/workers/{self.worker_name}/current_usage"
            usage_exists = self.storage.get(usage_path)
            
            if not usage_exists:
                default_usage = {
                    "resource_usage": {
                        "cpu": 0,
                        "ram": 0,
                        "disk": 0
                    }
                }
                self.storage.put(usage_path, json.dumps(default_usage))
                print(f"Initialized current usage for worker {self.worker_name}")
                
            # Register worker's API endpoint in storage
            if self.api_port:
                endpoint_path = f"/workers/{self.worker_name}/endpoint"
                self.storage.put(endpoint_path, f"http://localhost:{self.api_port}")
                print(f"Registered worker endpoint in storage")
            
        except Exception as e:
            print(f"Error registering worker with storage: {e}")

    def deploy_service(self, service: Service, unique_id: str):
        """Deploy a new service"""
        print(f"Deploying service: {service.get_service_name} with ID {unique_id}")
        try:
            # Create a service instance
            service_instance = ServiceInstance(
                service_name=service.get_service_name,
                image_url=service.get_image_url,
                number_of_replicas=service.get_number_of_replicas,
                requested_resources=service.get_requested_resources,
                unique_id=unique_id,
                status=Status.DEPLOYED
            )
            
            # Store service instance
            self.services[unique_id] = service_instance
            
            # Update current usage in storage
            self._update_resource_usage()
            
            print(f"Successfully deployed service: {service.get_service_name} with ID {unique_id}")
            return {"status": "success", "message": f"Service {service.get_service_name} deployed successfully"}
        except Exception as e:
            error_msg = f"Error deploying service {service.get_service_name}: {e}"
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

    def start_service(self, unique_id: str):
        """Start a deployed service"""
        print(f"Starting service with ID: {unique_id}")
        if unique_id not in self.services:
            error_msg = f"Service with ID {unique_id} not deployed"
            print(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)
        
        try:
            # Update service status
            self.services[unique_id].status = Status.STARTED
            print(f"Successfully started service with ID: {unique_id}")
            return {"status": "success", "message": f"Service with ID {unique_id} started successfully"}
        except Exception as e:
            error_msg = f"Error starting service with ID {unique_id}: {e}"
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

    def stop_service(self, unique_id: str):
        """Stop a running service"""
        print(f"Stopping service with ID: {unique_id}")
        if unique_id not in self.services:
            error_msg = f"Service with ID {unique_id} not deployed"
            print(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)
        
        try:
            # Update service status
            self.services[unique_id].status = Status.STOPPED
            print(f"Successfully stopped service with ID: {unique_id}")
            return {"status": "success", "message": f"Service with ID {unique_id} stopped successfully"}
        except Exception as e:
            error_msg = f"Error stopping service with ID {unique_id}: {e}"
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

    def get_service_status(self, unique_id: str = None):
        """Get status of all services or a specific service"""
        if unique_id:
            if unique_id not in self.services:
                raise HTTPException(status_code=404, detail=f"Service with ID {unique_id} not found")
            return self.services[unique_id].to_json_dict()
        
        return {id: service.to_json_dict() for id, service in self.services.items()}

    def get_worker_specs(self):
        """Get the worker's specs"""
        try:
            specs_path = f"/workers/{self.worker_name}/specs"
            specs_json = self.storage.get(specs_path)
            if specs_json:
                specs_dict = json.loads(specs_json)
                return Specs.from_dict(specs_dict)
            else:
                raise HTTPException(status_code=404, detail=f"Specs for worker {self.worker_name} not found")
        except Exception as e:
            error_msg = f"Error getting specs for worker {self.worker_name}: {e}"
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

    def get_resource_usage(self):
        """Get the worker's current resource usage"""
        try:
            # Calculate current usage based on deployed services
            cpu_usage = 0
            ram_usage = 0
            disk_usage = 0
            
            for service in self.services.values():
                if service.status in [Status.DEPLOYED, Status.STARTED]:
                    resources = service.get_requested_resources
                    cpu_usage += resources.get_cpu
                    ram_usage += resources.get_ram
                    disk_usage += resources.get_disk
            
            resources = Resources(cpu=cpu_usage, ram=ram_usage, disk=disk_usage)
            resource_usage = ResourceUsage(resource_usage=resources)
            
            return resource_usage
        except Exception as e:
            error_msg = f"Error calculating resource usage for worker {self.worker_name}: {e}"
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

    def _update_resource_usage(self):
        """Update the worker's current resource usage in storage"""
        try:
            resource_usage = self.get_resource_usage()
            usage_path = f"/workers/{self.worker_name}/current_usage"
            self.storage.put(usage_path, json.dumps(resource_usage.to_json_dict()))
        except Exception as e:
            print(f"Error updating resource usage in storage: {e}")

# Create FastAPI app
app = FastAPI(title=f"Worker Node API")
worker_instance = None

# API endpoints
@app.post("/services/{unique_id}/deploy")
async def deploy_service(unique_id: str, service: Service):
    """Deploy a service"""
    if not worker_instance:
        raise HTTPException(status_code=500, detail="Worker node not initialized")
    return worker_instance.deploy_service(service, unique_id)

@app.post("/services/{unique_id}/start")
async def start_service(unique_id: str):
    """Start a service"""
    if not worker_instance:
        raise HTTPException(status_code=500, detail="Worker node not initialized")
    return worker_instance.start_service(unique_id)

@app.post("/services/{unique_id}/stop")
async def stop_service(unique_id: str):
    """Stop a service"""
    if not worker_instance:
        raise HTTPException(status_code=500, detail="Worker node not initialized")
    return worker_instance.stop_service(unique_id)

@app.get("/services/{unique_id}")
async def get_service_status(unique_id: str):
    """Get status of a specific service"""
    if not worker_instance:
        raise HTTPException(status_code=500, detail="Worker node not initialized")
    return worker_instance.get_service_status(unique_id)

@app.get("/services")
async def get_all_services():
    """Get status of all services"""
    if not worker_instance:
        raise HTTPException(status_code=500, detail="Worker node not initialized")
    return worker_instance.get_service_status()

@app.get("/specs")
async def get_worker_specs():
    """Get worker specs"""
    if not worker_instance:
        raise HTTPException(status_code=500, detail="Worker node not initialized")
    return worker_instance.get_worker_specs().to_json_dict()

@app.get("/usage")
async def get_resource_usage():
    """Get current resource usage"""
    if not worker_instance:
        raise HTTPException(status_code=500, detail="Worker node not initialized")
    return worker_instance.get_resource_usage().to_json_dict()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "worker_name": worker_instance.worker_name if worker_instance else "not_initialized"}

def signal_handler(sig, frame):
    """Handle termination signals"""
    print("Received termination signal, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Worker Node API Service')
    parser.add_argument('--worker-name', type=str, default=os.environ.get("WORKER_NAME", "worker1"),
                        help='Name of this worker node')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind the server to')
    parser.add_argument('--port', type=int, default=8001, help='Port to bind the server to')
    parser.add_argument('--etcd-host', type=str, default='127.0.0.1', help='Etcd host')
    parser.add_argument('--etcd-port', type=int, default=2379, help='Etcd port')
    
    args = parser.parse_args()
    
    # Create worker instance
    worker_instance = WorkerNode(args.worker_name, etcd_host=args.etcd_host, etcd_port=args.etcd_port)
    worker_instance.api_port = args.port
    
    print(f"Worker node {args.worker_name} API running at http://{args.host}:{args.port}")
    
    # Start the FastAPI server
    uvicorn.run(app, host=args.host, port=args.port)
