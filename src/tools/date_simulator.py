from typing import Optional, List, Dict
import os
import dotenv
import pathlib
import argparse
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import TextMessage, AgentEvent, ToolCallRequestEvent, ToolCallExecutionEvent
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient

from src.models.agent_with_wallet import AgentWithWallet
from src.models.model import Agent


dotenv.load_dotenv()

class DateSimulator:

    def __init__(self, model_name: str = "gpt-4o-mini", max_messages: int = 10):
        self.model_name = model_name
        self.max_messages = max_messages
        self.participants: Dict[str, AssistantAgent] = {}
        self.date_organizer: Optional[AssistantAgent] = None
        self.summary_agent: Optional[AssistantAgent] = None
        self.model_client: Optional[OpenAIChatCompletionClient] = None
        self.scene_instruction: str = "Date Organizer, please set the scene and start the date."
        self.is_running: bool = False
        
    def initialize_model_client(self):
        """Initialize the OpenAI model client."""
        self.model_client = OpenAIChatCompletionClient(
            model=self.model_name,
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
    
    def add_participant_from_agent(self, agent: Agent) -> AgentWithWallet:
        """Add a new participant to the date simulation."""
        if not self.model_client:
            raise RuntimeError("Model client not initialized. Call initialize_model_client() first.")
        
        self.participants[agent.name] = AgentWithWallet.from_agent(agent, model_client=self.model_client)
    
    def add_participant(self, name: str, system_message: str) -> AgentWithWallet:
        """Add a new participant to the date simulation."""
        if not self.model_client:
            raise RuntimeError("Model client not initialized. Call initialize_model_client() first.")
            
        agent = AgentWithWallet(
            name=name,
            system_message=system_message,
            model_client=self.model_client,
            reflect_on_tool_use=True
        )
        self.participants[name] = agent
        return agent
        
    def set_date_organizer(self, system_message: Optional[str] = None, wallet_address: Optional[str] = None):
        """Configure the date organizer with optional custom system message."""
        if not self.model_client:
            raise RuntimeError("Model client not initialized. Call initialize_model_client() first.")
        if wallet_address is None:
            raise ValueError("Wallet address is required.")
        if system_message is None:
            system_message = pathlib.Path("prompts/date_organizer.txt").read_text()
        self.date_organizer = AssistantAgent(
            name="DateOrganizer",
            system_message=system_message.format(participants=', '.join(self.participants.keys()), wallet_address=wallet_address),
            model_client=self.model_client,
        )
        
    def set_summarizer(self, system_message: Optional[str] = None):
        """Configure the summary agent with optional custom system message."""
        if not self.model_client:
            raise RuntimeError("Model client not initialized. Call initialize_model_client() first.")
        
        if system_message is None:
            system_message = pathlib.Path("prompts/date_summarizer.txt").read_text()
            
        self.summary_agent = AssistantAgent(
            name="DateSummarizer",
            system_message=system_message,
            model_client=self.model_client,
        )
        
    def set_scene(self, scene_instruction: str):
        """Set the initial scene/prompt for the date."""
        self.scene_instruction = scene_instruction
        
    def _create_selector_prompt(self) -> str:
        """Create the selector prompt for the group chat."""
        return pathlib.Path("prompts/speaker_selector.txt").read_text()
        
    def _format_conversation_history(self, messages: List[TextMessage|AgentEvent]) -> str:
        """Format the conversation history for summary."""
        return "\n\n".join([f"*{msg.source}*: {msg.content}" for msg in messages if isinstance(msg, TextMessage)])
        
    def _format_conversation_history_with_tool_calls(self, messages: List[TextMessage|AgentEvent]) -> str:
        """Format the conversation history for summary."""
        output = []
        for msg in messages:
            if isinstance(msg, TextMessage):
                output.append(f"**{msg.source}**: {msg.content}")
            elif isinstance(msg, ToolCallExecutionEvent):
                for tool_call in msg.content:
                    output.append(f"**{msg.source}** used a tool: {tool_call.content}")
        return "\n\n".join(output)
        
    async def simulate_date(self, scene_instruction: Optional[str] = None) -> TaskResult:
        """Run the date simulation."""
        if not self.model_client:
            raise RuntimeError("Model client not initialized. Call initialize_model_client() first.")
        if not self.date_organizer:
            self.set_date_organizer()
        if len(self.participants) < 2:
            raise ValueError("Need at least 2 participants for a date.")
            
        # Create participant list with date organizer first
        all_participants = [self.date_organizer] + list(self.participants.values())
        
        # Create and run the group chat
        date_conversation = SelectorGroupChat(
            participants=all_participants,
            model_client=self.model_client,
            selector_prompt=self._create_selector_prompt(),
            termination_condition=MaxMessageTermination(self.max_messages)
        )
        self.is_running = True
        stream = date_conversation.run_stream(task=scene_instruction or self.scene_instruction)
        result = await Console(stream)
        self.is_running = False
        return result
        
    async def summarize_date(self, conversation_result: TaskResult):
        """Generate a summary of the date."""
        
        summarizer = AssistantAgent(
            name="DateSummarizer",
            system_message=pathlib.Path("prompts/date_summarizer.txt").read_text(),
            model_client=self.model_client,
        )   
        conversation_history = self._format_conversation_history_with_tool_calls(conversation_result.messages)
        summary_response = await summarizer.on_messages(
            [TextMessage(
                content=f"Please summarize the date between {', '.join(self.participants.keys())}:\n\n{conversation_history}",
                source="user"
            )],
            cancellation_token=CancellationToken(),
        )
        return summary_response.chat_message.content

    def save_conversation(self, result: TaskResult, summary: str):
        # Get next conversation number
        i = 1
        base_path = pathlib.Path("./conversations")
        while any(f.name.startswith(f"{i}_") for f in base_path.glob("*.md")):
            i += 1
            
        # save chat and summary as markdown
        with open(base_path / f"{i}_{'_'.join(self.participants.keys())}.md", "w") as f:
            f.write(f"# Conversation between {'_'.join(self.participants.keys())}\n")
            f.write(self._format_conversation_history_with_tool_calls(result.messages))
            f.write("\n# Summary\n")
            f.write(summary)

async def main(args: argparse.Namespace):
    simulator = DateSimulator()
    simulator.initialize_model_client()
    participants = args.participants.split(",")
    # load participants from json file
    available_participants: list[Agent] = []
    for file in pathlib.Path("agents").glob("*.json"):
        available_participants.append(Agent.load(file))
    for participant in participants:
        for available_participant in available_participants:
            if available_participant.name == participant:
                simulator.add_participant(available_participant.name, available_participant.get_full_system_prompt(num_examples=4))
    result = await simulator.simulate_date()
    summary = await simulator.summarize_date(result)
    print('SUMMARY:\n')
    print(summary)
    simulator.save_conversation(result, summary)

if __name__ == "__main__":
    # run like this:
    # python date_simulator.py --participants "Alice, Bob" --max_messages 10
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--participants", type=str, required=True)
    parser.add_argument("-m", "--max_messages", type=int, required=True)
    args = parser.parse_args()
    
    asyncio.run(main(args))
    
