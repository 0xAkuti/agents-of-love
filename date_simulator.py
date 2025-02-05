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
dotenv.load_dotenv()

class DateSimulator:
    DEFAULT_DATE_ORGANIZER_PROMPT = """You are the date organizer for the date between {participants}, 
    responsible for describing environmental events and setting the scene.
    Your role is to:
    1. Describe random environmental events happening around the participants, such as:
       - Weather changes (light rain starting, sun peeking through clouds)
       - Animals appearing (birds landing nearby, cats walking past)
       - Background activities (street musician starting to play, waiter bringing water)
       - Ambient changes (sunset colors appearing, candles being lit)
    2. Keep descriptions brief and natural, letting them serve as conversation starters
    3. Space out your environmental descriptions to not interrupt the flow
    
    IMPORTANT: Never speak as the date participants.
    Only describe external events happening around them that they might notice and react to."""

    DEFAULT_SUMMARIZER_PROMPT = """You are a perceptive date analyst who notices both obvious and subtle interaction dynamics.
    Your role is to provide an honest, nuanced analysis of interpersonal chemistry and communication patterns.
    
    Focus on:
    - Observe how different conversation styles and worldviews interact
    - Notice moments of both connection and disconnect
    - Analyze how each participant's unique perspective affects the interaction
    - Identify patterns in how they respond to each other's interests
    - Pay attention to shifts in engagement levels throughout the conversation
    
    Provide balanced, insightful observations about the interaction dynamics while maintaining professional objectivity."""

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
        
    def set_date_organizer(self, system_message: Optional[str] = None):
        """Configure the date organizer with optional custom system message."""
        if not self.model_client:
            raise RuntimeError("Model client not initialized. Call initialize_model_client() first.")
            
        self.date_organizer = AssistantAgent(
            name="DateOrganizer",
            system_message=system_message or self.DEFAULT_DATE_ORGANIZER_PROMPT.format(participants=self.participants.keys()),
            model_client=self.model_client,
        )
        
    def set_summarizer(self, system_message: Optional[str] = None):
        """Configure the summary agent with optional custom system message."""
        if not self.model_client:
            raise RuntimeError("Model client not initialized. Call initialize_model_client() first.")
            
        self.summary_agent = AssistantAgent(
            name="DateSummarizer",
            system_message=system_message or self.DEFAULT_SUMMARIZER_PROMPT,
            model_client=self.model_client,
        )
        
    def set_scene(self, scene_instruction: str):
        """Set the initial scene/prompt for the date."""
        self.scene_instruction = scene_instruction
        
    def _create_selector_prompt(self) -> str:
        """Create the selector prompt for the group chat."""
        return """Observe the natural flow of conversation between two people on a date, each with distinct personalities and perspectives.
        Select the next speaker based on realistic conversation dynamics, considering:
        - Natural response patterns
        - Individual communication styles
        - Authentic reactions to previous statements
        
        The DateOrganizer should be selected to:
        - Create environmental context that might influence the interaction
        - Provide natural breaks in conversation
        - Add atmospheric elements that could affect the mood
        
        The following roles are available:
        {roles}.
        Read the following conversation. Then select the next role from {participants} to play. Only return the role.

        {history}

        Read the above conversation. Then select the next role from {participants} to play. Only return the role."""
        
    def _format_conversation_history(self, messages: List[TextMessage]) -> str:
        """Format the conversation history for summary."""
        return "\n".join([f"{msg.source}: {msg.content}" for msg in messages if isinstance(msg, TextMessage)])
        
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