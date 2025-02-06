import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from date_simulator import DateSimulator
from src.model import Agent, AgentRole, StoreableBaseModel
import os
import pathlib
import dotenv

dotenv.load_dotenv()

class UserProfile(StoreableBaseModel):
    name: str
    interests: List[str]
    personality_traits: List[str]
    conversation_style: List[str]
    dislikes: List[str]

class DateManager:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.model_client = OpenAIChatCompletionClient(
            model=model_name,
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
        
        # Load agent templates
        self.manager_template = Agent.load(pathlib.Path("agents/date_manager.json"))
        self.organizer_template = Agent.load(pathlib.Path("agents/date_organizer.json"))
        self.summarizer_template = Agent.load(pathlib.Path("agents/date_summarizer.json"))
        
        # Load available participants
        self.available_participants = self._load_available_participants()
        
        # Create the date manager agent
        self.manager_agent = AssistantAgent(
            name=self.manager_template.name,
            system_message=self.manager_template.system_prompt,
            model_client=self.model_client,
            tools=[self.create_user_profile, self.list_available_participants, self.run_simulation]
        )
        
        self.user_profile: Optional[UserProfile] = None
        self.simulator: Optional[DateSimulator] = None
        
    def _load_available_participants(self) -> Dict[str, Agent]:
        """Load all available participant agents from the agents folder."""
        participants = {}
        agents_path = pathlib.Path("agents")
        for file in agents_path.glob("*.json"):
            agent = Agent.load(file)
            if agent.role == AgentRole.PARTICIPANT:
                participants[agent.name] = agent
        return participants
        
    async def list_available_participants(self) -> str:
        """List all available participants with their brief descriptions."""
        if not self.available_participants:
            return "No participants available for dating."
                
        return "Available participants for dating:\n" + ",".join(self.available_participants.keys())
        
    def generate_system_prompt(self, profile: UserProfile) -> str:
        """Generate a system prompt based on the user's profile."""
        prompt = f"""You are {profile.name}, a person with distinct interests and personality traits.
        
        Your passions and interests include:
        {', '.join(profile.interests)}
        
        Key personality traits:
        {', '.join(profile.personality_traits)}
        
        Conversation style:
        {', '.join(profile.conversation_style)}
        
        Things you tend to dislike or avoid:
        {', '.join(profile.dislikes)}
        
        Remember to:
        - Stay true to your interests and personality
        - React authentically to topics you like or dislike
        - Maintain your unique conversation style
        - Show genuine enthusiasm for your interests
        - Naturally steer away from topics you dislike
        
        Keep your responses natural while staying true to your character."""
        
        return prompt
        
    async def run_date_simulation(self, user_prompt: str, match_name: str) -> str:
        """Run a date simulation with the user's character and their match."""
        if match_name not in self.available_participants:
            return f"Error: {match_name} is not available for dating."
            
        match_agent = self.available_participants[match_name]
        match_prompt = match_agent.get_full_system_prompt(num_examples=4)
        
        self.simulator = DateSimulator(max_messages=10)
        self.simulator.initialize_model_client()
        
        # Create date organizer from template
        self.simulator.set_date_organizer(self.organizer_template.system_prompt)
        
        # Add the participants
        self.simulator.add_participant(self.user_profile.name, user_prompt)
        self.simulator.add_participant(match_name, match_prompt)
        
        # Set the summarizer from template
        self.simulator.set_summarizer(self.summarizer_template.system_prompt)
        
        # Run the simulation
        result = await self.simulator.simulate_date()
        summary = await self.simulator.summarize_date(result)
        self.simulator.save_conversation(result, summary)
        return summary
        
    async def create_user_profile(self, name: str, interests: List[str], personality_traits: List[str], conversation_style: List[str], dislikes: List[str]):
        """Create a user profile from the collected data as a python dict and without any markdown formatting."""
        self.user_profile = UserProfile(name=name, interests=interests, personality_traits=personality_traits, conversation_style=conversation_style, dislikes=dislikes)
        return f"Created profile for {self.user_profile.name}"
        
    async def run_simulation(self, match_name: str) -> str:
        """Run a date simulation with the specified match."""
        if not self.user_profile:
            return "Error: User profile not created yet. Please provide user information first."
            
        user_prompt = self.generate_system_prompt(self.user_profile)
        summary = await self.run_date_simulation(user_prompt, match_name)
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
