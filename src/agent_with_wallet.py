import os
from autogen_agentchat.agents import AssistantAgent
from src.model import Agent
from cdp_langchain.agent_toolkits import CdpToolkit
from src.cdp_landchain_adapter import CDPLangChainToolAdapter
from cdp_langchain.utils.cdp_agentkit_wrapper import CdpAgentkitWrapper
import dotenv
import functools
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient

dotenv.load_dotenv(override=True)

class AgentWithWallet(AssistantAgent):
    @functools.wraps(AssistantAgent.__init__)
    def __init__(self, name: str, system_message: str, model_client: ChatCompletionClient, **kwargs):
        self.cdp_agentkit = CdpAgentkitWrapper(
            network_id=os.environ.get("NETWORK_ID") # default to base-sepolia
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
        
    @classmethod
    def from_agent(cls, agent: Agent, **kwargs):
        if agent.model_provider.provider == "openai":
            model_client = OpenAIChatCompletionClient(
                model=agent.model_provider.model,
                api_key=os.environ.get("OPENAI_API_KEY"),
            )
        else:
            raise ValueError(f"Unsupported model provider: {agent.model_provider.provider}")
        
        return cls(
            name=agent.name,
            system_message=agent.get_full_system_prompt(),
            model_client=model_client,
            **kwargs
        )
    
    @classmethod
    def from_json(cls, path: str, **kwargs):
        with open(path, "r") as f:
            agent = Agent.model_validate_json(f.read())
        return cls.from_agent(agent, **kwargs)

    def get_wallet(self):
        return self.cdp_agentkit.wallet