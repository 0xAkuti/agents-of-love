import json
from typing import Any, Dict, List, Optional
import aioboto3
from .base import StorageInterface


class S3Storage(StorageInterface):
    def __init__(self, bucket_name: str, endpoint_url: Optional[str] = None, 
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 region_name: Optional[str] = None):
        """
        Initialize S3 storage.
        
        Args:
            bucket_name: Name of the S3 bucket
            endpoint_url: Optional custom endpoint URL for S3-compatible storage
            aws_access_key_id: Optional AWS access key
            aws_secret_access_key: Optional AWS secret key
            region_name: Optional AWS region name
        """
        self.bucket_name = bucket_name
        self.session = aioboto3.Session()
        self.client_kwargs = {
            'endpoint_url': endpoint_url,
            'aws_access_key_id': aws_access_key_id,
            'aws_secret_access_key': aws_secret_access_key,
            'region_name': region_name
        }
        # Remove None values
        self.client_kwargs = {k: v for k, v in self.client_kwargs.items() if v is not None}
        
    async def read_text(self, path: str) -> str:
        async with self.session.client('s3', **self.client_kwargs) as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=path)
            async with response['Body'] as stream:
                data = await stream.read()
                return data.decode('utf-8')
    
    async def write_text(self, path: str, content: str) -> None:
        async with self.session.client('s3', **self.client_kwargs) as s3:
            await s3.put_object(
                Bucket=self.bucket_name,
                Key=path,
                Body=content.encode('utf-8')
            )
    
    async def read_json(self, path: str) -> Dict[str, Any]:
        content = await self.read_text(path)
        return json.loads(content)
    
    async def write_json(self, path: str, content: Dict[str, Any]) -> None:
        json_str = json.dumps(content, indent=2)
        await self.write_text(path, json_str)
    
    async def read_bytes(self, path: str) -> bytes:
        async with self.session.client('s3', **self.client_kwargs) as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=path)
            async with response['Body'] as stream:
                return await stream.read()
    
    async def write_bytes(self, path: str, content: bytes) -> None:
        async with self.session.client('s3', **self.client_kwargs) as s3:
            await s3.put_object(
                Bucket=self.bucket_name,
                Key=path,
                Body=content
            )
    
    async def exists(self, path: str) -> bool:
        try:
            async with self.session.client('s3', **self.client_kwargs) as s3:
                await s3.head_object(Bucket=self.bucket_name, Key=path)
                return True
        except:
            return False
    
    async def delete(self, path: str) -> None:
        async with self.session.client('s3', **self.client_kwargs) as s3:
            await s3.delete_object(Bucket=self.bucket_name, Key=path)
    
    async def list_dir(self, path: str) -> List[str]:
        async with self.session.client('s3', **self.client_kwargs) as s3:
            # Ensure path ends with /
            if path and not path.endswith('/'):
                path += '/'
                
            paginator = s3.get_paginator('list_objects_v2')
            files = []
            
            async for page in paginator.paginate(Bucket=self.bucket_name, Prefix=path):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Remove the prefix from the key
                        key = obj['Key']
                        if key != path:  # Don't include the directory itself
                            relative_path = key[len(path):]
                            # Only include immediate children
                            if '/' not in relative_path:
                                files.append(relative_path)
            
            return files 