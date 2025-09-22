import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.graph import GraphManager
from app.config import Settings
from app.events import EventBus
from app.robot_server import RobotEventServer


settings = Settings()
graph_manager = GraphManager(settings)
event_bus = EventBus()
robot_event_server = RobotEventServer(
    host=settings.event_listen_host,
    port=settings.event_listen_port,
    transport=settings.event_transport,
    bus=event_bus,
)

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


@app.on_event("startup")
async def _on_startup():
    # Start socket server for robot events
    robot_event_server.start()


@app.on_event("shutdown")
async def _on_shutdown():
    robot_event_server.stop()


# Robot pushes asynchronous events (e.g., research results) here.
@app.post("/robot/event")
async def robot_event(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    # Minimal normalization: ensure a kind
    if not isinstance(data, dict):
        return JSONResponse(status_code=400, content={"error": "Body must be a JSON object"})
    kind = data.get("kind") or data.get("type") or "robot_event"
    data["kind"] = kind
    event_bus.publish(data)
    print(f"[ROBOT][event] {data}")
    return JSONResponse({"ok": True})


# Server-Sent Events stream for browser UI to receive robot updates.
@app.get("/events")
async def events():
    q = event_bus.subscribe()

    async def gen():
        try:
            # optional initial comment to open stream
            yield ":ok\n\n"
            while True:
                item = await q.get()
                # Each message is a single JSON line
                import json as _json
                payload = _json.dumps(item, ensure_ascii=False)
                yield f"data: {payload}\n\n"
        except Exception:
            pass
        finally:
            event_bus.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream")


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
