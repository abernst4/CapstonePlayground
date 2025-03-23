from pydantic import BaseModel
from typing import List

class BackendConfig(BaseModel):
    backend_type: str
    control_plane_ports: List[int]
    
    # Getter for backend_type
    @property
    def get_backend_type(self) -> str:
        return self.backend_type
    
    # Getter for control_plane_ports
    @property
    def get_control_plane_ports(self) -> List[int]:
        return self.control_plane_ports
    
    # Method to convert the object into a JSON-ready dictionary
    def to_json_dict(self) -> dict:
        return self.model_dump()
    
    # A class method that creates an instance from a dictionary
    @classmethod
    def from_dict(cls, data: dict):
        return cls.model_validate(data)

# Example usage
if __name__ == '__main__':
    sample_data = {
        "backend_type": "etcd",
        "control_plane_ports": [100, 200, 300]
    }
    
    # Create an instance of BackendConfig from a dictionary
    backend_config = BackendConfig.from_dict(sample_data)
    
    # Access the fields using the getter properties
    print("Backend Type:", backend_config.get_backend_type)
    print("Control Plane Ports:", backend_config.get_control_plane_ports)
    
    # Convert the instance back to a JSON dictionary
    print("JSON Dictionary:", backend_config.to_json_dict())