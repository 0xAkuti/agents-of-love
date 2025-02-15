import hashlib
import pathlib
import uuid
from autogen_core.models import ChatCompletionClient

from src.models.model import Agent, AgentRole, ModelProvider, SimpleUser
from src.models.agent_with_wallet import AgentWithWallet
from src.storage.manager import StorageManager
from src.config import Config


class UserAgentWithWallet(AgentWithWallet):
    def __init__(self, user_id: int, name: str, system_message: str, model_client: ChatCompletionClient, agent_role: AgentRole = AgentRole.USER, **kwargs):
        # Create deterministic UUID based on discord user id
        hash_value = hashlib.md5(str(user_id).encode()).hexdigest()
        kwargs["agent_id"] = uuid.UUID(hash_value)
        
        self.storage_manager = StorageManager()
        self.user_id = user_id
        self.agent_data: Agent = None
        
        super().__init__(
            name=name,
            system_message=system_message,
            model_client=model_client,
            agent_role=agent_role,
            **kwargs
        )
    
    @staticmethod
    def get_user_agent_id(user_id: int) -> uuid.UUID:
        hash_value = hashlib.md5(str(user_id).encode()).hexdigest()
        return uuid.UUID(hash_value)
    
    @staticmethod
    def get_user_agent_path(user_id: int) -> pathlib.Path:
        return pathlib.Path(f"agents/users/{user_id}.json")

    async def save_agent_data(self):
        """Save agent data using storage manager"""
        await self.storage_manager.save_user_agent(self.user_id, self.agent_data.model_dump())

    @classmethod
    async def load_or_create(cls, user: SimpleUser):
        storage_manager = StorageManager()
        agent_data = await storage_manager.load_user_agent(user.id)
        
        if agent_data:
            agent = Agent.model_validate(agent_data)
            return await cls.from_agent(agent, user_id=user.id)

        user_agent = Agent(
            id=cls.get_user_agent_id(user.id),
            name=''.join(c for c in user.name if c.isalnum()),
            system_message="",
            model_provider=ModelProvider(provider='openai', model='gpt-4o-mini'),
            role=AgentRole.USER,
        )
        await storage_manager.save_user_agent(user.id, user_agent.model_dump())
        instance = await cls.from_agent(user_agent, user_id=user.id)
        instance.agent_data = user_agent
        return instance
