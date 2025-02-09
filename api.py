from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from date_manager import DateManager
from src.model import SimpleUser
import uvicorn
app = FastAPI(title="Date Manager API")

# Store date managers for different users
date_managers = {}

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
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 