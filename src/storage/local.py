import json
import os
from pathlib import Path
from typing import Any, Dict, List
import aiofiles
from .base import StorageInterface


class LocalStorage(StorageInterface):
    def __init__(self, base_path: str):
        """
        Initialize local storage.
        
        Args:
            base_path: Base directory for all storage operations
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    def _get_full_path(self, path: str) -> Path:
        """Get full path from relative path"""
        full_path = self.base_path / path
        # Ensure the parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path
        
    async def read_text(self, path: str) -> str:
        full_path = self._get_full_path(path)
        async with aiofiles.open(full_path, mode='r', encoding='utf-8') as f:
            return await f.read()
    
    async def write_text(self, path: str, content: str) -> None:
        full_path = self._get_full_path(path)
        async with aiofiles.open(full_path, mode='w', encoding='utf-8') as f:
            await f.write(content)
    
    async def read_json(self, path: str) -> Dict[str, Any]:
        content = await self.read_text(path)
        return json.loads(content)
    
    async def write_json(self, path: str, content: Dict[str, Any]) -> None:
        json_str = json.dumps(content, indent=2)
        await self.write_text(path, json_str)
    
    async def read_bytes(self, path: str) -> bytes:
        full_path = self._get_full_path(path)
        async with aiofiles.open(full_path, mode='rb') as f:
            return await f.read()
    
    async def write_bytes(self, path: str, content: bytes) -> None:
        full_path = self._get_full_path(path)
        async with aiofiles.open(full_path, mode='wb') as f:
            await f.write(content)
    
    async def exists(self, path: str) -> bool:
        full_path = self._get_full_path(path)
        return full_path.exists()
    
    async def delete(self, path: str) -> None:
        full_path = self._get_full_path(path)
        if full_path.exists():
            full_path.unlink()
    
    async def list_dir(self, path: str) -> List[str]:
        full_path = self._get_full_path(path)
        if not full_path.exists() or not full_path.is_dir():
            return []
            
        return [item.name for item in full_path.iterdir() if item.is_file()] 