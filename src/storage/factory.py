from typing import Optional
from .base import StorageInterface
from .local import LocalStorage
from .s3 import S3Storage


class StorageFactory:
    @staticmethod
    def create_storage(
        storage_type: str,
        base_path: Optional[str] = None,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None
    ) -> StorageInterface:
        """
        Create a storage implementation based on configuration.
        
        Args:
            storage_type: Type of storage ('local' or 's3')
            base_path: Base path for local storage
            bucket_name: S3 bucket name
            endpoint_url: Optional S3 endpoint URL
            aws_access_key_id: Optional AWS access key
            aws_secret_access_key: Optional AWS secret key
            region_name: Optional AWS region
            
        Returns:
            StorageInterface implementation
        """
        if storage_type == 'local':
            if not base_path:
                raise ValueError("base_path is required for local storage")
            return LocalStorage(base_path)
        elif storage_type == 's3':
            if not bucket_name:
                raise ValueError("bucket_name is required for S3 storage")
            return S3Storage(
                bucket_name=bucket_name,
                endpoint_url=endpoint_url,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )
        else:
            raise ValueError(f"Unknown storage type: {storage_type}") 