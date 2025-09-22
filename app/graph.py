from __future__ import annotations

from typing import Dict, List, Sequence, TypedDict
from typing_extensions import Annotated

import json
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, AnyMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .config import Settings
from .robot import RobotClient
from .tools import build_tools


class MessagesState(TypedDict):
    # Accumulate messages across nodes
    messages: Annotated[List[AnyMessage], add_messages]


def _route_after_model(state: MessagesState):
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return END


class GraphManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sessions: Dict[str, MessagesState] = {}

        # Robot client
        self.robot = RobotClient(
            host=settings.robot_host,
            port=settings.robot_port,
            transport=settings.robot_transport,
        )

        # Tools
        self.tools = build_tools(
            self.robot,
            settings.action_name_follow,
            settings.action_name_block,
            settings.action_name_research,
        )

        # Model
        base_model = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.temperature,
            num_ctx=settings.num_ctx,
        )
        # Only bind tools if explicitly enabled. Some Ollama models do not
        # support tool/function calling and will error with 400 otherwise.
        self.model = (
            base_model.bind_tools(self.tools) if settings.use_tools else base_model
        )

        # Build graph
        builder = StateGraph(MessagesState)
        builder.add_node("model", self._call_model)
        if settings.use_tools:
            builder.add_node("tools", ToolNode(self.tools))
            builder.add_edge("tools", "model")
            builder.add_conditional_edges("model", _route_after_model, {"tools": "tools", END: END})
        else:
            # No tool support; model is terminal node
            builder.add_edge("model", END)
        builder.set_entry_point("model")
        self.graph = builder.compile()

    def _ensure_session(self, session_id: str) -> MessagesState:
        if session_id not in self.sessions:
            self.sessions[session_id] = {"messages": [SystemMessage(content=self.settings.system_prompt)]}
        return self.sessions[session_id]

    def _call_model(self, state: MessagesState) -> MessagesState:
        # Chat models expect a list of BaseMessage (chat history), not the
        # full state dict. Feed only the messages list so tools and history
        # are applied correctly.
        # Debug: print last user message
        try:
            last_user = next((m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None)
            if last_user is not None:
                print("[LLM][input][user]", (last_user.content or "").strip())
        except Exception:
            pass

        res = self.model.invoke(state["messages"])

        # Debug: print assistant content and tool calls (if any)
        try:
            content = (res.content or "").strip()
            if content:
                print("[LLM][output][assistant]", content)
            tool_calls = getattr(res, "tool_calls", None)
            if tool_calls:
                print("[LLM][output][tool_calls]", json.dumps(tool_calls, ensure_ascii=False))
        except Exception:
            pass
        return {"messages": [res]}

    def chat(self, session_id: str, user_text: str) -> str:
        session = self._ensure_session(session_id)
        session["messages"].append(HumanMessage(content=user_text))

        result: MessagesState = self.graph.invoke({"messages": session["messages"]})
        # Graph returns the full updated state; extend session
        # Only append new messages beyond what we had
        new_msgs = result["messages"][len(session["messages"]):]
        session["messages"].extend(new_msgs)

        # Find the latest AI message content to return
        last_ai = None
        for m in reversed(session["messages"]):
            if isinstance(m, AIMessage):
                last_ai = m
                break
        # 1) Try JSON-based command parsing from the assistant text
        if last_ai:
            parsed = self._try_parse_command(last_ai.content or "")
            if parsed is not None:
                cmd = parsed.get("cmd")
                say = (parsed.get("say") or "").strip()
                handled_text = self._handle_command(cmd)
                # If command executed, prefer 'say' if provided; otherwise, use a default confirmation
                if handled_text is not None:
                    return say or handled_text
                # If cmd was 'none', just return 'say' or original content
                if cmd == "none":
                    return say or (last_ai.content or "")
                # If parsing succeeded but command unknown, fall through to content
                if say:
                    return say
                return last_ai.content or ""

        # 2) Fallback: if the model emitted only a tool call with no text,
        #    do not surface raw tool output (no robot-side feedback). Show a generic ack unless error.
        for m in reversed(new_msgs):
            if isinstance(m, ToolMessage):
                tool_text = (m.content or "").strip()
                if tool_text:
                    return tool_text if tool_text.startswith("ERROR") else "명령을 전송했습니다."

        # 3) Default: return assistant content or empty
        return (last_ai.content or "").strip() if last_ai else ""

    # --- JSON command parsing & execution helpers ---
    def _try_parse_command(self, text: str):
        import re
        try:
            # Fast path: direct JSON
            s = text.strip()
            if s.startswith("{") and s.endswith("}"):
                return json.loads(s)
            # Code fence with json
            fence = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", s, re.IGNORECASE)
            if fence:
                return json.loads(fence.group(1))
            # Any fenced block
            fence_any = re.search(r"```\s*(\{[\s\S]*?\})\s*```", s)
            if fence_any:
                return json.loads(fence_any.group(1))
            # Brace scan to find first balanced JSON object
            start = -1
            depth = 0
            for i, ch in enumerate(s):
                if ch == '{':
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == '}':
                    if depth > 0:
                        depth -= 1
                        if depth == 0 and start != -1:
                            candidate = s[start:i+1]
                            try:
                                return json.loads(candidate)
                            except Exception:
                                pass
            return None
        except Exception as e:
            print(f"[CMD][parse][error] {e}")
            return None

    def _handle_command(self, cmd: str | None) -> str | None:
        if not cmd:
            return None
        norm = cmd.strip().lower()
        try:
            if norm in ("follow", "따라", "따라가", "따라가라", "따라와"):
                print("[CMD] execute: follow")
                self.robot.send(self.settings.action_name_follow)
                return "따라가겠습니다."
            if norm in ("block", "막", "막아", "길을 막아", "길을 막아라"):
                print("[CMD] execute: block")
                self.robot.send(self.settings.action_name_block)
                return "앞을 가로막겠습니다."
            if norm in ("research", "탐색", "탐색해", "수색", "수색해", "scan", "explore"):
                print("[CMD] execute: research")
                self.robot.send(self.settings.action_name_research)
                return "주변을 탐색하겠습니다."
            if norm == "none":
                print("[CMD] no-op")
                return None
            print(f"[CMD][warn] unknown cmd: {cmd}")
            return None
        except Exception as e:
            print(f"[CMD][error] {e}")
            return f"ERROR: {e}"
