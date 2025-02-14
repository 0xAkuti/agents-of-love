from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from src.agents.date_manager import DateManager
from src.models.model import SimpleUser
from src.server.token_registry import TokenRegistry, NFTMetadata

app = FastAPI(title="Date Manager API")

# Store date managers for different users
date_managers = {}
token_registry = TokenRegistry()

class ChatRequest(BaseModel):
    user_id: int
    user_name: str
    message: str
    
class AutonomeRequest(BaseModel):
    text: str
    
class AutonomeResponse(BaseModel):
    text: str

class ChatResponse(BaseModel):
    response: str

@app.get("/token/{token_id}", response_model=NFTMetadata)
async def get_token_metadata(token_id: int):
    """Get metadata for a specific token ID."""
    metadata = await token_registry.get_nft_metadata(token_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Token not found")
    return metadata

@app.get("/tokens")
async def list_tokens():
    """List all tokens and their metadata."""
    return {"tokens": token_registry.registry}

@app.post("/chat", response_model=AutonomeResponse)
async def chat(request: AutonomeRequest):
    try:
        # Get or create date manager for this user
        if "AutonomeChat" not in date_managers:
            date_managers["AutonomeChat"] = DateManager(SimpleUser(id=0, name="AutonomeChat"))
            # Initialize the date manager
            await date_managers["AutonomeChat"].init_memory()
        
        # Get response from date manager
        response = await date_managers["AutonomeChat"].get_manager_response(request.text)
        return AutonomeResponse(text=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8080, reload=True) 