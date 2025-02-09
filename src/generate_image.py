import os
from typing import Literal
from openai import AsyncOpenAI
from autogen_core.tools import BaseTool
from autogen_core import CancellationToken
from pydantic import BaseModel, Field
from autogen_core import Image
from PIL import Image as PILImage
import aiohttp
import asyncio
import json
from huggingface_hub import InferenceClient


async def from_url(url: str) -> Image:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            content = await response.read()
            return Image.from_pil(PILImage.open(content))

AvailableImageSizes = Literal['256x256', '512x512', '1024x1024', '1792x1024', '1024x1792']
AvailableImageQualities = Literal['standard', 'hd']
AvailableImageStyles = Literal['natural', 'vivid']
AvailableModels = Literal['dall-e-3', 'flux']

class ImageGenerationRequest(BaseModel):
    """Parameters for image generation."""
    prompt: str = Field(..., description="A text description of the image you want to generate")
    size: AvailableImageSizes = Field(default="512x512", description="The size of the generated image.")
    quality: AvailableImageQualities = Field(default="standard", description="The quality of the image. Options: standard, hd")
    style: AvailableImageStyles = Field(default="natural", description="The style of the image. Options: natural, vivid")
    n: int = Field(default=1, description="The number of images to generate (1-10)")
    model: AvailableModels = Field(default="dall-e-3", description="The model to use for generation: dall-e-3 or flux")

class ImageGenerationResponse(BaseModel):
    """Response from image generation."""
    urls: list[str] = Field(..., description="List of URLs for the generated images")

class ImageGenerationTool(BaseTool[ImageGenerationRequest, ImageGenerationResponse]):
    """A tool for generating images using OpenAI's DALL-E model or HuggingFace's FLUX model."""
    
    def __init__(self):
        super().__init__(
            name="generate_image",
            description="Generate images from text descriptions using DALL-E or FLUX",
            args_type=ImageGenerationRequest,
            return_type=ImageGenerationResponse
        )
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        if not self.hf_api_key:
            raise ValueError("HUGGINGFACE_API_KEY environment variable is not set")
            
        self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
        self.hf_client = InferenceClient(token=self.hf_api_key)
        
    async def generate_with_dalle(self, args: ImageGenerationRequest) -> ImageGenerationResponse:
        """Generate images using DALL-E model"""
        response = await self.openai_client.images.generate(
            model="dall-e-3",
            prompt=args.prompt,
            size=args.size,
            quality=args.quality,
            style=args.style,
            n=args.n,
            response_format="b64_json"
        )
        images = [image.b64_json for image in response.data]
        return ImageGenerationResponse(urls=images)
        
    async def generate_with_flux(self, args: ImageGenerationRequest) -> ImageGenerationResponse:
        """Generate images using FLUX model"""
        response = await asyncio.to_thread(
            self.hf_client.post,
            model="black-forest-labs/FLUX.1-schnell",
            json={"inputs": args.prompt}
        )
        return ImageGenerationResponse(urls=[response])
        
    async def run(self, args: ImageGenerationRequest, cancellation_token: CancellationToken) -> ImageGenerationResponse:
        """
        Generate an image based on the provided request.
        
        Args:
            args: The image generation parameters
            cancellation_token: Token for cancelling the operation
            
        Returns:
            ImageGenerationResponse: Object containing the URLs of generated images
        """
        try:
            if args.model == "dall-e-3":
                return await self.generate_with_dalle(args)
            else:  # flux
                return await self.generate_with_flux(args)
                
        except Exception as e:
            raise RuntimeError(f"Error generating image: {str(e)}")

# Example usage:
"""
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Create the image generation tool
image_tool = ImageGenerationTool()

# Create an assistant with the image generation tool
assistant = AssistantAgent(
    name="artist",
    system_message="You are an AI artist assistant. You can generate images based on descriptions.",
    model_client=OpenAIChatCompletionClient(model="gpt-4"),
    tools=[image_tool],
    reflect_on_tool_use=True
)
"""
