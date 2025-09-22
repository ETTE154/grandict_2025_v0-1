from typing import List, Optional, Dict, Any
from langchain_core.tools import Tool

from .robot import RobotClient


def build_tools(
    robot: RobotClient,
    action_name_follow: str,
    action_name_block: str,
    action_name_research: str,
) -> List[Tool]:
    def t_follow(**kwargs) -> str:
        try:
            if kwargs:
                print(f"[TOOL] invoke: {action_name_follow} args={kwargs}")
            else:
                print(f"[TOOL] invoke: {action_name_follow}")
            robot.send(action_name_follow)
            return "OK"
        except Exception as e:
            # Avoid crashing the chat flow if robot connection fails
            print(f"[TOOL][error] {e}")
            return f"ERROR: {e}"

    def t_block(**kwargs) -> str:
        try:
            if kwargs:
                print(f"[TOOL] invoke: {action_name_block} args={kwargs}")
            else:
                print(f"[TOOL] invoke: {action_name_block}")
            robot.send(action_name_block)
            return "OK"
        except Exception as e:
            # Avoid crashing the chat flow if robot connection fails
            print(f"[TOOL][error] {e}")
            return f"ERROR: {e}"

    def t_research(**kwargs) -> str:
        try:
            if kwargs:
                print(f"[TOOL] invoke: {action_name_research} args={kwargs}")
            else:
                print(f"[TOOL] invoke: {action_name_research}")
            robot.send(action_name_research)
            return "OK"
        except Exception as e:
            # Avoid crashing the chat flow if robot connection fails
            print(f"[TOOL][error] {e}")
            return f"ERROR: {e}"

    # Some models (e.g., gpt-oss) emit a generic tool call named "tool_use"
    # with structured args like {"name": "따라가라", "arguments": {...}}.
    # Provide a dispatcher tool to handle that pattern.
    def t_tool_use(name: str, arguments: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        try:
            norm = (name or "").strip().lower()
            # Simple normalization for Korean/English synonyms
            if any(k in norm for k in ["따라", "follow"]):
                print(f"[TOOL] dispatch(tool_use) -> {action_name_follow}")
                robot.send(action_name_follow)
                return "OK"
            if any(k in norm for k in ["막", "block"]):
                print(f"[TOOL] dispatch(tool_use) -> {action_name_block}")
                robot.send(action_name_block)
                return "OK"
            if any(k in norm for k in ["탐색", "수색", "research", "scan", "explore"]):
                print(f"[TOOL] dispatch(tool_use) -> {action_name_research}")
                robot.send(action_name_research)
                return "OK"
            msg = f"Unknown tool name: {name}"
            print(f"[TOOL][warn] {msg}")
            return f"ERROR: {msg}"
        except Exception as e:
            print(f"[TOOL][error] {e}")
            return f"ERROR: {e}"

    follow_tool = Tool.from_function(
        name=action_name_follow,
        description=(
            "Go2 로봇이 사용자를 따라가도록 실행한다. 인자 없음. 사용자가 '따라와', '따라가', 'follow me' 등 "
            "유사 표현을 하면 이 도구를 호출하라."
        ),
        func=t_follow,
    )

    block_tool = Tool.from_function(
        name=action_name_block,
        description=(
            "Go2 로봇이 길을 막도록 실행한다. 인자 없음. 사용자가 '길을 막아', '앞을 막아', 'block the way' 등 "
            "유사 표현을 하면 이 도구를 호출하라."
        ),
        func=t_block,
    )

    research_tool = Tool.from_function(
        name=action_name_research,
        description=(
            "Go2 로봇이 주변을 탐색(research/scan)하도록 실행한다. 인자 없음. 사용자가 '탐색해', '수색해', 'research' 등 "
            "유사 표현을 하면 이 도구를 호출하라."
        ),
        func=t_research,
    )

    tool_use = Tool.from_function(
        name="tool_use",
        description=(
            "도구 디스패처. name 이 '따라가라' 또는 '길을 막아라'일 때 해당 동작 실행. "
            "영문 'follow me', 'block the way' 도 인식."
        ),
        func=t_tool_use,
    )

    return [follow_tool, block_tool, research_tool, tool_use]
