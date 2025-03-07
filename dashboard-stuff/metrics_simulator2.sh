#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Define nodes
NODES=("etcd1" "etcd2" "etcd3")

# Define job types
JOB_TYPES=("web-server" "database" "cache" "batch-job" "analytics" "monitoring")

# Function to set a key in etcd
set_etcd_key() {
    local node=$1
    local key=$2
    local value=$3
    
    docker exec $node etcdctl --endpoints=http://$node:2379 put "$key" "$value" > /dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Set key $key=$value on $node${NC}"
    else
        echo -e "${YELLOW}Failed to set key $key on $node${NC}"
    fi
}

# Function to delete a key from etcd
delete_etcd_key() {
    local node=$1
    local key=$2
    
    docker exec $node etcdctl --endpoints=http://$node:2379 del "$key" > /dev/null
}

# Function to wipe all data from the cluster
wipe_cluster_data() {
    echo -e "${RED}Wiping all data from the cluster...${NC}"
    
    for node in "${NODES[@]}"; do
        echo -e "${YELLOW}Clearing all keys from $node...${NC}"
        docker exec $node etcdctl --endpoints=http://$node:2379 del "" --prefix > /dev/null
    done
    
    echo -e "${GREEN}Cluster data wiped successfully${NC}"
}

# Function to generate random value with fluctuation
generate_value() {
    local base=$1
    local fluctuation=$2
    
    local min=$(echo "$base - $fluctuation" | bc)
    local max=$(echo "$base + $fluctuation" | bc)
    local range=$(echo "$max - $min" | bc)
    
    # Generate random value
    echo "scale=2; $min + $range * $RANDOM / 32767" | bc
}

# Function to initialize jobs for a node
initialize_jobs() {
    local node=$1
    local job_count=$2
    
    echo -e "${BLUE}Initializing $job_count jobs for $node...${NC}"
    
    # Clear existing jobs for this node
    docker exec $node etcdctl --endpoints=http://$node:2379 del "nodes/$node" --prefix > /dev/null
    
    # Extract node number
    local node_number=${node#etcd}
    
    # Create new jobs
    for i in $(seq 1 $job_count); do
        # Create node-specific job name
        local job_name="job-node$node_number-$i"
        
        # Select a random job type
        local job_type=${JOB_TYPES[$((RANDOM % ${#JOB_TYPES[@]}))]}
        
        # Set job type
        set_etcd_key $node "nodes/$node/jobs/$job_name" "$job_type"
        
        # Set initial resource usage values
        local cpu_usage=$(generate_value 20 15)
        local memory_usage=$(generate_value 512 256)
        local disk_usage=$(generate_value 5 3)
        
        set_etcd_key $node "nodes/$node/cpu/$job_name" "$cpu_usage"
        set_etcd_key $node "nodes/$node/memory/$job_name" "$memory_usage"
        set_etcd_key $node "nodes/$node/disk/$job_name" "$disk_usage"
    done
}

# Function to update metrics for a node
update_metrics() {
    local node=$1
    
    echo -e "${BLUE}Updating metrics for $node...${NC}"
    
    # Extract node number
    local node_number=${node#etcd}
    
    # Get list of jobs
    local jobs_output=$(docker exec $node etcdctl --endpoints=http://$node:2379 get "nodes/$node/jobs/" --prefix --keys-only)
    local jobs=()
    
    # Parse the output to get job names
    while read -r line; do
        if [[ -n "$line" ]]; then
            local job_name=$(echo "$line" | awk -F'/' '{print $NF}')
            jobs+=("$job_name")
        fi
    done <<< "$jobs_output"
    
    # Update metrics for each job
    for job_name in "${jobs[@]}"; do
        # Get current values
        local current_cpu=$(docker exec $node etcdctl --endpoints=http://$node:2379 get "nodes/$node/cpu/$job_name" --print-value-only)
        local current_memory=$(docker exec $node etcdctl --endpoints=http://$node:2379 get "nodes/$node/memory/$job_name" --print-value-only)
        local current_disk=$(docker exec $node etcdctl --endpoints=http://$node:2379 get "nodes/$node/disk/$job_name" --print-value-only)
        
        # Generate new values with small fluctuations
        local new_cpu=$(generate_value "$current_cpu" 5)
        local new_memory=$(generate_value "$current_memory" 50)
        local new_disk=$(generate_value "$current_disk" 0.5)
        
        # Ensure no negative values
        new_cpu=$(echo "if($new_cpu < 0) 0 else $new_cpu" | bc)
        new_memory=$(echo "if($new_memory < 0) 0 else $new_memory" | bc)
        new_disk=$(echo "if($new_disk < 0) 0 else $new_disk" | bc)
        
        # Update values
        set_etcd_key $node "nodes/$node/cpu/$job_name" "$new_cpu"
        set_etcd_key $node "nodes/$node/memory/$job_name" "$new_memory"
        set_etcd_key $node "nodes/$node/disk/$job_name" "$new_disk"
    done
    
    # Randomly start or stop a job (10% chance)
    if [ $((RANDOM % 10)) -eq 0 ]; then
        if [ ${#jobs[@]} -gt 1 ] && [ $((RANDOM % 2)) -eq 0 ]; then
            # Stop a random job
            local job_to_stop="${jobs[$((RANDOM % ${#jobs[@]}))]}"
            echo -e "${YELLOW}Stopping job $job_to_stop on $node${NC}"
            
            delete_etcd_key $node "nodes/$node/jobs/$job_to_stop"
            delete_etcd_key $node "nodes/$node/cpu/$job_to_stop"
            delete_etcd_key $node "nodes/$node/memory/$job_to_stop"
            delete_etcd_key $node "nodes/$node/disk/$job_to_stop"
        else
            # Start a new job
            local new_job_num=$((RANDOM % 100 + 1))
            local new_job_name="job-node$node_number-$new_job_num"
            local job_type=${JOB_TYPES[$((RANDOM % ${#JOB_TYPES[@]}))]}
            
            echo -e "${GREEN}Starting new job $new_job_name on $node${NC}"
            
            set_etcd_key $node "nodes/$node/jobs/$new_job_name" "$job_type"
            set_etcd_key $node "nodes/$node/cpu/$new_job_name" "$(generate_value 20 15)"
            set_etcd_key $node "nodes/$node/memory/$new_job_name" "$(generate_value 512 256)"
            set_etcd_key $node "nodes/$node/disk/$new_job_name" "$(generate_value 5 3)"
        fi
    fi
}

# Main script
echo -e "${BLUE}Starting node metrics simulator...${NC}"
echo "Press Ctrl+C to stop"

# First wipe all existing data
wipe_cluster_data

# Initialize jobs for each node
initialize_jobs "etcd1" 3
initialize_jobs "etcd2" 4
initialize_jobs "etcd3" 5

# Continuous update loop
while true; do
    for node in "${NODES[@]}"; do
        update_metrics "$node"
    done
    
    echo -e "${BLUE}Waiting 5 seconds before next update...${NC}"
    sleep 5
done
