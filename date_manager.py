import asyncio
import logging
from typing import Callable, List, Optional, Dict, Any
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from date_simulator import DateSimulator
from src.model import Agent, AgentRole, UserProfile, SimpleUser
from src.agent_with_wallet import AgentWithWallet
import os
import pathlib
import dotenv
import discord
import json
from autogen_core.memory import ListMemory, MemoryContent, MemoryMimeType
from src.leonardo_image import LeonardoImageTool, LeonardoRequest
from src.prompt_generator import PromptGenerator
from src.token_registry import TokenRegistry

from src.user_agent import UserAgentWithWallet
dotenv.load_dotenv()



class DateManager:
    def __init__(self, model_name: str = "gpt-4o-mini", user: Optional[SimpleUser] = None):
        self.model_name = model_name
        self.user = user
        self.model_client = OpenAIChatCompletionClient(
            model=model_name,
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
        
        # Create states directory if it doesn't exist
        self.states_dir = pathlib.Path("states")
        self.states_dir.mkdir(exist_ok=True)
        
        # Load agent templates
        self.manager_template = pathlib.Path("prompts/date_manager.txt").read_text() # Agent.load(pathlib.Path("agents/date_manager.json"))
        self.organizer_template = pathlib.Path("prompts/date_organizer.txt").read_text() #Agent.load(pathlib.Path("agents/date_organizer.json"))
        self.summarizer_template = pathlib.Path("prompts/date_summarizer.txt").read_text() #Agent.load(pathlib.Path("agents/date_summarizer.json"))
        
        # Load available participants
        self.available_participants = self._load_available_participants()
        
        if user:
            print(f"Loading user avatar for {user.name} ({user.id})")
            self.user_agent = UserAgentWithWallet.load_or_create(user)
        else:
            raise ValueError("User is required for now")
            
        # Create memory for storing user profile
        self.memory = ListMemory()
        self.prompt_generator = PromptGenerator(self.model_client)
        self.token_registry = TokenRegistry()
        self.image_tool = LeonardoImageTool()
        
        self.manager_agent = AgentWithWallet.from_json(
            path=pathlib.Path("agents/date_manager.json"),
            system_message=self.manager_template,
            tools=[self.image_tool, 
                   self.create_user_avatar, 
                   self.list_available_participants, 
                   self.run_date_simulation, 
                   self.get_user_avatar_wallet, 
                   self.get_user_avatar_balance,
                   self.mint_date_nft],
            reflect_on_tool_use=True,
            memory=[self.memory]
        )

        self.simulator: Optional[DateSimulator] = None
        self.date_started_callback: Optional[Callable[[], None]] = None
    
    def _get_state_path(self) -> pathlib.Path:
        """Get the path to the state file for the current user."""
        if not self.user:
            raise ValueError("No user set")
        return self.states_dir / f"{self.user.id}_state.json"

    async def save_state(self):
        """Save the current state of the date manager."""
        if not self.user:
            return
            
        # Get state from manager agent
        manager_state = await self.manager_agent.save_state()
        
        # Get memory contents - ListMemory has a contents property, not get_contents()
        memory_contents = []
        for content in self.memory.content:
            memory_contents.append({
                "content": content.content,
                "mime_type": content.mime_type.value
            })
        
        # Combine states
        state = {
            "manager_state": manager_state,
            "memory_contents": memory_contents
        }
        
        # Save to file
        state_path = self._get_state_path()
        with open(state_path, "w") as f:
            json.dump(state, f)
            
    async def _load_state(self) -> bool:
        """Load the previous state if it exists and returns whether it was loaded successfully."""
        state_path = self._get_state_path()
        if not state_path.exists():
            return False
            
        try:
            # Read the file content first
            with open(state_path, "r", encoding='utf-8') as f:
                file_content = f.read()
                
            try:
                state = json.loads(file_content)
            except json.JSONDecodeError as e:
                # If JSON is invalid, log the error and save the problematic file
                error_path = state_path.with_suffix('.error')
                with open(error_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                print(f"Error parsing state file: {e}")
                print(f"Saved problematic state to: {error_path}")
                # Delete the corrupted state file
                state_path.unlink()
                return False
                
            # Load manager state
            if "manager_state" in state:
                try:
                    await self.manager_agent.load_state(state["manager_state"])
                except Exception as e:
                    print(f"Error loading manager state: {e}")
                
            # Load memory contents    
            if "memory_contents" in state:
                for content in state["memory_contents"]:
                    try:
                        mime_type = content.get("mime_type")
                        # Convert string mime type to enum if needed
                        if isinstance(mime_type, str):
                            mime_type = MemoryMimeType(mime_type)
                        await self.memory.add(MemoryContent(
                            content=content["content"],
                            mime_type=mime_type
                        ))
                    except Exception as e:
                        print(f"Error loading memory content: {e}")
            return True
                
        except Exception as e:
            print(f"Error loading state: {e}")
            # Save the problematic state file for debugging
            error_path = state_path.with_suffix('.error')
            try:
                state_path.rename(error_path)
                print(f"Moved problematic state to: {error_path}")
            except Exception as rename_error:
                print(f"Could not save problematic state: {rename_error}")
            return False
    
    async def init_memory(self):
        """Initialize the date manager."""
        if await self._load_state():
            return
            
        if self.user_agent.agent_data.user_profile:
            # Create the profile JSON
            profile_json = json.dumps(self.user_agent.agent_data.user_profile.model_dump(), indent=2)
            
            # Query for the exact profile content
            query_result = await self.memory.query(profile_json)
            
            # Only add if profile doesn't exist (check query_result.results)
            if not query_result.results:
                await self.memory.add(
                    MemoryContent(
                        content=profile_json,
                        mime_type=MemoryMimeType.JSON
                    )
                )
    
    def _load_available_participants(self) -> Dict[str, Agent]:
        """Load all available participant agents from the agents folder."""
        participants = {}
        agents_path = pathlib.Path("agents")
        for file in agents_path.glob("*.json"):
            agent = Agent.load(file)
            if agent.role == AgentRole.PARTICIPANT:
                participants[agent.name] = agent
        return participants
    
    async def get_user_avatar_wallet(self) -> str:
        """Get the wallt address of the users avatar."""
        if self.user_agent is None:
            return "User avatar not found"
        return self.user_agent.cdp_agentkit.wallet.default_address.address_id
    
    async def get_user_avatar_balance(self, asset_id: str) -> str:
        """Get balance for all addresses in the wallet of the users avatar for a given asset.

        Args:
            asset_id (str): The asset ID to get the balance for (e.g., "eth", "usdc", or a valid contract address like "0x036CbD53842c5426634e7929541eC2318f3dCF7e")

        Returns:
            str: A message containing the balance information of all addresses in the wallet.

        """
        if self.user_agent is None:
            return "User avatar not found"
        for tool in self.user_agent.cdp_toolkit.get_tools():
            if tool.name == "get_balance":
                return await tool.arun({"asset_id": asset_id})
        return "No balance tool found"
        
    async def list_available_participants(self) -> str:
        """List all available participants with their brief descriptions."""
        if not self.available_participants:
            return "No participants available for dating."
        
        available_participants = [f"{p.name}: {p.system_prompt}" for p in self.available_participants.values()]
                
        return "Available participants for dating:\n" + "\n".join(available_participants)
        
    async def run_date_simulation(self,  match_name: str, scene_instruction: Optional[str] = None) -> str:
        """Run a date simulation with the specified match.
        If the user has not specified a scene instruction, the simulator will use the default one.
        Otherwise please provide a scene instruction to the date organizer."""
    
        if match_name not in self.available_participants:
            return f"Error: {match_name} is not available for dating."
        if self.user_agent is None:
            return "Error: User avatar not found"
            
        match_agent = self.available_participants[match_name]
        # match_prompt = match_agent.get_full_system_prompt(num_examples=4)
        
        self.simulator = DateSimulator(max_messages=12)
        self.simulator.model_name = self.model_name
        self.simulator.initialize_model_client()
        
        # Create date organizer from template
        self.simulator.set_date_organizer(self.organizer_template, self.manager_agent.cdp_agentkit.wallet.default_address.address_id)
        
        # Add the participants
        #self.simulator.add_participant(self.user_profile.name, user_prompt)
        #self.simulator.add_participant(match_name, match_prompt)
        
        self.simulator.participants[self.user_agent.name] = self.user_agent
        self.simulator.add_participant_from_agent(match_agent)
        
        # Set the summarizer from template
        self.simulator.set_summarizer(self.summarizer_template)
        
        # Run the simulation
        result = await self.simulator.simulate_date(scene_instruction)
        conversation = self.simulator._format_conversation_history_with_tool_calls(result.messages)
        summary = await self.simulator.summarize_date(result)
        
        # After the date, mint an NFT
        participants = [self.user_agent.name, match_name]
        try:
            nft_result = await self._mint_date_nft_from_conversation(conversation, participants)
        except Exception as e:
            nft_result = f"Error minting NFT: {str(e)}"
        
        self.simulator.save_conversation(result, summary)
        return f"{conversation}\n\n{nft_result}"
        
    async def create_user_avatar(self, name: str, interests: List[str], personality_traits: List[str], conversation_style: List[str], dislikes: List[str], areas_of_expertise_and_knowledge: List[str], passionate_topics: List[str], user_appearance: List[str]):
        """Create or update a user avatar profile from the collected data, call without any markdown formatting."""
        if self.user_agent is None:
            raise ValueError("User avatar not found")
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
            user_agent.user_profile.appearance = user_appearance
        user_agent.save(path)

        return f"Updated profile for {user_agent.user_profile.name}"
        
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

    async def mint_date_nft(self, prompt: str, participants: list[str]) -> str:
        """Generate an image and mint an NFT for a date. Give a detailed prompt describing the image, setting and participants."""
        
        prompt = prompt.replace("Bruce", "Bruce Lee")
        prompt = prompt.replace("Arnold", "Arnold Schwarzenegger")
        prompt = prompt.replace("Trump", "Donald Trump")
        prompt = prompt.replace("Tesla", "Nikola Tesla")
        
        # Generate the image using Leonardo
        image_request = LeonardoRequest(prompt=prompt)
        image_response = await self.image_tool.run(image_request, CancellationToken())
        logging.warning(f"Image generated with prompt: {prompt}\nImage URL: {image_response.urls[0]}")
        if not image_response.urls:
            return "Failed to generate image"
            
        image_url = image_response.urls[0]
        # return f"Image taken during the date: {prompt}\nImage: {image_url}"
        
        # Register the token
        metadata = self.token_registry.register_token(
            image_url=image_url,
            prompt=prompt,
            participants=participants
        )
        logging.info(f"Token registered: {metadata}")
        # Mint the NFT using CDP toolkit
        for tool in self.manager_agent.cdp_toolkit.get_tools():
            if tool.name == "mint_nft":
                result = await tool.arun({
                    "contract_address": "0xb598fFa84C2608cC93b203772A6A2683a84aC959",
                    "destination": await self.get_user_avatar_wallet()
                })
                logging.info(f"NFT minted: {result}")
                result_msg = f"Image taken during the date: {prompt}\nImage: {image_url}\nNFT minted successfully {result}"
                if result.startswith("Minted NFT from contract"):
                    result_msg += f"\nOpensea: https://testnets.opensea.io/assets/base_sepolia/0xb598ffa84c2608cc93b203772a6a2683a84ac959/{metadata.token_id}"
                return result_msg
        
        return f"Failed to mint NFT, but image was generated: {image_url}"

    async def _mint_date_nft_from_conversation(self, conversation: str, participants: list[str]) -> str:
        """Generate an image and mint an NFT for a date."""
        # Generate a prompt for the image
        path = UserAgentWithWallet.get_user_agent_path(self.user.id)
        user_agent = Agent.load(path)
        prompt = await self.prompt_generator.generate_prompt(conversation, user_agent.user_profile)
        
        return await self.mint_date_nft(prompt, participants)

async def main():
    manager = DateManager()
    await manager.init_memory()
    await manager.start_conversation()

if __name__ == "__main__":
    asyncio.run(main())
