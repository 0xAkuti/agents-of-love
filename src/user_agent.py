import hashlib
import os
import pathlib
import uuid
from src.model import Agent, AgentRole, ModelProvider
from src.agent_with_wallet import AgentWithWallet
from src.model import AgentRole
from autogen_core.models import ChatCompletionClient
from src.model import SimpleUser
from autogen_ext.models.openai import OpenAIChatCompletionClient
class UserAgentWithWallet(AgentWithWallet):
    def __init__(self, user_id: int, name: str, system_message: str, model_client: ChatCompletionClient, agent_role: AgentRole = AgentRole.USER, **kwargs):
        # Create deterministic UUID based on discord user id
        hash_value = hashlib.md5(str(user_id).encode()).hexdigest()
        kwargs["agent_id"] = uuid.UUID(hash_value)
        
        self.agent_data = Agent.load(self.get_user_agent_path(user_id))
        
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

    @classmethod
    def load_or_create(cls, user: SimpleUser):
        path = UserAgentWithWallet.get_user_agent_path(user.id)
        if path.exists():
            return cls.from_json(user_id=user.id, path=path)

        user_agent = Agent(
            id=cls.get_user_agent_id(user.id),
            name=''.join(c for c in user.name if c.isalnum()),
            system_message="",
            model_provider=ModelProvider(provider='openai', model='gpt-4o-mini'),
            role=AgentRole.USER,
        )
        user_agent.save(path)
        return cls.from_agent(user_agent, user_id=user.id)
