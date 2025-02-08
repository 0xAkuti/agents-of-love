import asyncio
from typing import Callable, List, Optional, Dict, Any
from pydantic import BaseModel
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from date_simulator import DateSimulator
from src.model import Agent, AgentRole, StoreableBaseModel, UserProfile
from src.agent_with_wallet import AgentWithWallet
import os
import pathlib
import dotenv
import discord

from src.user_agent import UserAgentWithWallet
dotenv.load_dotenv()



class DateManager:
    def __init__(self, model_name: str = "gpt-4o-mini", user: Optional[discord.User] = None):
        self.model_name = model_name
        self.user = user
        self.model_client = OpenAIChatCompletionClient(
            model=model_name,
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
        
        # Load agent templates
        self.manager_template = pathlib.Path("prompts/date_manager.txt").read_text() # Agent.load(pathlib.Path("agents/date_manager.json"))
        self.organizer_template = pathlib.Path("prompts/date_organizer.txt").read_text() #Agent.load(pathlib.Path("agents/date_organizer.json"))
        self.summarizer_template = pathlib.Path("prompts/date_summarizer.txt").read_text() #Agent.load(pathlib.Path("agents/date_summarizer.json"))
        
        # Load available participants
        self.available_participants = self._load_available_participants()
        
        if user:
            print(f"Loading user agent for {user.name} ({user.id})")
            self.user_agent = UserAgentWithWallet.load_or_create(user)
        else:
            raise ValueError("User is required for now")
        
        self.manager_agent = AgentWithWallet.from_json(
            path=pathlib.Path("agents/date_manager.json"),
            system_message=self.manager_template,
            tools=[self.create_user_profile, self.list_available_participants, self.run_simulation, self.get_user_agent_wallet],
            reflect_on_tool_use=True
        )

        self.simulator: Optional[DateSimulator] = None
        self.date_started_callback: Optional[Callable[[], None]] = None
           
    def _load_available_participants(self) -> Dict[str, Agent]:
        """Load all available participant agents from the agents folder."""
        participants = {}
        agents_path = pathlib.Path("agents")
        for file in agents_path.glob("*.json"):
            agent = Agent.load(file)
            if agent.role == AgentRole.PARTICIPANT:
                participants[agent.name] = agent
        return participants
    
    async def get_user_agent_wallet(self) -> str:
        """Get the wallt address of the users agent."""
        if self.user_agent is None:
            return "User agent not found"
        return self.user_agent.cdp_agentkit.wallet.default_address.address_id
        
    async def list_available_participants(self) -> str:
        """List all available participants with their brief descriptions."""
        if not self.available_participants:
            return "No participants available for dating."
        
        available_participants = [f"{p.name}: {p.system_prompt}" for p in self.available_participants.values()]
                
        return "Available participants for dating:\n" + "\n".join(available_participants)
        
    async def run_date_simulation(self, user_prompt: str, match_name: str, scene_instruction: Optional[str] = None) -> str:
        """Run a date simulation with the user's character and their match.
        
        Keep in mind that you need to save the user profile first.
        """
        if match_name not in self.available_participants:
            return f"Error: {match_name} is not available for dating."
        if self.user_agent is None:
            return "Error: User agent not found"
            
        match_agent = self.available_participants[match_name]
        # match_prompt = match_agent.get_full_system_prompt(num_examples=4)
        
        self.simulator = DateSimulator(max_messages=6)
        self.simulator.model_name = self.model_name
        self.simulator.initialize_model_client()
        
        # Create date organizer from template
        self.simulator.set_date_organizer(self.organizer_template)
        
        # Add the participants
        #self.simulator.add_participant(self.user_profile.name, user_prompt)
        #self.simulator.add_participant(match_name, match_prompt)
        
        self.simulator.participants.append(self.user_agent)
        self.simulator.add_participant_from_agent(match_agent)
        
        # Set the summarizer from template
        self.simulator.set_summarizer(self.summarizer_template)
        
        # Run the simulation
        result = await self.simulator.simulate_date(scene_instruction)
        conversation = self.simulator._format_conversation_history(result.messages)
        summary = await self.simulator.summarize_date(result)
        self.simulator.save_conversation(result, summary)
        return conversation
        
    async def create_user_profile(self, name: str, interests: List[str], personality_traits: List[str], conversation_style: List[str], dislikes: List[str], areas_of_expertise_and_knowledge: List[str], passionate_topics: List[str]):
        """Create or udpate a user profile from the collected data, call without any markdown formatting."""
        if self.user_agent is None:
            raise ValueError("User agent not found")
        path = UserAgentWithWallet.get_user_agent_path(self.user.id)
        user_agent = Agent.load(path)
        user_agent.name = name
        if user_agent.user_profile is None:
            user_agent.user_profile = UserProfile(name=name, interests=interests, personality_traits=personality_traits, conversation_style=conversation_style, dislikes=dislikes, areas_of_expertise_and_knowledge=areas_of_expertise_and_knowledge, passionate_topics=passionate_topics)
        else:
            user_agent.user_profile.interests = interests
            user_agent.user_profile.personality_traits = personality_traits
            user_agent.user_profile.conversation_style = conversation_style
            user_agent.user_profile.dislikes = dislikes
            user_agent.user_profile.areas_of_expertise_and_knowledge = areas_of_expertise_and_knowledge
            user_agent.user_profile.passionate_topics = passionate_topics
        user_agent.save(path)

        return f"Updated profile for {user_agent.user_profile.name}"
        
    async def run_simulation(self, match_name: str, scene_instruction: Optional[str] = None) -> str:
        """Run a date simulation with the specified match.
        If the user has not specified a scene instruction, the simulator will use the default one.
        Otherwise please provide a scene instruction to the date organizer."""
        if not self.user_profile:
            return "Error: User profile not created yet. Please provide user information first."
            
        user_prompt = self.generate_system_prompt(self.user_profile)
        summary = await self.run_date_simulation(user_prompt, match_name, scene_instruction)
        return summary
        
    async def get_manager_response(self, user_input: str) -> str:
        """Get a response from the manager agent."""
        response = await self.manager_agent.on_messages(
            [TextMessage(content=user_input, source="user")],
            cancellation_token=CancellationToken(),
        )
        return response.chat_message.content
        
    async def start_conversation(self):
        """Start the conversation with the user to collect information and run the date."""
        print("""Hi! I'm your date manager. I'll help you set up and run a date simulation.
        I'd like to know about your:
        - Name
        - Interests and hobbies
        - Personality traits
        - Conversation style
        - Things you tend to dislike or avoid
        
        Let's start! What's your name and tell me a bit about yourself?
        (Type 'exit' to end the conversation)
        """)
        
        while True:
            # Get user input
            user_input = input("\nYou: ").strip()
            if user_input.lower() == 'exit':
                print("\nGoodbye!")
                break
                
            # Get manager's response
            manager_response = await self.get_manager_response(user_input)
            print(f"\nDate Manager: {manager_response}")

async def main():
    manager = DateManager()
    await manager.start_conversation()

if __name__ == "__main__":
    asyncio.run(main())
