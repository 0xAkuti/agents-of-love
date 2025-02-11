from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.memory import ListMemory
from autogen_agentchat.agents import AssistantAgent
from src.model import UserProfile
class PromptGenerator:
    def __init__(self, model_client: OpenAIChatCompletionClient):
        self.model_client = model_client
        
        system_message = """You are an expert at generating prompts for image generation. Your task is to analyze date conversations and generate a prompt for a memorable photo that the participants might have taken during their date.
If there is a photo happening in the conversation, use that as the basis for the prompt.

The prompt should:
1. Be detailed and but not too long (max 1000 characters)
2. Capture a specific moment or scene from the date
3. Include the physical descriptions of the participants if available and full names if available
4. Set the mood and atmosphere of the scene
5. Be suitable for generating a high-quality image

Focus on creating prompts that would make meaningful NFT memories of the date.
ALWAYS KEEP THE PROMPT SHORT AND TO THE POINT"""

        self.agent = AssistantAgent(
            name="prompt_generator",
            system_message=system_message,
            model_client=self.model_client
        )
    
    async def generate_prompt(self, conversation: str, user: UserProfile) -> str:
        """Generate an image prompt from a date conversation."""
        
        conversation = conversation.replace("Bruce", "Bruce Lee")
        conversation = conversation.replace("Arnold", "Arnold Schwarzenegger")
        conversation = conversation.replace("Trump", "Donald Trump")
        conversation = conversation.replace("Tesla", "Nikola Tesla")
        
        message = f"""Based on this date conversation, generate a prompt for an image that captures a memorable moment from the date.

Conversation:
{conversation}

Here is more information about {user.name}:
{user.appearance}
Make sure to include the appearance of {user.name} in the prompt.

Generate a detailed image prompt that captures a special moment from this date."""

        response = await self.agent.on_messages(
            [TextMessage(content=message, source="user")],
            cancellation_token=CancellationToken()
        )
        
        return response.chat_message.content 