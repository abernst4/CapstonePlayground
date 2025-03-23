from pydantic import BaseModel
from models.resources import Resources

class Specs(BaseModel):
    specs: Resources

    # Getter for specs
    @property
    def get_specs(self) -> Resources:
        return self.specs

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
        "specs": {
            "cpu": 4,
            "ram": 16,
            "disk": 200
        }
    }

    # Create an instance of Specs from a dictionary
    specs = Specs.from_dict(sample_data)

    # Access the field using the getter property
    print("Specs:", specs.get_specs)

    # Convert the instance back to a JSON dictionary
    print("JSON Dictionary:", specs.to_json_dict())