The config server reads config information from a file. It returns a dictionary. 
The client node will be running a bash script that parses this data and instantiates a python wrapper class with the arguments it got from the config serer.

If you want the full interactive diagram besides the picture in this repo, please paste the data-flow.yaml file into https://app.ilograph.com/

To run this, just run 'docker-compose up --build' 

This will have 3 different nodes ping the control plane and print out what it recieved. Additionally, if the node is apart of the control plane it will print out "I am in the control plane," otherwise
it will print "I am NOT in the control plane" or something like that
