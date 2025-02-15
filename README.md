# Agents of Love 💖

An AI-powered dating simulation platform that creates virtual date scenarios and analyzes interpersonal dynamics using blockchain technology and AI agents.

## Description

Imagine a world where you can go on a virtual "date" with Nikola Tesla, Bruce Lee, ELIZA, or any AI-generated character of your choice—without worrying about what to say or boring conversations.

We have created an virtual dating experience where users can 'clone' themselves into avatars and interact with AI-generated characters in a dynamic, fully autonomous environment. Each AI character and user avatar has its own CDP wallet, enabling transactions like paying for dates, buying virtual gifts, and even minting memories as NFTs.

![whitebk_flowchart](https://github.com/user-attachments/assets/30f8787b-2a20-47d8-9e3a-f397b5de7553)


### How It Works:
1. Create Your AI Avatar – Users generate a digital twin with their personality, interests, and preferences by chatting with the Date Manager Agent in a Discord channel.
2. Match & Date AI Characters – Let the Date Manager pair you or choose a pre-created AI characters like Donald Trump, ELIZA, Tesla, or Bruce Lee.
3. Autonomous Date Simulation – The Date Organizer coordinates dates in the backend. Users can simply let the AI run the date.
4. Fully Autonomous Agents– Avatars and AI characters can decide when to pay for dates, buy gifts, and interact dynamically based on how the date unfolds.
5. Multi-agent Assistance – Background AI agents, such as a Date Organizer and Conversation Selector work behind the scene with the Data Manager to ensure a seamless and engaging experience.
6. Date Highlights – Users can observe date highlights, chat with the Date Manager for insights, or view their gifts and selfies which take place in a Discord channel with a privacy toggle. 
7. Mint Date Memories as NFTs – Avatars can take selfies, exchange gifts, buy souvenirs, and capture memories as mintable NFTs that are sent to their wallets after the date.


### Core Dating Features
- Create personalized AI dating profiles with:
  - Interests and hobbies
  - Personality traits
  - Conversation styles
  - Areas of expertise
  - Personal preferences and dislikes
  - Unique experiences
- Run natural date simulations between AI agents and Avatars with distinct personalities
- Get detailed analysis of date chemistry and interaction dynamics
- Save conversations and summaries as markdown files
- AI-generated date environment and scene settings
- Persistant memory for AI assistant


## How It's Made
- Custom Starknet Tools for Autogen - Implemented custom tools for Starknet to be used in Autogen using starknet-py to allow agents to autonomously deploy accounts, transfer tokens, mint NFTs, and check balances depending on their permissions.
- Coinbase Agent Kit – Each user avatar and AI character is equipped with a CDP wallet for payment
- Multi-Agent System: The system runs on Autogen, coordinating multiple AI agents:
  - Three AI Assistants (Date Manager, Date Organizer, Conversation Selector) handle date logistics. We used prompts to define their roles.
  - Fully Autonomous Agents (user avatars & AI characters) also have unique character files defining their communication style and personality. We used prompts for dating guideline.
- Discord as the Frontend and primary UI
- Full date simulation run run on a server-side backend using Autogen
- NFT smart contracts deployed by the agent:
  - on Base Sepolia (contract address: 0xb598fFa84C2608cC93b203772A6A2683a84aC959). NFT date memories minted by the agent, viewable on OpenSea (https://testnets.opensea.io/collection/date-memories).
  - on Starknet Mainnet (contract address: 0x07881ce471fad37b0344100cf86efdccce1c93dafc15c52c1c3114da5193419e). NFT date memories minted by the agent, viewable on Element (https://element.market/assets/starknet/0x07881ce471fad37b0344100cf86efdccce1c93dafc15c52c1c3114da5193419e).

### Technical Stack
- Autogen multi-agent framework 
- OpenAI GPT-4
- FastAPI
- Discord
- CDP Toolkit for blockchain integration
- Leonardo AI for image generation
- SQLite for wallet storage
- Docker support

  
## Getting Started

### Prerequisites
- Python 3.11+
- Docker (optional)
- OpenAI API key
- Discord API token
- CDP API credentials
- Leonardo AI API key

### Environment Variables
```bash
OPENAI_API_KEY=""
DISCORD_TOKEN=""
CDP_API_KEY_NAME=""
CDP_API_KEY_PRIVATE_KEY=""
NETWORK_ID=""
LEONARDO_API_KEY=""
```

### Installation

1. Clone the repository:
```bash
git clone https://github.com/0xAkuti/agents-of-love
cd agents-of-love
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the application:
```bash
# Run both API and Discord bot
./start.sh

# Or run them separately
python api.py  # For API only
python bot.py  # For Discord bot only
```

### Docker Support

Build and run using Docker:
```bash
docker build -t agents-of-love .
docker run -p 8000:8000 agents-of-love
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
