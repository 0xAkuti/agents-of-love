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

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Get or create date manager for this user
        if request.user_id not in date_managers:
            user = SimpleUser(id=request.user_id, name=request.user_name)
            date_managers[request.user_id] = DateManager(user=user)
            # Initialize the date manager
            await date_managers[request.user_id].init_memory()
        
        # Get response from date manager
        response = await date_managers[request.user_id].get_manager_response(request.message)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 