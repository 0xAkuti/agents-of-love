from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from typing import Optional, List, Dict
import os
import dotenv
import pathlib
from src.model import Agent
import argparse
import asyncio
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
        
    def initialize_model_client(self):
        """Initialize the OpenAI model client."""
        self.model_client = OpenAIChatCompletionClient(
            model=self.model_name,
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
        
    def add_participant(self, name: str, system_message: str) -> AssistantAgent:
        """Add a new participant to the date simulation."""
        if not self.model_client:
            raise RuntimeError("Model client not initialized. Call initialize_model_client() first.")
            
        agent = AssistantAgent(
            name=name,
            system_message=system_message,
            model_client=self.model_client,
        )
        self.participants[name] = agent
        return agent
        
    def set_date_organizer(self, system_message: Optional[str]):
        """Configure the date organizer with optional custom system message."""
        if not self.model_client:
            raise RuntimeError("Model client not initialized. Call initialize_model_client() first.")
        
        if system_message is None:
            system_message = pathlib.Path("prompts/date_organizer.txt").read_text()
            
        self.date_organizer = AssistantAgent(
            name="DateOrganizer",
            system_message=system_message.format(participants=self.participants.keys()),
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
        
    def _format_conversation_history(self, messages: List[TextMessage]) -> str:
        """Format the conversation history for summary."""
        return "\n\n".join([f"*{msg.source}*: {msg.content}" for msg in messages if isinstance(msg, TextMessage)])
        
    async def simulate_date(self) -> TaskResult:
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
        
        stream = date_conversation.run_stream(task=self.scene_instruction)
        return await Console(stream)
        
    async def summarize_date(self, conversation_result: TaskResult):
        """Generate a summary of the date."""
        if not self.summary_agent:
            self.set_summarizer()
            
        conversation_history = self._format_conversation_history(conversation_result.messages)
        
        summary_response = await self.summary_agent.on_messages(
            [TextMessage(
                content=f"""Please analyze this date conversation and provide a detailed summary:

Conversation:
{conversation_history}

Focus on:
1. The overall chemistry between the participants
2. Key shared interests or moments of connection
3. Notable reactions or memorable exchanges
4. Overall assessment of the date's success""",
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
            f.write(self._format_conversation_history(result.messages))
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
    
