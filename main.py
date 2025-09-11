import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.graph import GraphManager
from app.config import Settings


settings = Settings()
graph_manager = GraphManager(settings)

app = FastAPI(title="Go2 Control Chat (LangGraph + Ollama)")


class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str


@app.get("/", response_class=HTMLResponse)
def index():
    # Serve simple chat UI
    return FileResponse("web/index.html")


@app.post("/chat")
def chat(req: ChatRequest):
    try:
        content = graph_manager.chat(req.session_id, req.message)
        return JSONResponse({"reply": content})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


def run():
    import uvicorn
    uvicorn.run(
        app,
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    run()

