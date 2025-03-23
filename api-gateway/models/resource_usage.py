from pydantic import BaseModel
from models.resources import Resources

class ResourceUsage(BaseModel):
    resource_usage: Resources

    # Getter for resource_usage
    @property
    def get_resource_usage(self) -> Resources:
        return self.resource_usage

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
        "resource_usage": {
            "cpu": 2,
            "ram": 8,
            "disk": 100
        }
    }

    # Create an instance of ResourceUsage from a dictionary
    resource_usage = ResourceUsage.from_dict(sample_data)

    # Access the field using the getter property
    print("Resource Usage:", resource_usage.get_current_usage)

    # Convert the instance back to a JSON dictionary
    print("JSON Dictionary:", resource_usage.to_json_dict())