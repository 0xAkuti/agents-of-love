import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Storage settings
    STORAGE_TYPE: str = os.getenv('STORAGE_TYPE', 'local')
    STORAGE_BASE_PATH: str = os.getenv('STORAGE_BASE_PATH', str(Path('data').absolute()))
    S3_BUCKET_NAME: Optional[str] = os.getenv('S3_BUCKET_NAME')
    S3_ENDPOINT_URL: Optional[str] = os.getenv('S3_ENDPOINT_URL')
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION: Optional[str] = os.getenv('AWS_REGION')
    
    # Storage paths
    WALLETS_PATH: str = 'wallets'  # Directory for wallet JSON files
    TOKEN_REGISTRY_PATH: str = 'registry/tokens.json'
    AGENT_STATES_PATH: str = 'states'
    USER_AGENTS_PATH: str = 'agents/users'
    CONVERSATIONS_PATH: str = 'conversations'
    PROMPTS_PATH: str = 'prompts'
    
    @classmethod
    def get_wallet_path(cls, agent_id: str) -> str:
        """Get the path for a wallet JSON file"""
        return f"{cls.WALLETS_PATH}/{agent_id}.json"
    
    @classmethod
    def get_agent_state_path(cls, user_id: int) -> str:
        return f"{cls.AGENT_STATES_PATH}/{user_id}_state.json"
    
    @classmethod
    def get_user_agent_path(cls, user_id: int) -> str:
        return f"{cls.USER_AGENTS_PATH}/{user_id}.json"
    
    @classmethod
    def get_conversation_path(cls, conversation_id: int, participants: list[str]) -> str:
        return f"{cls.CONVERSATIONS_PATH}/{conversation_id}_{'_'.join(participants)}.md"
    
    @classmethod
    def get_prompt_path(cls, prompt_name: str) -> str:
        return f"{cls.PROMPTS_PATH}/{prompt_name}.txt" 