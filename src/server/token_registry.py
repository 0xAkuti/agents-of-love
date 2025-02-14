import json
import pathlib
from typing import Dict, Optional
from pydantic import BaseModel
from src.storage.manager import StorageManager

class TokenMetadata(BaseModel):
    token_id: int
    image_url: str
    prompt: str
    participants: list[str]

class NFTAttribute(BaseModel):
    trait_type: str
    value: str

class NFTMetadata(BaseModel):
    description: str
    image: str
    name: str
    attributes: list[NFTAttribute]


class TokenRegistry:
    def __init__(self):
        self.registry: Dict[int, TokenMetadata] = {}
        self.storage = StorageManager()
        self.current_token_id = 0
    
    async def initialize(self):
        await self._load_registry()
    
    async def _load_registry(self):
        """Load the registry from file if it exists."""
        data = await self.storage.load_token_registry()
        if data is None:
            return
        self.registry = {int(k): TokenMetadata(**v) for k, v in data["registry"].items()}
        self.current_token_id = data["current_token_id"]
    
    async def save_registry(self):
        """Save the registry to file."""
        data = {
            "registry": {str(k): v.model_dump() for k, v in self.registry.items()},
            "current_token_id": self.current_token_id
        }
        await self.storage.save_token_registry(data)
    
    async def register_token(self, image_url: str, prompt: str, participants: list[str]) -> TokenMetadata:
        """Register a new token and return its metadata."""
        token_id = self.current_token_id
        self.current_token_id += 1
        
        metadata = TokenMetadata(
            token_id=token_id,
            image_url=image_url,
            prompt=prompt,
            participants=participants
        )
        
        self.registry[token_id] = metadata
        await self.save_registry()
        return metadata
    
    def get_token_metadata(self, token_id: int) -> Optional[TokenMetadata]:
        """Get metadata for a specific token ID."""
        return self.registry.get(token_id) 
    
    async def get_nft_metadata(self, token_id: int) -> Optional[NFTMetadata]:
        """Get metadata for a specific token ID."""
        token = self.registry.get(token_id) 
        if token is None:
            await self._load_registry()
            token = self.registry.get(token_id) 
            if token is None:
                return None
        return NFTMetadata(
            name=f"Date Memory #{token.token_id}",
            description=f"Taken during a date between {token.participants[0]} and {token.participants[1]}",
            image=token.image_url,
            attributes=[
                NFTAttribute(trait_type="User", value=token.participants[0]),
                NFTAttribute(trait_type="Match", value=token.participants[1]),
            ],
        )