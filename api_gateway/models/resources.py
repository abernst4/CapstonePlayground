from pydantic import BaseModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.resource_usage import ResourceUsage
    from models.specs import Specs


# Define a model for the nested expected_usage dictionary.
class Resources(BaseModel):
    cpu: int
    ram: int
    disk: int

    @property
    def get_cpu(self) -> int:
        return self.cpu

    @property
    def get_ram(self) -> int:
        return self.ram

    @property
    def get_disk(self) -> int:
        return self.disk

    def to_json_dict(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict):
        return cls.model_validate(data)
    
    @classmethod
    def from_two_specs(cls, total: 'Specs', used: 'ResourceUsage'):
        """
        Create an Resources instance by subtracting the 'used' specs from the 'total' specs.
        Meant to represent an available resources object.
        """
        total_specs = total.get_specs
        used_specs = used.get_current_usage
        available = cls(
            cpu=total_specs.get_cpu - used_specs.get_cpu,
            ram=total_specs.get_ram - used_specs.get_ram,
            disk=total_specs.get_disk - used_specs.get_disk
        )
        return available

if __name__ == '__main__':
    sample_data = {
        "cpu": 3,
        "ram": 10,
        "disk": 50
    }

    resources = Resources.from_dict(sample_data)
    print("CPU:", resources.get_cpu)
    print("RAM:", resources.get_ram)
    print("Disk:", resources.get_disk)
    print("JSON Dictionary:", resources.to_json_dict())