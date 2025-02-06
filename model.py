from typing import Optional
from pydantic import BaseModel
import enum
import pathlib
class StoreableBaseModel(BaseModel):
    def save(self, path: str | pathlib.Path):
        with open(path, 'w') as file:
            file.write(self.model_dump_json())
    
    @classmethod
    def load(cls, path: str | pathlib.Path):
        with open(path, 'r') as file:
            return cls.model_validate_json(file.read())

class MessageContent(StoreableBaseModel):
    text: str

class Message(StoreableBaseModel):
    user: str
    content: MessageContent

class ModelProvider(StoreableBaseModel):
    provider: str
    model: str

class Character(StoreableBaseModel):
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
    
    
class Agent(StoreableBaseModel):
    name: str
    model_provider: ModelProvider
    role: AgentRole
    system_prompt: Optional[str] = None
    character: Optional[Character] = None
