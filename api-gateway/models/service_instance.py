# Define the main ServiceInstance model.
from pydantic import BaseModel
from enum import Enum
from models.resources import Resources


class Status(Enum):
    DEPLOY_REQUESTED = 'deploy requested'
    DEPLOYED = 'deployed'
    START_REQUESTED = 'start requested'
    STARTED = 'started'
    STOP_REQUESTED = 'stop requested'
    STOPPED = 'stopped'

class ServiceInstance(BaseModel):
    unique_id: str
    status: Status
    image_url: str
    number_of_replicas: int
    requested_resources: Resources

    # Getter for unique_id.
    @property
    def get_unique_id(self) -> str:
        return self.unique_id

    # Getter for status.
    @property
    def get_status(self) -> Status:
        return self.status

    # Getter for image_url.
    @property
    def get_image_url(self) -> str:
        return self.image_url

    # Getter for number_of_replicas.
    @property
    def get_number_of_replicas(self) -> int:
        return self.number_of_replicas

    # Getter for requested_resources.
    @property
    def get_requested_resources(self) -> Resources:
        return self.requested_resources

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
        "unique_id": "1234",
        "status": "deployed",
        "image_url": "//dkfkfngfngngfj",
        "number_of_replicas": 8,
        "requested_resources": {
            "cpu": 3,
            "ram": 10,
            "disk": 50
        }
    }

    # Create an instance of JobDeployed from a dictionary.
    service = ServiceInstance.from_dict(sample_data)

    # Access the fields using the getter properties.
    print("Unique ID:", service.get_unique_id)
    print("Status:", service.get_status)
    print("Image URL:", service.get_image_url)
    print("Number of Replicas:", service.get_number_of_replicas)
    print("Requested Resources:", service.get_requested_resources)

    # Convert the instance back to a JSON dictionary.
    print("JSON Dictionary:", service.to_json_dict())