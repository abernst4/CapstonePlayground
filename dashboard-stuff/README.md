This is the dir about the streamlit dashboard. Right now I have just been prompting chat for things; I don't really know how streamlit works, but I'll get to that this week. 

In order to run this you require two terminals: one for the metrics bash script and another to do 'streamlit run sack-dashboard.py'. You can run 'docker-compose up -d' before any of the two commands 
to get the servers set up. 

Furthermore, it's best to create your own virtual environment (python3 -m venv <name of your virtual environment>) and then pip3 install the packages necessary. enjoy

What is happening: 
    - The docker compose creates 3 nodes with etcd installed and working among the 3 nodes (and between them)
    - The metrics bash script first deletes the nodes and then puts random entries into etcd, like ram, cpu, and disk nubmers
    - The dashboard displays the dynamic info from all etcd nodes
