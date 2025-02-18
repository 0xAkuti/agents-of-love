import logging
import os
import pathlib
import uuid
import json
import hashlib
import dotenv
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils.cdp_agentkit_wrapper import CdpAgentkitWrapper

from src.models.model import Agent, ModelProvider, AgentRole
from src.server.wallet_store import WalletStore
from src.tools.cdp_landchain_adapter import CDPLangChainToolAdapter
import enum

from src.tools.starknet_toolkit import StarknetToolkit
from src.storage.manager import StorageManager

class WalletProvider(enum.Enum):
    CDP = "cdp"
    STARKNET = "starknet"

	
dotenv.load_dotenv(override=True)

class AgentWithWallet(AssistantAgent):
    def __init__(self, name: str, system_message: str, model_client: ChatCompletionClient, agent_id: str | uuid.UUID | None = None, agent_role: AgentRole = AgentRole.ASSISTANT, wallet_provider: WalletProvider = WalletProvider.CDP, **kwargs):
        if agent_id is None:
            # Create deterministic UUID based on hash of name and system message
            combined = f"{name}{system_message}".encode()
            hash_value = hashlib.md5(combined).hexdigest()
            self.agent_id = uuid.UUID(hash_value)
        elif isinstance(agent_id, str):
            self.agent_id = uuid.UUID(agent_id)
        else:
            self.agent_id = agent_id
            
        self.agent_role = agent_role
        self.network_id = os.environ.get("NETWORK_ID", "base-sepolia")
        if "starknet" in self.network_id:
            self.wallet_provider = WalletProvider.STARKNET
            print('USING STARKNET')
        else:
            self.wallet_provider = WalletProvider.CDP
            print('USING CDP')
        
        self.storage_manager = StorageManager()
        self.wallet_store = WalletStore()
        
        # Load wallet data synchronously for initialization
        self.wallet_data = self.wallet_store.load_wallet_sync(str(self.agent_id))
        
        # Initialize CDP agentkit
        if self.wallet_data is None:
            # only create wallet if it doesn't exist yet
            self.cdp_agentkit = CdpAgentkitWrapper(
                network_id="base-sepolia",
                cdp_wallet_data=json.dumps(self.wallet_data.to_dict()) if self.wallet_data else None
            )
        
        # Initialize tools list
        tools = kwargs.pop("tools", [])
        
        # Initialize appropriate toolkit and tools
        if self.wallet_provider == WalletProvider.CDP:
            self.cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(self.cdp_agentkit)
            wallet_tools = [CDPLangChainToolAdapter(tool) for tool in self.cdp_toolkit.get_tools()]
            limited_tools = []
            transfer_tool = None
            for tool in wallet_tools:
                if tool.name == 'transfer':
                    transfer_tool = tool
                elif tool.name in ["get_balance", "get_wallet_details"]:
                    limited_tools.append(tool)
            tools.extend(limited_tools)
            if transfer_tool:
                def transfer_usdc(amount: str, destination: str):
                    """Transfers amount of USDC to a given wallet address in hexadecimal format"""
                    return transfer_tool._langchain_tool({"amount": amount, "asset_id": "usdc", "destination": destination})
                tools.append(transfer_usdc)
        elif self.wallet_provider == WalletProvider.STARKNET and self.wallet_data:
            self.starknet_toolkit = StarknetToolkit(self.wallet_data.seed)
            tools.extend(self.starknet_toolkit.get_tools())
        
        self.agent_data = Agent(
            id=self.agent_id,
            name=name,
            model_provider=ModelProvider(
                provider="openai",
                model="gpt-4o-mini"
            ),
            role=self.agent_role,
            system_prompt=system_message
        )
        
        super().__init__(
            name=name,
            system_message=system_message,
            model_client=model_client,
            tools=tools,
            **kwargs
        )
        
    async def initialize(self):
        """Initialize remaining async operations"""
        # Save wallet if it doesn't exist
        if self.wallet_data is None and self.cdp_agentkit.wallet:
            await self.wallet_store.save_wallet(str(self.agent_id), self.cdp_agentkit.wallet)
            logging.info(f"Agent {self.name!r} with ID {self.agent_id} created, wallet: {self.cdp_agentkit.wallet.default_address.address_id}")
        
        await self.storage_manager.save_user_agent(self.agent_id, self.agent_data.model_dump(mode="json"))
        
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
    async def from_agent(cls, agent: Agent, **kwargs):
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
        
        instance = cls(
            name=name,
            system_message=system_message,
            model_client=model_client,
            agent_id=agent_id,
            **kwargs
        )
        await instance.initialize()
        return instance
    
    @classmethod
    async def from_json(cls, path: str, **kwargs):
        with open(path, "r") as f:
            agent = Agent.model_validate_json(f.read())
        return await cls.from_agent(agent, **kwargs)

    def get_wallet(self):
        return self.cdp_agentkit.wallet if self.cdp_agentkit else None
    
    def get_address(self) -> str:
        if self.wallet_provider == WalletProvider.CDP:
            return self.cdp_agentkit.wallet.default_address.address_id if self.cdp_agentkit else None
        elif self.wallet_provider == WalletProvider.STARKNET:
            return self.starknet_toolkit.get_address() if self.starknet_toolkit else None
        else:
            raise ValueError(f"Unsupported wallet provider: {self.wallet_provider}")
