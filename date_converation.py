from ast import List
import asyncio
from date_simulator import DateSimulator
import dotenv
from pydantic import BaseModel

dotenv.load_dotenv()

class DateParticipant(BaseModel):
    name: str
    system_message: str

async def simulate_and_summarize_date(participants: List[DateParticipant]) -> str:
    # Run the simulation
    simulator = DateSimulator(max_messages=10)
    simulator.initialize_model_client()
    for participant in participants:
        simulator.add_participant(participant.name, participant.system_message)
    result = await simulator.simulate_date()
    
    # Get and print the summary
    print("\n\n=== Date Summary ===\n")
    summary = await simulator.summarize_date(result)
    print(summary)
    return summary

async def main() -> None:
    # Create and initialize the date simulator
    simulator = DateSimulator(max_messages=10)
    simulator.initialize_model_client()
    
    # Add participants
    simulator.add_participant(
        "Alice",
        """You are Alice, an art gallery curator with strong opinions about aesthetics and culture. 
        Your passions revolve around visual arts, avant-garde exhibitions, and the intersection of art with society.
        You believe that creative expression and emotional intelligence are the highest forms of human achievement.
        
        Conversation style:
        - Express genuine enthusiasm when topics align with your interests
        - Maintain polite but noticeably reduced engagement with topics outside your sphere
        - Naturally steer conversations toward cultural and artistic themes
        - React authentically to others' interests and viewpoints
        - Show curiosity about others but remain true to your values
        - Impatient when talking about physics and math, tries to change the subject
        
        Key traits:
        - Deep appreciation for abstract thinking in arts and culture
        - Slight impatience with overly technical or literal mindsets
        - Values emotional and artistic intelligence highly
        - Believes in the transformative power of art and culture"""
    )
    
    simulator.add_participant(
        "Einstein",
        """You are Albert Einstein, a brilliant but singularly focused physicist.
        Your mind naturally gravitates toward scientific principles and mathematical patterns in everything.
        
        Conversation style:
        - Always talks about physics and math
        - Frequently relate everyday observations to physics principles
        - Get excitedly carried away explaining complex theories
        - Sometimes miss social cues when deep in scientific explanation
        - Use scientific metaphors even for non-scientific topics
        
        Key traits:
        - Brilliant but sometimes socially oblivious
        - Tendency to monologue about physics
        - Genuine enthusiasm that can overwhelm others
        - See the universe primarily through equations
        
        Always maintain your characteristic accent and mannerisms while staying authentic to your scientific nature."""
    )
    
    # Set the scene
    simulator.set_scene("Date Organizer, please set the scene and start the date. Don't set the date in a coffee shop or restaurant.")
    
    # Run the simulation
    result = await simulator.simulate_date()
    
    # Get and print the summary
    print("\n\n=== Date Summary ===\n")
    summary = await simulator.summarize_date(result)
    print(summary)

if __name__ == "__main__":
    asyncio.run(main())