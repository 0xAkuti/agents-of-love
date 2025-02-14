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

class WalletProvider(enum.Enum):
    CDP = "cdp"
    STARKNET = "starknet"

	
dotenv.load_dotenv(override=True)

class AgentWithWallet(AssistantAgent):
    _wallet_store = WalletStore()

    def __init__(self, name: str, system_message: str, model_client: ChatCompletionClient, agent_id: str | uuid.UUID | None = None, agent_role: AgentRole = AgentRole.ASSISTANT, wallet_provider: WalletProvider = WalletProvider.CDP, **kwargs):
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
        if "starknet" in self.network_id:
            self.wallet_provider = WalletProvider.STARKNET
            print('USING STARKNET')
        else:
            self.wallet_provider = WalletProvider.CDP
            print('USING CDP')
        self.wallet_data = self._wallet_store.load_wallet(str(self.agent_id))
        # self.wallet_provider = wallet_provider
        self.cdp_agentkit = CdpAgentkitWrapper(
            network_id="base-sepolia",
            cdp_wallet_data=json.dumps(self.wallet_data.to_dict()) if self.wallet_data else None
        )
        if self.wallet_provider == WalletProvider.CDP:
            self.cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(self.cdp_agentkit)
            tools = [CDPLangChainToolAdapter(tool) for tool in self.cdp_toolkit.get_tools()]
            limited_tools = []
            transfer_tool = None
            for tool in tools:
                if tool.name == 'transfer':
                    transfer_tool = tool
                elif tool.name in ["get_balance", "get_wallet_details"]:
                    limited_tools.append(tool)
            tools = limited_tools
            def transfer_usdc(amount: str, destination: str):
                """Transfers amount of USDC to a given wallet address in hexadecimal format"""
                return transfer_tool._langchain_tool({"amount": amount, "asset_id": "usdc", "destination": destination})
            tools.append(transfer_usdc)
        elif self.wallet_provider == WalletProvider.STARKNET:
            self.starknet_toolkit = StarknetToolkit(self.wallet_data.seed)
            tools = self.starknet_toolkit.get_tools()

        tools.extend(kwargs.pop("tools", []))
        super().__init__(
            name=name,
            system_message=system_message,
            model_client=model_client,
            tools=tools,
            **kwargs
        )
        self._save_agent(name, system_message)
        if self.wallet_data is None:
            self._wallet_store.save_wallet(str(self.agent_id), self.cdp_agentkit.wallet)
        logging.info(f"Agent {name!r} with ID {self.agent_id} created, wallet: {self.cdp_agentkit.wallet.default_address.address_id}")
        
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
    
    def get_address(self) -> str:
        if self.wallet_provider == WalletProvider.CDP:
            return self.cdp_agentkit.wallet.default_address.address_id
        elif self.wallet_provider == WalletProvider.STARKNET:
            return self.starknet_toolkit.get_address()
        else:
            raise ValueError(f"Unsupported wallet provider: {self.wallet_provider}")
