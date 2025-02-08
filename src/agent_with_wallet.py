import os
import pathlib
import uuid
import json
from autogen_agentchat.agents import AssistantAgent
from src.model import Agent, ModelProvider, AgentRole
from cdp_langchain.agent_toolkits import CdpToolkit
from src.cdp_landchain_adapter import CDPLangChainToolAdapter
from cdp_langchain.utils.cdp_agentkit_wrapper import CdpAgentkitWrapper
from src.wallet_store import WalletStore
import dotenv
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from cdp.wallet import Wallet
import hashlib

	
dotenv.load_dotenv(override=True)

class AgentWithWallet(AssistantAgent):
    _wallet_store = WalletStore()

    def __init__(self, name: str, system_message: str, model_client: ChatCompletionClient, agent_id: str | uuid.UUID | None = None, agent_role: AgentRole = AgentRole.ASSISTANT, **kwargs):
        if agent_id is None:
            # Create deterministic UUID based on hash of name and system message
            combined = f"{name}{system_message}".encode()
            hash_value = hashlib.md5(combined).hexdigest()
            self.agent_id = uuid.UUID(hash_value)
        elif isinstance(agent_id, str):
            self.agent_id = uuid.UUID(agent_id)
        else:
            self.agent_id = agent_id#
        self.agent_role = agent_role
        self.network_id = os.environ.get("NETWORK_ID", "base-sepolia")
        wallet_data = self._wallet_store.load_wallet(str(self.agent_id))
        self.cdp_agentkit = CdpAgentkitWrapper(
            network_id=self.network_id,
            cdp_wallet_data=json.dumps(wallet_data.to_dict()) if wallet_data else None
        )
        self.cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(self.cdp_agentkit)
        tools = [CDPLangChainToolAdapter(tool) for tool in self.cdp_toolkit.get_tools()]
        tools.extend(kwargs.get("tools", []))
        super().__init__(
            name=name,
            system_message=system_message,
            model_client=model_client,
            tools=tools,
            **kwargs
        )
        self._save_agent(name, system_message)
        if wallet_data is None:
            self._wallet_store.save_wallet(str(self.agent_id), self.cdp_agentkit.wallet)
        
    def _save_agent(self, name: str, system_message: str):
        for agent_file in pathlib.Path(".").glob("agents/**/*.json"):
            agent = Agent.model_validate_json(agent_file.read_text())
            if agent.id == self.agent_id:
                return False
        Agent(
            id=self.agent_id,
            name=name,
            model_provider=ModelProvider(
                provider="openai",
                model="gpt-4o-mini"
            ),
            role=self.agent_role,
            system_prompt=system_message
        ).save(f'agents/generated/{name}_{self.agent_id}.json')
        return True

    @classmethod
    def from_agent(cls, agent: Agent, **kwargs):
        if agent.model_provider.provider == "openai":
            model_client = OpenAIChatCompletionClient(
                model=agent.model_provider.model,
                api_key=os.environ.get("OPENAI_API_KEY"),
            )
        else:
            raise ValueError(f"Unsupported model provider: {agent.model_provider.provider}")
        
        name = kwargs.pop("name", agent.name)
        system_message = kwargs.pop("system_message", agent.get_full_system_prompt())
        model_client = kwargs.pop("model_client", model_client)
        agent_id = kwargs.pop("agent_id", agent.id)
        
        return cls(
            name=name,
            system_message=system_message,
            model_client=model_client,
            agent_id=agent_id,
            **kwargs
        )
    
    @classmethod
    def from_json(cls, path: str, **kwargs):
        with open(path, "r") as f:
            agent = Agent.model_validate_json(f.read())
        return cls.from_agent(agent, **kwargs)

    def get_wallet(self):
        return self.cdp_agentkit.wallet
