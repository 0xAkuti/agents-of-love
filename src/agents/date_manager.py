import asyncio
import logging
from typing import Callable, List, Optional, Dict
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
import os
import pathlib
import dotenv
import json

from src.models.model import Agent, AgentRole, UserProfile, SimpleUser
from src.models.agent_with_wallet import AgentWithWallet, WalletProvider
from src.tools.date_simulator import DateSimulator
from autogen_core.memory import ListMemory, MemoryContent, MemoryMimeType
from src.tools.leonardo_image import LeonardoImageTool, LeonardoRequest
from src.agents.prompt_generator import PromptGenerator
from src.server.token_registry import TokenRegistry
from src.models.user_agent import UserAgentWithWallet
from src.storage.manager import StorageManager

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
        
        self.user_agent: Optional[UserAgentWithWallet] = None  # Will be initialized in initialize()
        self.manager_agent: Optional[AgentWithWallet] = None  # Will be initialized in initialize()
            
        # Create memory for storing user profile
        self.memory = ListMemory()
        self.prompt_generator = PromptGenerator(self.model_client)
        self.token_registry = TokenRegistry()
        self.image_tool = LeonardoImageTool()
        
        self.simulator: Optional[DateSimulator] = None
        self.date_started_callback: Optional[Callable[[], None]] = None
        self.storage_manager = StorageManager()
    
    async def initialize(self):
        """Initialize the date manager with user agent and manager agent."""
        logging.info("Initializing date manager...")
        await self.token_registry.initialize()
        
        if self.user:
            logging.info(f"Loading user avatar for {self.user.name} ({self.user.id})")
            self.user_agent = await UserAgentWithWallet.load_or_create(self.user)
            logging.info("Created user agent, initializing...")
            await self.user_agent.initialize()
            logging.info("User agent initialized")
            
            logging.info("Creating manager agent...")
            self.manager_agent = await AgentWithWallet.from_json(
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
            logging.info("Manager agent created, initializing memory...")
            await self.init_memory()
            logging.info("Date manager initialization complete")
        else:
            raise ValueError("User is required for now")
    
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
        await self.storage_manager.save_agent_state(self.user.id, state)
            
    async def _load_state(self) -> bool:
        """Load the previous state if it exists and returns whether it was loaded successfully."""
        try:
            # Read the file content first
            state = await self.storage_manager.load_agent_state(self.user.id)
            if state is None:
                logging.warning(f"No state found for user {self.user.id}")
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
        print("Initializing memory...")
        logging.info("Initializing memory...")
        if await self._load_state():
            print("Loaded state")
            logging.info("Loaded state")
            return
            
        if self.user_agent and self.user_agent.agent_data.user_profile:
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
                await self._save_state()
    
    def _load_available_participants(self) -> Dict[str, Agent]:
        """Load all available participant agents from the agents folder."""
        participants = {}
        agents_path = pathlib.Path("agents")
        for file in agents_path.glob("*.json"):
            if file.name == "template.json":
                continue
            agent = Agent.load_from_file(file)
            if agent.role == AgentRole.PARTICIPANT:
                participants[agent.name] = agent
        return participants
    
    async def get_user_avatar_wallet(self) -> str:
        """Get the wallet address of the user's avatar."""
        if self.user_agent is None:
            return "User avatar not found"
        return self.user_agent.get_address()
    
    async def get_user_avatar_balance(self, asset_id: str) -> str:
        """Get balance for all addresses in the wallet of the users avatar for a given asset.

        Args:
            asset_id (str): The asset ID to get the balance for (e.g., "eth", "strk", "usdc", or a valid contract address like "0x036CbD53842c5426634e7929541eC2318f3dCF7e")

        Returns:
            str: A message containing the balance information of all addresses in the wallet.

        """
        if self.user_agent is None:
            return "User avatar not found"
        if self.user_agent.wallet_provider == WalletProvider.CDP:
            for tool in self.user_agent.cdp_toolkit.get_tools():
                if tool.name == "get_balance":
                    return await tool.arun({"asset_id": asset_id})
        elif self.user_agent.wallet_provider == WalletProvider.STARKNET:
            return await self.user_agent.starknet_toolkit.get_strk_balance()
        return "No balance tool found"
        
    async def list_available_participants(self) -> str:
        """List all available participants with their brief descriptions."""
        if not self.available_participants:
            return "No participants available for dating."
        
        available_participants = [f"{p.name}: {p.system_prompt}" for p in self.available_participants.values()]
                
        return "Available participants for dating:\n" + "\n".join(available_participants) + "\n When referring to a participant description refer to them in third person."
        
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
        self.simulator.set_date_organizer(self.organizer_template, self.manager_agent.get_address())
        
        # Add the participants
        #await self.simulator.add_participant(self.user_profile.name, user_prompt)
        #await self.simulator.add_participant(match_name, match_prompt)
        
        self.simulator.participants[self.user_agent.name] = self.user_agent
        await self.simulator.add_participant_from_agent(match_agent)
        
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
        """Create or update a user avatar profile from the collected data, call without any markdown formatting.
        And deploy their account if using starknet and not deployed yet."""
        if self.user_agent is None:
            raise ValueError("User avatar not found")
        user_agent_data = await self.storage_manager.load_user_agent(self.user.id)
        if user_agent_data is None:
            raise ValueError("User avatar not found")
        user_agent = Agent.model_validate(user_agent_data)        
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
        await self.storage_manager.save_user_agent(self.user.id, user_agent.model_dump(mode="json"))
        
        if self.user_agent.wallet_provider == WalletProvider.STARKNET:
            funder_seed = self.manager_agent.wallet_data.seed
            if isinstance(funder_seed, str):
                funder_seed = int(funder_seed, 16)
            await self.user_agent.starknet_toolkit.setup_account_if_needed(funder_seed)
            return f"Updated profile for {user_agent.user_profile.name} and deployed account {self.user_agent.get_address()}"

        return f"Updated profile for {user_agent.user_profile.name}"
        
    async def get_manager_response(self, user_input: str) -> str:
        """Get a response from the manager agent."""
        logging.info(f"Getting manager response for input: {user_input[:100]}...")
        try:
            response = await self.manager_agent.on_messages(
                [TextMessage(content=user_input, source="user")],
                cancellation_token=CancellationToken(),
            )
            logging.info("Got response from manager agent")
            return response.chat_message.content
        except Exception as e:
            logging.error(f"Error getting manager response: {e}", exc_info=True)
            return "Sorry, I encountered an error while processing your message. Please try again later."
        
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
        metadata = await self.token_registry.register_token(
            image_url=image_url,
            prompt=prompt,
            participants=participants
        )
        logging.info(f"Token registered: {metadata}")
        # Mint the NFT using CDP toolkit
        if self.user_agent.wallet_provider == WalletProvider.CDP:
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
        elif self.user_agent.wallet_provider == WalletProvider.STARKNET:
            result = await self.manager_agent.starknet_toolkit.mint_nft(self.user_agent.get_address(), metadata.token_id)
            return f"Image taken during the date: {prompt}\nImage: {image_url}\nNFT minted successfully\n {result}"
        
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
    await manager.initialize()
    await manager.start_conversation()

if __name__ == "__main__":
    asyncio.run(main())
