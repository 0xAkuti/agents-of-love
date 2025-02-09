# Agents of Love 💖

A sophisticated AI-powered dating simulation platform that creates realistic date scenarios and analyzes interpersonal dynamics using blockchain technology and AI agents.

## Features

### Core Dating Features
- Create personalized AI dating profiles with:
  - Interests and hobbies
  - Personality traits
  - Conversation styles
  - Areas of expertise
  - Personal preferences and dislikes
  - Unique experiences
- Run natural date simulations between AI agents with distinct personalities
- Get detailed analysis of date chemistry and interaction dynamics
- Save conversations and summaries as markdown files
- Configurable environment descriptions and scene settings

### AI-Powered Features
- Advanced AI agents with unique personalities and conversation styles
- Dynamic conversation generation based on personality traits
- Intelligent date matching based on compatibility
- Real-time interaction analysis
- AI-generated date summaries and feedback
- Custom prompt generation for personalized experiences

### Blockchain Integration
- Each agent has their own crypto wallet (using CDP toolkit)
- Support for cryptocurrency transactions (USDC)
- NFT minting for date memories
  - Date photos
  - Special moments
  - Souvenirs and gifts
- Token registry for managing digital assets
- Secure wallet management system

### Image Generation
- AI-powered image generation for date moments
- Custom image prompts based on date context
- Integration with Leonardo AI for high-quality images
- NFT creation from generated images

### Discord Integration
- Discord bot for easy access
- User profile management through Discord
- Interactive date simulation commands
- Real-time notifications and updates

### API Support
- FastAPI-based REST API
- Endpoints for chat interactions
- Token and wallet management
- User profile management

## Price List
- Date simulation: $1 USDC
- Minting photos: $0.5 USDC
- Minting souvenirs: $0.5 USDC

## Technical Stack
- Python 3.11
- OpenAI GPT-4
- FastAPI
- Discord.py
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
- Base Sepolia network access

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
