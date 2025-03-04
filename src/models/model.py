from typing import Optional, List
from pydantic import BaseModel
import enum
import pathlib
import random
import uuid
from pydantic import Field
from src.storage.manager import StorageManager
import asyncio

class StoreableBaseModel(BaseModel):
    async def save_async(self, path: str | pathlib.Path):
        """Save model data asynchronously using storage manager"""
        storage = StorageManager()
        await storage.storage.write_json(str(path), self.model_dump())
    
    def save(self, path: str | pathlib.Path):
        """Synchronous wrapper for save_async"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self.save_async(path))
    
    @classmethod
    async def load_async(cls, path: str | pathlib.Path):
        """Load model data asynchronously using storage manager"""
        storage = StorageManager()
        if await storage.storage.exists(str(path)):
            data = await storage.storage.read_json(str(path))
            return cls.model_validate(data)
        return None
    
    @classmethod
    def load(cls, path: str | pathlib.Path):
        """Synchronous wrapper for load_async"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(cls.load_async(path))
        if result is None:
            # Fall back to legacy file-based loading if async load fails
            with open(path, 'r') as file:
                return cls.model_validate_json(file.read())
        return result

    @classmethod
    def load_from_file(cls, path: str | pathlib.Path):
        with open(path, 'r') as file:
            return cls.model_validate_json(file.read())

class SimpleUser(StoreableBaseModel):
    id: int
    name: str

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
    quotes: Optional[list[str]] = None
    
class AgentRole(str, enum.Enum):
    MANAGER = "manager"
    ORGANIZER = "organizer"
    PARTICIPANT = "participant"
    SUMMARIZER = "summarizer"
    MATCHMAKER = "matchmaker"
    SPEAKER_SELECTOR = "speaker_selector"
    ASSISTANT = "assistant"
    USER = "user"
    
class UserAppearance(StoreableBaseModel):
    hair_color: str
    gender: str
    ethnicity: str
    body_type: str  
    
class UserProfile(StoreableBaseModel):
    name: str
    interests: List[str]
    personality_traits: List[str]
    conversation_style: List[str]
    dislikes: List[str]
    areas_of_expertise_and_knowledge: List[str]
    passionate_topics: List[str]
    appearance: Optional[List[str]] = None
    
class Agent(StoreableBaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    model_provider: ModelProvider
    role: AgentRole
    system_prompt: Optional[str] = None
    character: Optional[Character] = None
    user_profile: Optional[UserProfile] = None

    def _format_list_items(self, items: List[str], num_items: int = 3) -> str:
        """Format a list of items as a bullet-point string, selecting random items."""
        selected_items = random.sample(items, min(num_items, len(items)))
        return "\n".join(f"- {item}" for item in selected_items)
    
    def _format_conversation_examples(self, examples: List[List[Message]], num_examples: int = 2) -> str:
        """Format conversation examples, selecting random examples."""
        if not examples:
            return ""
            
        selected_examples = random.sample(examples, min(num_examples, len(examples)))
        formatted_examples = []
        
        for i, example in enumerate(selected_examples, 1):
            messages = [f"{msg.user}: {msg.content.text}" for msg in example]
            formatted_example = f"Example {i}:\n" + "\n".join(messages)
            formatted_examples.append(formatted_example)
            
        return "\n\n".join(formatted_examples)
    
    def get_full_system_prompt(self, seed: Optional[int] = None, num_examples: int = 10) -> str:
        """Generate a full system prompt using the template and character information."""
        if seed is not None:
            random.seed(seed)
            
        # Determine which template to use
        if self.role == AgentRole.PARTICIPANT and self.character:
            template_path = pathlib.Path("prompts/character_template.txt")
        else:
            template_path = pathlib.Path("prompts/agent_template.txt")
            
        # Load the template
        with open(template_path, "r") as f:
            template = f.read()
            
        # Prepare sections
        sections = {
            "name": self.name,
            "role": self.role.value,
            "system_prompt": self.system_prompt or "",
        }
        
        # Add character information if available and if it's a participant
        if self.role == AgentRole.PARTICIPANT and self.character:
            sections.update({
                "bio_section": self._format_list_items(self.character.bio, num_examples),
                "lore_section": self._format_list_items(self.character.lore, num_examples),
                "knowledge_section": self._format_list_items(self.character.knowledge, num_examples),
                "style_section": "\n".join(f"- {item}" for item in self.character.style),
                "adjectives_section": "\n".join(f"- {item}" for item in self.character.adjectives),
                "topics_section": self._format_list_items(self.character.topics, num_examples),
                "conversation_examples": self._format_conversation_examples(self.character.conversation_examples, num_examples),
                "quotes_section": self._format_list_items(self.character.quotes, num_examples) if self.character.quotes else ""
            })
            
        # Format the template
        return template.format(**sections)
