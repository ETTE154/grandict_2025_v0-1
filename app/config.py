import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    # Ollama
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    num_ctx: int = int(os.getenv("LLM_CONTEXT_TOKENS", "4096"))

    # 도구 호출(함수 호출) 사용 여부
    # JSON 기반 명령 파싱으로 전환하므로 기본값을 false로 변경
    # 필요 시 환경변수 USE_TOOLS=true 로 켤 수 있음
    use_tools: bool = os.getenv("USE_TOOLS", "false").lower() in ("1", "true", "yes", "y")

    # Robot socket
    robot_host: str = os.getenv("ROBOT_HOST", "127.0.0.1")
    robot_port: int = int(os.getenv("ROBOT_PORT", "5555"))
    robot_transport: str = os.getenv("ROBOT_TRANSPORT", "tcp")  # tcp or udp

    # 소켓으로 전송할 액션 이름 (UTF-8 정리)
    action_name_follow: str = os.getenv("ACTION_NAME_FOLLOW", "따라가라")
    action_name_block: str = os.getenv("ACTION_NAME_BLOCK", "길을 막아라")

    # System prompt: JSON 기반 명령 지시
    system_prompt: str = os.getenv(
        "SYSTEM_PROMPT",
        (
            "너는 유닛리 Go2 로봇 제어 보조자다. 사용자의 요청을 분석해 다음 JSON만 출력하라."
            "문장, 코드펜스(```), 주석, 설명 없이 오직 한 줄의 JSON 객체만 출력한다. 키는 아래와 같다.\n\n"
            "- cmd: 'follow' | 'block' | 'none' 중 하나\n"
            "- say: 한국어 짧은 응답 문장 (예: '알겠습니다. 따라가겠습니다.')\n\n"
            "규칙:\n"
            "1) 사용자가 '따라와/따라가/follow' 등 추종 의도를 표현하면 cmd='follow'\n"
            "2) '길을 막아/막아/block' 등 차단 의도를 표현하면 cmd='block'\n"
            "3) 실행이 불필요하거나 모호하면 cmd='none'\n"
            "4) 반드시 JSON만 출력 (예시) {\"cmd\":\"follow\",\"say\":\"알겠습니다. 따라가겠습니다.\"}\n"
        ),
    )
