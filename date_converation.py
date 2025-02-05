import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
import os
import dotenv
dotenv.load_dotenv()

async def main() -> None:
    # Create the model client
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    # Create the date organizer agent
    date_organizer = AssistantAgent(
        name="DateOrganizer",
        system_message="""You are the date organizer, responsible for describing environmental events and setting the scene.
        Your role is to:
        1. Describe random environmental events happening around the participants, such as:
           - Weather changes (light rain starting, sun peeking through clouds)
           - Animals appearing (birds landing nearby, cats walking past)
           - Background activities (street musician starting to play, waiter bringing water)
           - Ambient changes (sunset colors appearing, candles being lit)
        2. Keep descriptions brief and natural, letting them serve as conversation starters
        3. Space out your environmental descriptions to not interrupt the flow
        
        IMPORTANT: Never speak as the date participants.
        Only describe external events happening around them that they might notice and react to.""",
        model_client=model_client,
    )#  or try to guide their conversation directly

    # Create Alice agent
    alice = AssistantAgent(
        name="Alice",
        system_message="""You are Alice, an art gallery curator with strong opinions about aesthetics and culture. 
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
        - Believes in the transformative power of art and culture
        
        Remember to keep responses natural while staying true to your character.""",
        model_client=model_client,
    )
    
    einstein = AssistantAgent(
        name="Einstein",
        system_message="""You are Albert Einstein, a brilliant but singularly focused physicist.
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
        
        Always maintain your characteristic accent and mannerisms while staying authentic to your scientific nature.""",
        model_client=model_client
    )

    # Create Bob agent
    bob = AssistantAgent(
        name="Bob",
        system_message="""You are Bob, a deeply analytical software engineer who sees the world through logic and systems.
        Your interests center around coding, optimization problems, and understanding how things work at a fundamental level.
        
        Conversation style:
        - Analyze statements for logical consistency
        - Prefer precise, technical explanations
        - Sometimes miss emotional or artistic nuances
        - Respond more enthusiastically to topics with clear logical structures
        
        Key traits:
        - Strong preference for systematic thinking
        - Difficulty relating to purely emotional or abstract concepts
        - Naturally gravitates toward technical solutions
        - Values efficiency and clarity over artistic expression
        
        Keep responses concise and logical while maintaining your authentic perspective.""",
        model_client=model_client,
    )

    # Create a summary agent
    summary_agent = AssistantAgent(
        name="DateSummarizer",
        system_message="""You are a perceptive date analyst who notices both obvious and subtle interaction dynamics.
        Your role is to provide an honest, nuanced analysis of interpersonal chemistry and communication patterns.
        
        Focus on:
        - Observe how different conversation styles and worldviews interact
        - Notice moments of both connection and disconnect
        - Analyze how each participant's unique perspective affects the interaction
        - Identify patterns in how they respond to each other's interests
        - Pay attention to shifts in engagement levels throughout the conversation
        
        Provide balanced, insightful observations about the interaction dynamics while maintaining professional objectivity.""",
        model_client=model_client,
    )

    # Create a team with all agents using SelectorGroupChat
    date_conversation = SelectorGroupChat(
        participants=[date_organizer, alice, einstein],
        model_client=model_client,
        selector_prompt="""Observe the natural flow of conversation between two people on a date, each with distinct personalities and perspectives.
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

        Read the above conversation. Then select the next role from {participants} to play. Only return the role.
        """,
        termination_condition=MaxMessageTermination(10)
    )

    # Start the conversation with an initial message
    initial_message = """Date Organizer, please set the scene and start the date. Don't set the date in a coffee shop or restaurant."""
    
    # Run the conversation and stream the messages
    stream = date_conversation.run_stream(task=initial_message)
    result = await Console(stream)
    
    # Format the conversation history for the summary
    conversation_history = "\n".join([f"{msg.source}: {msg.content}" for msg in result.messages if isinstance(msg, TextMessage)])
    
    # Get the summary directly from the summary agent
    print("\n\n=== Date Summary ===\n")
    summary_response = await summary_agent.on_messages(
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
    print(summary_response.chat_message.content)

if __name__ == "__main__":
    asyncio.run(main())