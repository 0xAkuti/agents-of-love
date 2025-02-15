import pathlib

from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent

from src.models.model import UserProfile

class PromptGenerator:
    def __init__(self, model_client: OpenAIChatCompletionClient):
        self.model_client = model_client
        
        system_message = pathlib.Path("prompts/prompt_generator.txt").read_text()

        self.agent = AssistantAgent(
            name="prompt_generator",
            system_message=system_message,
            model_client=self.model_client
        )
    
    @staticmethod
    def _fix_full_name(conversation: str) -> str:
        names = {'Bruce': 'Bruce Lee', 'Arnold': 'Arnold Schwarzenegger', 'Trump': 'Donald Trump', 'Tesla': 'Nikola Tesla'}
        for short_name, full_name in names.items():
            conversation = conversation.replace(full_name, short_name) # first replace full name with short name to prevent double names in the prompt
            conversation = conversation.replace(short_name, full_name) # then replace short name with full name
        return conversation
    
    async def generate_prompt(self, conversation: str, user: UserProfile) -> str:
        """Generate an image prompt from a date conversation."""
        
        conversation = self._fix_full_name(conversation)
        
        message = f"""
        Based on this date conversation, create a prompt for generating a photo that was taken during the date.

        Conversation:
        {conversation}

        Here is more information about {user.name}:
        {user.appearance}
        """

        response = await self.agent.on_messages(
            [TextMessage(content=message, source="user")],
            cancellation_token=CancellationToken()
        )
        
        return response.chat_message.content 