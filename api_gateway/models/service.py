from pydantic import BaseModel
from models.resources import Resources

class Service(BaseModel):
    service_name: str
    image_url: str
    number_of_replicas: int
    requested_resources: Resources

    # Getter for service_name.
    @property
    def get_service_name(self) -> str:
        return self.service_name

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
        "service_name": "1234",
        "image_url": "//dkfkfngfngngfj",
        "number_of_replicas": 8,
        "requested_resources": {
            "cpu": 3,
            "ram": 10,
            "disk": 50
        }
    }

    # Create an instance of Service from a dictionary.
    service = Service.from_dict(sample_data)

    # Access the fields using the getter properties.
    print("Service Name:", service.get_service_name)
    print("Image URL:", service.get_image_url)
    print("Number of Replicas:", service.get_number_of_replicas)
    print("Requested Resources:", service.get_requested_resources)

    # Convert the instance back to a JSON dictionary.
    print("JSON Dictionary:", service.to_json_dict())