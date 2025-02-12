import os
import asyncio
import aiohttp

from pydantic import BaseModel, Field
from autogen_core.tools import BaseTool
from autogen_core import CancellationToken

from src.agents.prompt_generator import PromptGenerator

class LeonardoRequest(BaseModel):
    """Parameters for image generation."""
    prompt: str = Field(..., description="A text description of the image you want to generate")
    negative_prompt: str = Field(
        default="plastic, Deformed, blurry, bad anatomy, bad eyes, crossed eyes, disfigured, poorly drawn face, mutation, mutated, extra limb, ugly, poorly drawn hands, missing limb, blurry, floating limbs, disconnected limbs, malformed hands, blur, out of focus, long neck, long body, mutated hands and fingers, out of frame, blender, doll, cropped, low-res, poorly-drawn face, out of frame double, two heads, blurred, ugly, disfigured, too many fingers, deformed, repetitive, black and white, grainy",
        description="What not to include in the image"
    )

class LeonardoResponse(BaseModel):
    """Response from image generation."""
    urls: list[str] = Field(..., description="List of URLs for the generated images")

class LeonardoImageTool(BaseTool[LeonardoRequest, LeonardoResponse]):
    """A tool for generating images using Leonardo AI."""
    
    def __init__(self):
        super().__init__(
            name="generate_image_leonardo",
            description="Generate images from text descriptions, e.g., users talking selfies or pictures, notes or other things happening during the date",
            args_type=LeonardoRequest,
            return_type=LeonardoResponse
        )
        self.api_key = os.getenv("LEONARDO_API_KEY")
        if not self.api_key:
            raise ValueError("LEONARDO_API_KEY environment variable is not set")
        
        # Leonardo API endpoints
        self.base_url = "https://cloud.leonardo.ai/api/rest/v1"
        self.generate_url = f"{self.base_url}/generations"
        
        # Default model and settings
        self.model_id = "aa77f04e-3eec-4034-9c07-d0f619684628"  # Leonardo Kino XL
        
    async def _wait_for_generation(self, session: aiohttp.ClientSession, generation_id: str, max_attempts: int = 30) -> dict:
        """Wait for the generation to complete and return the result."""
        url = f"{self.base_url}/generations/{generation_id}"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.api_key}"
        }
        
        for _ in range(max_attempts):
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get generation status: {await response.text()}")
                
                data = await response.json()
                status = data["generations_by_pk"]["status"]
                
                if status == "COMPLETE":
                    return data
                elif status == "FAILED":
                    raise Exception("Image generation failed")
                
                await asyncio.sleep(0.5)  # Wait 0.5 seconds before checking again
                
        raise Exception("Timeout waiting for image generation")

    async def run(self, args: LeonardoRequest, cancellation_token: CancellationToken) -> LeonardoResponse:
        """
        Generate an image using Leonardo AI.
        
        Args:
            args: The image generation parameters
            cancellation_token: Token for cancelling the operation
            
        Returns:
            LeonardoResponse: Object containing the URLs of generated images
        """
        try:
            payload = {
                "alchemy": False,
                "height": 768,
                "width": 1024,
                "modelId": self.model_id,
                "num_images": 1,
                "presetStyle": "CINEMATIC",
                "prompt": PromptGenerator._fix_full_name(args.prompt),
                "negative_prompt": args.negative_prompt,
                "seed": 1234
            }
            
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "authorization": f"Bearer {self.api_key}"
            }
            
            async with aiohttp.ClientSession() as session:
                # Step 1: Initialize generation
                async with session.post(self.generate_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to initialize generation: {await response.text()}")
                    
                    init_data = await response.json()
                    generation_id = init_data["sdGenerationJob"]["generationId"]
                    
                    # Step 2: Wait for generation to complete and get results
                    result = await self._wait_for_generation(session, generation_id)
                    
                    # Extract image URLs
                    image_urls = [
                        img["url"] 
                        for img in result["generations_by_pk"]["generated_images"]
                    ]
                    
                    return LeonardoResponse(urls=image_urls)
                
        except Exception as e:
            raise RuntimeError(f"Error generating image: {str(e)}")

# Example usage:
"""
leonardo_tool = LeonardoImageTool()
request = LeonardoRequest(
    prompt="a modern and fun photobooth picture of two people having a good time"
)
response = await leonardo_tool.run(request, CancellationToken())
print(response.urls)
""" 