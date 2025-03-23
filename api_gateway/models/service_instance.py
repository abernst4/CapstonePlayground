from enum import Enum
from models.service import Service

class Status(Enum):
    DEPLOY_REQUESTED = 'deploy requested'
    DEPLOYED = 'deployed'
    START_REQUESTED = 'start requested'
    STARTED = 'started'
    STOP_REQUESTED = 'stop requested'
    STOPPED = 'stopped'

class ServiceInstance(Service):
    unique_id: str
    status: Status

    # Getter for unique_id.
    @property
    def get_unique_id(self) -> str:
        return self.unique_id

    # Getter for status.
    @property
    def get_status(self) -> Status:
        return self.status

    # Method to convert the object into a JSON-ready dictionary.
    def to_json_dict(self) -> dict:
        return self.model_dump()

    # A class method that creates an instance from a dictionary.
    @classmethod
    def from_dict(cls, data: dict):
        return cls.model_validate(data)

# Example usage
if __name__ == '__main__':
    sample_data = {
        "unique_id": "1234-worker1-1",
        "status": "deployed",
        "service_name": "1234",
        "image_url": "//dkfkfngfngngfj",
        "number_of_replicas": 8,
        "requested_resources": {
            "cpu": 3,
            "ram": 10,
            "disk": 50
        }
    }

    # Create an instance of ServiceInstance from a dictionary.
    service = ServiceInstance.from_dict(sample_data)

    # Access the fields using the getter properties.
    print("Unique ID:", service.get_unique_id)
    print("Status:", service.get_status)
    print("Service Name:", service.get_service_name)
    print("Image URL:", service.get_image_url)
    print("Number of Replicas:", service.get_number_of_replicas)
    print("Requested Resources:", service.get_requested_resources)

    # Convert the instance back to a JSON dictionary.
    print("JSON Dictionary:", service.to_json_dict())