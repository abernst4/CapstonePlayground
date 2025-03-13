from abc import ABC, abstractmethod
import json
from typing import Dict, List, Optional, Tuple, Any, Union


class StorageService(ABC):
    """Abstract interface for key-value storage systems."""
    
    @abstractmethod
    def put(self, key: str, value: Any) -> None:
        """Store a value at the given key."""
        pass
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key. Returns None if key doesn't exist."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if key existed and was deleted."""
        pass
    
    @abstractmethod
    def get_prefix(self, prefix: str) -> Dict[str, Any]:
        """Get all keys and values with the given prefix."""
        pass
    
    @abstractmethod
    def delete_prefix(self, prefix: str) -> int:
        """Delete all keys with the given prefix. Returns count of deleted keys."""
        pass


class EtcdStorage(StorageService):
    """Etcd implementation of the StorageService interface."""
    
    def __init__(self, host='localhost', port=2379, **kwargs):
        """
        Initialize Etcd client connection.
        
        Args:
            host: Etcd host or load balancer address
            port: Etcd port (default 2379)
            **kwargs: Additional arguments for etcd3.client (ca_cert, cert_key, etc.)
        """
        import etcd3
        self.client = etcd3.client(host=host, port=port, **kwargs)
    
    def put(self, key: str, value: Any) -> None:
        """Store a value at the given key, serializing non-string values as JSON."""
        if not isinstance(value, str):
            value = json.dumps(value)
        self.client.put(key, value)
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key, attempting to deserialize JSON values."""
        result = self.client.get(key)
        if result[0] is None:
            return None
        
        # Decode bytes to string
        value_str = result[0].decode('utf-8')
        
        # Try to parse as JSON, return as string if not valid JSON
        try:
            return json.loads(value_str)
        except json.JSONDecodeError:
            return value_str
    
    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if key existed and was deleted."""
        result = self.client.delete(key)
        return result
    
    def get_prefix(self, prefix: str) -> Dict[str, Any]:
        """Get all keys and values with the given prefix."""
        result = {}
        for item in self.client.get_prefix(prefix):
            value, metadata = item
            key = metadata.key.decode('utf-8')
            
            # Try to decode value as JSON, fallback to string
            try:
                value_str = value.decode('utf-8')
                result[key] = json.loads(value_str)
            except (json.JSONDecodeError, UnicodeDecodeError):
                result[key] = value.decode('utf-8', errors='replace')
        
        return result
    
    def delete_prefix(self, prefix: str) -> int:
        """Delete all keys with the given prefix. Returns count of deleted keys."""
        result = self.client.delete_prefix(prefix)
        return result.deleted
    
class TestStorage(StorageService):
    """Test implementation of the StorageService interface using a dictionary."""

    def __init__(self, **kwargs):
        self.data = {}
    
    def put(self, key: str, value: Any) -> None:
        """Store a value at the given key."""
        self.data[key] = value
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key. Returns None if key doesn't exist."""
        return self.data.get(key)
    
    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if key existed and was deleted."""
        if key in self.data:
            del self.data[key]
            return True
        return False
    
    def get_prefix(self, prefix: str) -> Dict[str, Any]:
        """Get all keys and values with the given prefix."""
        return {k: v for k, v in self.data.items() if k.startswith(prefix)}
    
    def delete_prefix(self, prefix: str) -> int:
        """Delete all keys with the given prefix. Returns count of deleted keys."""
        keys = [k for k in self.data.keys() if k.startswith(prefix)]
        for key in keys:
            del self.data[key]
        return len(keys)


class StorageFactory:
    """Factory class to create storage service instances."""
    
    @staticmethod
    def create(storage_type: str, **config) -> StorageService:
        """
        Create and return a storage service instance.
        
        Args:
            storage_type: Type of storage ('etcd' or 'redis')
            **config: Configuration options for the storage service
            
        Returns:
            StorageService: An initialized storage service
            
        Raises:
            ValueError: If storage_type is not supported
        """
        if storage_type.lower() == 'etcd':
            return EtcdStorage(**config)
        elif storage_type.lower() == 'test':
            return TestStorage(**config)
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")


# Example usage
if __name__ == "__main__":
    # Configuration
    config = {
        'etcd': {
            'host': 'localhost',
            'port': 2379
        }
    }
    
    # Example with dependency injection
    def app_init(storage_service: StorageService):
        # # Store some data
        # storage_service.put('/app/config', {
        #     'version': '1.0.0',
        #     'debug': True,
        #     'features': ['auth', 'reporting', 'export']
        # })
        
        # # Retrieve data
        # config = storage_service.get('/app/config')
        # print(f"App config: {config}")
        
        while True:
            print("Enter a command:")
            print("1. Put")
            print("2. Get")
            print("3. Delete")
            print("4. Get Prefix")
            print("5. Delete Prefix")
            print("6. Exit")
            command = input("Command: ")
            if command == '1':
                key = input("Enter key: ")
                value = input("Enter value: ")
                storage_service.put(key, value)
            elif command == '2':
                key = input("Enter key: ")
                value = storage_service.get(key)
                print(f"Value: {value}")
            elif command == '3':
                key = input("Enter key: ")
                result = storage_service.delete(key)
                print(f"Deleted: {result}")
            elif command == '4':
                prefix = input("Enter prefix: ")
                values = storage_service.get_prefix(prefix)
                print(f"Values: {values}")
            elif command == '5':
                prefix = input("Enter prefix: ")
                count = storage_service.delete_prefix(prefix)
                print(f"Deleted {count} keys.")
            elif command == '6':
                break
            else:
                print("Invalid command.")
    
    # # Initialize with etcd
    # etcd_storage = StorageFactory.create('etcd', **config['etcd'])
    # app_init(etcd_storage)
    
    # # Initialize with redis
    # redis_storage = StorageFactory.create('redis', **config['redis'])
    # app_init(redis_storage)

    # Initialize with test storage
    storage_type = input("Enter storage service (etcd/test): ")
    if storage_type == 'etcd':
        storage_service = StorageFactory.create('etcd', **config['etcd'])
    else:
        storage_service = StorageFactory.create('test')
    app_init(storage_service)
