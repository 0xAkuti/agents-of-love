from typing import Optional, Dict, Any, List
from .base import StorageInterface
from .factory import StorageFactory
from ..config import Config


class StorageManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StorageManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.storage = StorageFactory.create_storage(
            storage_type=Config.STORAGE_TYPE,
            base_path=Config.STORAGE_BASE_PATH,
            bucket_name=Config.S3_BUCKET_NAME,
            endpoint_url=Config.S3_ENDPOINT_URL,
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION
        )
        self._initialized = True
    
    async def save_agent_state(self, user_id: int, state: Dict[str, Any]) -> None:
        """Save agent state to storage"""
        path = Config.get_agent_state_path(user_id)
        await self.storage.write_json(path, state)
    
    async def load_agent_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Load agent state from storage"""
        path = Config.get_agent_state_path(user_id)
        if await self.storage.exists(path):
            return await self.storage.read_json(path)
        return None
    
    async def save_user_agent(self, user_id: int, agent_data: Dict[str, Any]) -> None:
        """Save user agent data to storage"""
        path = Config.get_user_agent_path(user_id)
        await self.storage.write_json(path, agent_data)
    
    async def load_user_agent(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Load user agent data from storage"""
        path = Config.get_user_agent_path(user_id)
        if await self.storage.exists(path):
            return await self.storage.read_json(path)
        return None
    
    async def save_conversation(self, conversation_id: int, participants: List[str], content: str) -> None:
        """Save conversation to storage"""
        path = Config.get_conversation_path(conversation_id, participants)
        await self.storage.write_text(path, content)
    
    async def load_conversation(self, conversation_id: int, participants: List[str]) -> Optional[str]:
        """Load conversation from storage"""
        path = Config.get_conversation_path(conversation_id, participants)
        if await self.storage.exists(path):
            return await self.storage.read_text(path)
        return None
    
    async def load_prompt(self, prompt_name: str) -> Optional[str]:
        """Load prompt template from storage"""
        path = Config.get_prompt_path(prompt_name)
        if await self.storage.exists(path):
            return await self.storage.read_text(path)
        return None
    
    async def save_token_registry(self, registry_data: Dict[str, Any]) -> None:
        """Save token registry to storage"""
        await self.storage.write_json(Config.TOKEN_REGISTRY_PATH, registry_data)
    
    async def load_token_registry(self) -> Optional[Dict[str, Any]]:
        """Load token registry from storage"""
        if await self.storage.exists(Config.TOKEN_REGISTRY_PATH):
            return await self.storage.read_json(Config.TOKEN_REGISTRY_PATH)
        return None 