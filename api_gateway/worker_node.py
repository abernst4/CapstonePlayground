import requests
import json
import os
import threading
import time
import signal
import sys
from enum import Enum

from storage_classes.etcd_implementation import EtcdClient

class TaskAction(Enum):
    DEPLOY = "deploy"
    START = "start"
    STOP = "stop"

class WorkerNode:
    def __init__(self, worker_name):
        self.worker_name = worker_name
        self.etcd_client = EtcdClient()
        self.watch_path = f"/workers/{worker_name}/tasks"
        self.running = True
        self.tasks = {}
        # Connect to etcd
        self.etcd_client.connect(host="127.0.0.1", port=2379)
        print(f"Worker node {worker_name} initialized and connected to etcd")

    def start_watching(self):
        """Start watching for task updates in a separate thread"""
        self.watch_thread = threading.Thread(target=self._watch_tasks)
        self.watch_thread.daemon = True
        self.watch_thread.start()
        print(f"Worker {self.worker_name} started watching for task updates")

    def _watch_tasks(self):
        """Watch for changes in the etcd tasks directory"""
        while self.running:
            try:
                # Get the watch events generator and cancel function
                event_iterator, cancel = self.etcd_client.client.watch_prefix(self.watch_path)
                
                # Process events from the watch iterator
                for response in event_iterator:
                    try:
                        self._handle_task_update(response)
                    except Exception as e:
                        print(f"Error handling event: {e}")
            except Exception as e:
                print(f"Error watching tasks: {e}")
                time.sleep(1)  # Prevent tight loop on error

    def _handle_task_update(self, event):
        """Handle updates to task status"""
        try:
            # Extract key and value from the event
            key = event.key.decode('utf-8')
            value = event.value.decode('utf-8')
            
            # Extract task name from the path
            path_parts = key.split('/')
            if len(path_parts) < 4:  # Ensure we have enough path parts
                print(f"Invalid path structure: {key}")
                return
                
            task_name = path_parts[-1]
            
            # Parse the JSON value
            task_data = json.loads(value)
            
            # Get the action
            action_str = task_data.get('action')
            if not action_str:
                print(f"No action specified in task data: {task_data}")
                return
                
            action = TaskAction(action_str)
            
            print(f"Received {action.value} action for task {task_name}")
            
            # Process the action
            if action == TaskAction.DEPLOY:
                self._deploy_task(task_name, task_data)
            elif action == TaskAction.START:
                self._start_task(task_name)
            elif action == TaskAction.STOP:
                self._stop_task(task_name)
        except Exception as e:
            print(f"Error handling task update: {e}")

    def _deploy_task(self, task_name, task_data):
        """Deploy a new task"""
        print(f"Deploying task: {task_name}")
        try:
            # Extract required information from task_data
            image_url = task_data.get('image_url')
            if not image_url:
                raise ValueError("No image URL provided in task data")
                
            # Store task information
            self.tasks[task_name] = {
                'image_url': image_url,
                'status': 'deployed',
                'resources': task_data.get('expected_usage', {})
            }
            
            # Update current usage in etcd
            current_usage = {
                "current_usage": self.tasks[task_name]['resources']
            }
            self.etcd_client.put(
                f"/workers/{self.worker_name}/current_usage",
                json.dumps(current_usage)
            )
            
            print(f"Successfully deployed task: {task_name}")
        except Exception as e:
            print(f"Error deploying task {task_name}: {e}")

    def _start_task(self, task_name):
        """Start a deployed task"""
        print(f"Starting task: {task_name}")
        if task_name not in self.tasks:
            print(f"Task {task_name} not deployed")
            return
        
        try:
            # Update task status
            self.tasks[task_name]['status'] = 'running'
            print(f"Successfully started task: {task_name}")
        except Exception as e:
            print(f"Error starting task {task_name}: {e}")

    def _stop_task(self, task_name):
        """Stop a running task"""
        print(f"Stopping task: {task_name}")
        if task_name not in self.tasks:
            print(f"Task {task_name} not deployed")
            return
        
        try:
            # Update task status
            self.tasks[task_name]['status'] = 'stopped'
            print(f"Successfully stopped task: {task_name}")
        except Exception as e:
            print(f"Error stopping task {task_name}: {e}")

    def stop(self):
        """Stop the worker node"""
        print(f"Stopping worker node {self.worker_name}")
        self.running = False
        if hasattr(self, 'watch_thread'):
            self.watch_thread.join(timeout=2)
        print(f"Worker node {self.worker_name} stopped")

    def register_with_etcd(self):
        """Register this worker with etcd"""
        try:
            # Set default specs if not already set
            specs_path = f"/workers/{self.worker_name}/specs"
            specs_exists = self.etcd_client.get(specs_path)
            
            if not specs_exists:
                default_specs = {
                    "specs": {
                        "cpu": 4,
                        "ram": 8,
                        "disk": 100
                    }
                }
                self.etcd_client.put(specs_path, json.dumps(default_specs))
                print(f"Registered worker {self.worker_name} with default specs")
            else:
                print(f"Worker {self.worker_name} already registered")
                
            # Initialize current usage if not set
            usage_path = f"/workers/{self.worker_name}/current_usage"
            usage_exists = self.etcd_client.get(usage_path)
            
            if not usage_exists:
                default_usage = {
                    "current_usage": {
                        "cpu": 0,
                        "ram": 0,
                        "disk": 0
                    }
                }
                self.etcd_client.put(usage_path, json.dumps(default_usage))
                print(f"Initialized current usage for worker {self.worker_name}")
        except Exception as e:
            print(f"Error registering worker with etcd: {e}")

def signal_handler(sig, frame):
    """Handle termination signals"""
    print("Received termination signal, shutting down...")
    if worker:
        worker.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get worker name from environment or use default
    worker_name = os.environ.get("WORKER_NAME", "worker1")
    
    # Create and start worker
    worker = WorkerNode(worker_name)
    
    # Register with etcd
    worker.register_with_etcd()
    
    # Start watching for tasks
    worker.start_watching()
    
    print(f"Worker node {worker_name} running. Press Ctrl+C to stop.")
    
    # Keep the main thread running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        worker.stop()
