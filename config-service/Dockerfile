FROM python:3.9-slim

WORKDIR /app

# Install jq for JSON parsing in the bash script
RUN apt-get update && apt-get install -y curl jq && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY ha_server.py processor.py client.sh update_config.sh ./

# Make the scripts executable
RUN chmod +x client.sh update_config.sh

# Default command - can be overridden
CMD ["python", "ha_server.py"]
