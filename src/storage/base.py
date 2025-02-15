from abc import ABC, abstractmethod
from typing import Any, Optional, BinaryIO, Dict, List
from pathlib import Path


class StorageInterface(ABC):
    """Base interface for all storage operations"""
    
    @abstractmethod
    async def read_text(self, path: str) -> str:
        """Read text content from storage"""
        pass
    
    @abstractmethod
    async def write_text(self, path: str, content: str) -> None:
        """Write text content to storage"""
        pass
    
    @abstractmethod
    async def read_json(self, path: str) -> Dict[str, Any]:
        """Read JSON content from storage"""
        pass
    
    @abstractmethod
    async def write_json(self, path: str, content: Dict[str, Any]) -> None:
        """Write JSON content to storage"""
        pass
    
    @abstractmethod
    async def read_bytes(self, path: str) -> bytes:
        """Read binary content from storage"""
        pass
    
    @abstractmethod
    async def write_bytes(self, path: str, content: bytes) -> None:
        """Write binary content to storage"""
        pass
    
    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if path exists in storage"""
        pass
    
    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete content at path"""
        pass
    
    @abstractmethod
    async def list_dir(self, path: str) -> List[str]:
        """List contents of a directory"""
        pass 