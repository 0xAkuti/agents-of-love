from typing import Optional
from pydantic import BaseModel
import enum

class MessageContent(BaseModel):
    text: str

class Message(BaseModel):
    user: str
    content: MessageContent

class ModelProvider(BaseModel):
    provider: str
    model: str

class Character(BaseModel):
    bio: list[str]
    lore: list[str]
    knowledge: list[str]
    conversation_examples: list[list[Message]]
    topics: list[str]
    style: list[str]
    adjectives: list[str]
    
class AgentRole(str, enum.Enum):
    MANAGER = "manager"
    ORGANIZER = "organizer"
    PARTICIPANT = "participant"
    SUMMARIZER = "summarizer"
    MATCHMAKER = "matchmaker"
    SPEAKER_SELECTOR = "speaker_selector"
    
    
class Agent(BaseModel):
    name: str
    model_provider: ModelProvider
    role: AgentRole
    system_prompt: Optional[str] = None
    character: Optional[Character] = None
