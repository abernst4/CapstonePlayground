import streamlit as st
import subprocess
import json
import time
import pandas as pd
import altair as alt
from datetime import datetime
import random
import re

st.set_page_config(
    page_title="Node Cluster Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
    }
    .stButton button {
        width: 100%;
    }
    .metric-box {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
        border-left: 4px solid #007bff;
    }
    .node-card {
        border: 1px solid #ccc;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        transition: all 0.3s ease;
        background-color: #f5f9ff;
    }
    .node-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        background-color: #e9f2ff;
    }
    .job-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        transition: all 0.3s ease;
        background-color: #f9f9f9;
    }
    .job-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        background-color: #f0f0f0;
    }
    .warning {
        color: #856404;
        background-color: #fff3cd;
        border-color: #ffeeba;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .critical {
        color: #721c24;
        background-color: #f8d7da;
        border-color: #f5c6cb;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    /* Make nav links look like buttons */
    .nav-link {
        display: inline-block;
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        background-color: #f0f0f0;
        border-radius: 4px;
        text-decoration: none;
        color: #333;
        transition: background-color 0.2s ease;
    }
    .nav-link:hover {
        background-color: #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# Define etcd node endpoints
NODES = {
    "etcd1": "http://localhost:2379",
    "etcd2": "http://localhost:22379",
    "etcd3": "http://localhost:32379"
    # You can add more nodes here and the dashboard will scale dynamically
    # "etcd4": "http://localhost:42379",
    # ...
    # "etcd12": "http://localhost:122379"
}

# =================================
# DATA LAYER (BACKEND FUNCTIONS)
# =================================

# Function to run etcdctl command
def run_etcdctl(node, command):
    try:
        full_command = f"docker exec {node} etcdctl --endpoints=http://{node}:2379 {command}"
        result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.returncode == 0
    except Exception as e:
        return str(e), False

# Function to get all keys with a specific prefix
def get_keys_with_prefix(node, prefix):
    keys_output, success = run_etcdctl(node, f"get {prefix} --prefix=true")
    if not success or not keys_output:
        return []
    
    # Parse the output - etcdctl returns key-value pairs as alternating lines
    lines = keys_output.splitlines()
    result = []
    
    i = 0
    while i < len(lines):
        if i + 1 < len(lines):
            key = lines[i]
            value = lines[i + 1]
            result.append((key, value))
        i += 2
    
    return result

# Function to check if node is healthy
def check_node_health(node_name):
    endpoint = NODES[node_name]
    try:
        full_command = f"curl -s {endpoint}/health"
        result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
        response = result.stdout.strip()
        return "true" in response, response
    except Exception as e:
        return False, str(e)

# Function to get node metrics
def get_node_metrics(node_name):
    # Get CPU metrics for this specific node only
    cpu_keys = get_keys_with_prefix(node_name, f"nodes/{node_name}/cpu")
    cpu_data = {}
    for key, value in cpu_keys:
        # Extract the job name from the key
        job_name = key.split('/')[-1]
        # Check if the job belongs to this node (should contain node name in job name)
        node_number = node_name.replace("etcd", "")
        if f"node{node_number}-" in job_name:
            cpu_data[job_name] = float(value)
    
    # Get memory metrics for this specific node
    memory_keys = get_keys_with_prefix(node_name, f"nodes/{node_name}/memory")
    memory_data = {}
    for key, value in memory_keys:
        job_name = key.split('/')[-1]
        node_number = node_name.replace("etcd", "")
        if f"node{node_number}-" in job_name:
            memory_data[job_name] = float(value)
    
    # Get disk metrics for this specific node
    disk_keys = get_keys_with_prefix(node_name, f"nodes/{node_name}/disk")
    disk_data = {}
    for key, value in disk_keys:
        job_name = key.split('/')[-1]
        node_number = node_name.replace("etcd", "")
        if f"node{node_number}-" in job_name:
            disk_data[job_name] = float(value)
    
    # Get jobs running on this specific node
    jobs_keys = get_keys_with_prefix(node_name, f"nodes/{node_name}/jobs")
    jobs_data = {}
    for key, value in jobs_keys:
        job_name = key.split('/')[-1]
        node_number = node_name.replace("etcd", "")
        if f"node{node_number}-" in job_name:
            jobs_data[job_name] = value
    
    return {
        "cpu": cpu_data,
        "memory": memory_data,
        "disk": disk_data,
        "jobs": jobs_data
    }

# Function to get aggregate metrics for all nodes
def get_all_nodes_metrics():
    all_metrics = {}
    for node_name in NODES.keys():
        is_healthy, _ = check_node_health(node_name)
        metrics = get_node_metrics(node_name) if is_healthy else {}
        all_metrics[node_name] = {
            "healthy": is_healthy,
            "metrics": metrics
        }
    
    return all_metrics

# =================================
# STATE MANAGEMENT
# =================================

class DashboardState:
    def __init__(self):
        self.view = "cluster"
        self.selected_node = None
        self.selected_job = None
        self.metrics_history = {}
        self.all_metrics = {}
        self.auto_refresh = False
        self.refresh_interval = 5
        self.last_refresh = datetime.now()
    
    def update_metrics(self):
        # Get fresh metrics
        self.all_metrics = get_all_nodes_metrics()
        
        # Update metrics history
        timestamp = datetime.now()
        
        for node_name, node_data in self.all_metrics.items():
            if node_data["healthy"]:
                if node_name not in self.metrics_history:
                    self.metrics_history[node_name] = []
                
                metrics = node_data["metrics"]
                
                # Calculate totals
                cpu_total = sum(metrics.get("cpu", {}).values())
                memory_total = sum(metrics.get("memory", {}).values())
                disk_total = sum(metrics.get("disk", {}).values())
                
                history_entry = {
                    "timestamp": timestamp,
                    "cpu_total": cpu_total,
                    "memory_total": memory_total,
                    "disk_total": disk_total
                }
                
                self.metrics_history[node_name].append(history_entry)
                
                # Keep only last 100 entries to avoid memory issues
                if len(self.metrics_history[node_name]) > 100:
                    self.metrics_history[node_name].pop(0)
        
        self.last_refresh = datetime.now()
    
    def navigate_to_cluster(self):
        self.view = "cluster"
        self.selected_node = None
        self.selected_job = None
    
    def navigate_to_node(self, node_name):
        self.view = "node"
        self.selected_node = node_name
        self.selected_job = None
    
    def navigate_to_job(self, node_name, job_name):
        self.view = "job"
        self.selected_node = node_name
        self.selected_job = job_name
    
    def maybe_auto_refresh(self):
        if self.auto_refresh:
            time_since_refresh = (datetime.now() - self.last_refresh).total_seconds()
            if time_since_refresh >= self.refresh_interval:
                self.update_metrics()
                return True
        return False

# Initialize the state
if 'dashboard_state' not in st.session_state:
    st.session_state.dashboard_state = DashboardState()

# Get state object for convenience
state = st.session_state.dashboard_state

# Update metrics if needed
if not state.all_metrics:
    state.update_metrics()

# Auto-refresh check
state.maybe_auto_refresh()

# =================================
# COMPONENT VIEWS
# =================================

def render_sidebar():
    st.sidebar.header("Dashboard Controls")
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto Refresh", value=state.auto_refresh)
    refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 1, 30, state.refresh_interval)
    
    # Update state
    state.auto_refresh = auto_refresh
    state.refresh_interval = refresh_interval
    
    # Manual refresh button
    if st.sidebar.button("Refresh Now"):
        state.update_metrics()
    
    # Auto-refresh countdown
    if state.auto_refresh:
        time_since_refresh = (datetime.now() - state.last_refresh).total_seconds()
        time_remaining = max(0, state.refresh_interval - time_since_refresh)
        st.sidebar.write(f"Next refresh in: {time_remaining:.1f} seconds")
    
    # Display last refresh time
    st.sidebar.markdown("---")
    st.sidebar.write(f"Last refreshed: {state.last_refresh.strftime('%H:%M:%S')}")
    st.sidebar.write(f"Dashboard version: 2.0.0")
    
    # Add navigation shortcuts
    st.sidebar.markdown("---")
    st.sidebar.subheader("Navigation")
    if st.sidebar.button("Cluster Overview"):
        state.navigate_to_cluster()
        st.rerun()
    
    if state.view != "cluster":
        if st.sidebar.button(f"Back to Cluster"):
            state.navigate_to_cluster()
            st.rerun()
    
    if state.view == "job" and state.selected_node:
        if st.sidebar.button(f"Back to {state.selected_node}"):
            state.navigate_to_node(state.selected_node)
            st.rerun()

def render_cluster_view():
    st.header("Cluster Health")
    
    # Calculate number of columns based on number of nodes
    num_nodes = len(NODES)
    nodes_per_row = 4  # Show 4 nodes per row
    
    # Create rows based on number of nodes
    for i in range(0, num_nodes, nodes_per_row):
        cols = st.columns(min(nodes_per_row, num_nodes - i))
        
        for j, node_name in enumerate(list(NODES.keys())[i:i+nodes_per_row]):
            if j < len(cols):  # Ensure we don't exceed the number of columns
                with cols[j]:
                    is_healthy = state.all_metrics[node_name]["healthy"]
                    health_status = "Healthy" if is_healthy else "Unhealthy"
                    health_color = "green" if is_healthy else "red"
                    
                    st.markdown(f"""
                    <div class="node-card">
                        <h3>{node_name}</h3>
                        <p style="color: {health_color};">{health_status}</p>
                        <p>Endpoint: {NODES[node_name]}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Direct button that sets state and triggers rerun
                    if st.button(f"Select {node_name}", key=f"select_{node_name}", use_container_width=True):
                        state.navigate_to_node(node_name)
                        st.rerun()
    
    # Display aggregate metrics
    st.header("Cluster Resource Usage")
    
    # Create a DataFrame for the metrics
    metrics_df = []
    for node_name, node_data in state.all_metrics.items():
        if node_data["healthy"]:
            metrics = node_data["metrics"]
            cpu_total = sum(metrics.get("cpu", {}).values())
            memory_total = sum(metrics.get("memory", {}).values())
            disk_total = sum(metrics.get("disk", {}).values())
            
            metrics_df.append({
                "Node": node_name,
                "CPU Usage (%)": cpu_total,
                "Memory Usage (MB)": memory_total,
                "Disk Usage (GB)": disk_total,
                "Running Jobs": len(metrics.get("jobs", {}))
            })
    
    if metrics_df:
        # Display as a table
        st.dataframe(pd.DataFrame(metrics_df), use_container_width=True)
        
        # Create a chart for resource usage
        chart_data = pd.DataFrame(metrics_df)
        
        # CPU Chart
        cpu_chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Node:N', title='Node'),
            y=alt.Y('CPU Usage (%):Q', title='CPU Usage (%)'),
            color=alt.Color('Node:N', legend=None)
        ).properties(
            title='CPU Usage by Node',
            height=200
        )
        
        # Memory Chart
        memory_chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Node:N', title='Node'),
            y=alt.Y('Memory Usage (MB):Q', title='Memory Usage (MB)'),
            color=alt.Color('Node:N', legend=None)
        ).properties(
            title='Memory Usage by Node',
            height=200
        )
        
        # Disk Chart
        disk_chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Node:N', title='Node'),
            y=alt.Y('Disk Usage (GB):Q', title='Disk Usage (GB)'),
            color=alt.Color('Node:N', legend=None)
        ).properties(
            title='Disk Usage by Node',
            height=200
        )
        
        # Display charts side by side
        col1, col2, col3 = st.columns(3)
        with col1:
            st.altair_chart(cpu_chart, use_container_width=True)
        with col2:
            st.altair_chart(memory_chart, use_container_width=True)
        with col3:
            st.altair_chart(disk_chart, use_container_width=True)
    else:
        st.info("No metrics data available yet. Please refresh or check node health.")

def render_node_view():
    node_name = state.selected_node
    
    # Add back button
    if st.button("← Back to Cluster View", key="back_to_cluster", use_container_width=False):
        state.navigate_to_cluster()
        st.rerun()
    
    st.header(f"{node_name} Details")
    
    if state.all_metrics[node_name]["healthy"]:
        metrics = state.all_metrics[node_name]["metrics"]
        
        # Display jobs running on the node as boxes
        st.subheader("Running Jobs")
        jobs_data = metrics.get("jobs", {})
        
        if jobs_data:
            # Show jobs in a grid (4 jobs per row)
            num_jobs = len(jobs_data)
            jobs_per_row = 4
            
            # Create rows based on number of jobs
            job_items = list(jobs_data.items())
            for i in range(0, num_jobs, jobs_per_row):
                job_cols = st.columns(min(jobs_per_row, num_jobs - i))
                
                for j, (job_name, job_type) in enumerate(job_items[i:i+jobs_per_row]):
                    if j < len(job_cols):  # Ensure we don't exceed the number of columns
                        with job_cols[j]:
                            # Get resource usage for preview
                            cpu_usage = metrics.get("cpu", {}).get(job_name, 0)
                            memory_usage = metrics.get("memory", {}).get(job_name, 0)
                            
                            # Make job name more prominent
                            job_card = f"""
                            <div class="job-card">
                                <h3 style="color: #0066cc; margin-bottom: 10px;">{job_name}</h3>
                                <p><strong>Type:</strong> {job_type}</p>
                                <p><strong>CPU:</strong> {cpu_usage:.1f}%</p>
                                <p><strong>Memory:</strong> {memory_usage:.1f} MB</p>
                            </div>
                            """
                            st.markdown(job_card, unsafe_allow_html=True)
                            
                            # Direct button that sets state and triggers rerun
                            if st.button(f"View {job_name}", key=f"job_{job_name}", use_container_width=True):
                                state.navigate_to_job(node_name, job_name)
                                st.rerun()
        else:
            st.info(f"No jobs running on {node_name}.")
        
        # Display historical metrics for this node
        st.subheader("Resource Usage Over Time")
        
        if node_name in state.metrics_history and state.metrics_history[node_name]:
            history_df = pd.DataFrame(state.metrics_history[node_name][-20:])  # Last 20 entries
            history_df['formatted_time'] = history_df['timestamp'].dt.strftime('%H:%M:%S')
            
            # CPU history chart
            cpu_history = alt.Chart(history_df).mark_line().encode(
                x=alt.X('formatted_time:N', title='Time', sort=None),
                y=alt.Y('cpu_total:Q', title='CPU Usage (%)'),
                tooltip=['formatted_time', 'cpu_total']
            ).properties(
                title='CPU Usage History',
                height=200
            )
            
            # Memory history chart
            memory_history = alt.Chart(history_df).mark_line().encode(
                x=alt.X('formatted_time:N', title='Time', sort=None),
                y=alt.Y('memory_total:Q', title='Memory Usage (MB)'),
                tooltip=['formatted_time', 'memory_total']
            ).properties(
                title='Memory Usage History',
                height=200
            )
            
            # Disk history chart
            disk_history = alt.Chart(history_df).mark_line().encode(
                x=alt.X('formatted_time:N', title='Time', sort=None),
                y=alt.Y('disk_total:Q', title='Disk Usage (GB)'),
                tooltip=['formatted_time', 'disk_total']
            ).properties(
                title='Disk Usage History',
                height=200
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.altair_chart(cpu_history, use_container_width=True)
                st.altair_chart(disk_history, use_container_width=True)
            with col2:
                st.altair_chart(memory_history, use_container_width=True)
        else:
            st.info("No historical data available yet. Wait for a few refresh cycles.")
    else:
        st.error(f"{node_name} is currently unhealthy or unavailable.")

def render_job_view():
    node_name = state.selected_node
    job_name = state.selected_job
    
    # Add back buttons
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back to Cluster View", key="back_to_cluster_from_job"):
            state.navigate_to_cluster()
            st.rerun()
    with col2:
        if st.button(f"← Back to {node_name}", key="back_to_node"):
            state.navigate_to_node(node_name)
            st.rerun()
    
    st.header(f"Job Details: {job_name}")
    
    if state.all_metrics[node_name]["healthy"]:
        metrics = state.all_metrics[node_name]["metrics"]
        jobs_data = metrics.get("jobs", {})
        
        if job_name in jobs_data:
            job_type = jobs_data[job_name]
            
            # Get resource usage for this job
            cpu_usage = metrics.get("cpu", {}).get(job_name, 0)
            memory_usage = metrics.get("memory", {}).get(job_name, 0)
            disk_usage = metrics.get("disk", {}).get(job_name, 0)
            
            # Create job info card
            st.markdown(f"""
            <div class="job-card" style="padding: 20px; background-color: #f0f8ff;">
                <h3>{job_name}</h3>
                <p><strong>Type:</strong> {job_type}</p>
                <p><strong>Node:</strong> {node_name}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Display metrics
            st.subheader("Resource Usage")
            metric_cols = st.columns(3)
            with metric_cols[0]:
                st.metric("CPU Usage", f"{cpu_usage:.1f}%", delta=None)
            with metric_cols[1]:
                st.metric("Memory Usage", f"{memory_usage:.1f} MB", delta=None)
            with metric_cols[2]:
                st.metric("Disk Usage", f"{disk_usage:.1f} GB", delta=None)
            
            # Detailed chart for this job's resource usage (if available)
            st.subheader("Resource Usage Visualization")
            
            # Create dummy data for demonstration (real implementation would track history per job)
            if node_name in state.metrics_history and state.metrics_history[node_name]:
                # For simplicity, we'll generate sample data based on the current value
                chart_data = []
                history = state.metrics_history[node_name][-10:]  # Last 10 entries
                
                for i, entry in enumerate(history):
                    # Generate slightly varying values based on current metrics
                    cpu_var = cpu_usage * (0.9 + 0.2 * random.random())  # Vary by ±10%
                    memory_var = memory_usage * (0.9 + 0.2 * random.random())
                    disk_var = disk_usage * (0.95 + 0.1 * random.random())
                    
                    chart_data.append({
                        "time": entry["timestamp"].strftime('%H:%M:%S'),
                        "CPU (%)": cpu_var,
                        "Memory (MB)": memory_var,
                        "Disk (GB)": disk_var
                    })
                
                # Convert to DataFrame for charting
                df = pd.DataFrame(chart_data)
                
                # Create chart
                cpu_chart = alt.Chart(df).mark_line(color='blue').encode(
                    x='time',
                    y=alt.Y('CPU (%)', title='CPU Usage (%)'),
                    tooltip=['time', 'CPU (%)']
                ).properties(title='CPU Usage', height=250)
                
                memory_chart = alt.Chart(df).mark_line(color='green').encode(
                    x='time',
                    y=alt.Y('Memory (MB)', title='Memory Usage (MB)'),
                    tooltip=['time', 'Memory (MB)']
                ).properties(title='Memory Usage', height=250)
                
                # Display charts
                col1, col2 = st.columns(2)
                with col1:
                    st.altair_chart(cpu_chart, use_container_width=True)
                with col2:
                    st.altair_chart(memory_chart, use_container_width=True)
            else:
                st.info("No historical data available for this job yet.")
            
            # Job management options
            st.subheader("Job Management")
            action_cols = st.columns(4)
            with action_cols[0]:
                if st.button("Restart Job", key="restart_job"):
                    st.success(f"Simulated: {job_name} restart initiated")
            with action_cols[1]:
                if st.button("Stop Job", key="stop_job"):
                    st.error(f"Simulated: {job_name} stop initiated")
            with action_cols[2]:
                if st.button("View Logs", key="view_logs"):
                    st.info(f"Simulated: Fetching logs for {job_name}")
            with action_cols[3]:
                if st.button("Scale Resources", key="scale_resources"):
                    st.info(f"Simulated: Resource scaling dialog for {job_name}")
        else:
            st.error(f"Job {job_name} was not found or is no longer running.")
    else:
        st.error(f"{node_name} is currently unhealthy or unavailable.")

# =================================
# MAIN APP RENDERING
# =================================

# Main dashboard title
st.title("Node Cluster Dashboard")

# Render sidebar
render_sidebar()

# Render the appropriate view based on state
if state.view == "cluster":
    render_cluster_view()
elif state.view == "node" and state.selected_node in NODES:
    render_node_view()
elif state.view == "job" and state.selected_node in NODES and state.selected_job:
    render_job_view()
else:
    # If invalid state, reset to cluster view
    state.navigate_to_cluster()
    st.rerun()
