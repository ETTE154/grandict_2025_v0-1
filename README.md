Go2 Control Chat (LangGraph + Ollama)
====================================

개요
----
- LLM Function Calling을 이용해 유닛리 Go2 로봇을 제어하는 간단한 관리자 PC용 웹앱입니다.
- 채팅 UI에서 "따라가라" 또는 "길을 막아라" 관련 지시가 나오면, 소켓으로 `{name: 동작명, value: 1}` JSON을 전송합니다.
- LLM 백엔드는 Ollama + EXAONE 4.0 32B (GGUF)로 동작합니다.
- LangGraph를 활용해 Tool(함수) 호출 흐름을 구성했습니다.

구성
----
- 백엔드: FastAPI (`/` 웹 UI, `/chat` API)
- LLM: Ollama + `langchain-ollama` (모델: EXAONE 4.0 32B GGUF)
- 도구(함수):
  - `따라가라` (인자 없음)
  - `길을 막아라` (인자 없음)
- 로봇 통신: TCP/UDP 소켓 (기본 TCP), `{name: 동작명, value: 1}` 전송

사전 준비 (Ollama + 모델)
-------------------------
1) Ollama 설치 (Windows 포함): https://ollama.com/download

2) EXAONE GGUF 모델 로드용 Modelfile 생성/빌드
   - 본 저장소의 `Modelfile.exaone` 예시 사용 가능
   - 필요 시 특정 quant(예: Q4_K_M)로 경로 지정 (Hugging Face에서 해당 파일 확인)

   예)
   ```bash
   ollama create exaone-4-32b -f Modelfile.exaone
   ```

3) Ollama 서버 실행 확인
   - 기본: `http://localhost:11434`
   - 모델 테스트:
   ```bash
   ollama run exaone-4-32b "안녕"
   ```

환경 변수
--------
- `OLLAMA_BASE_URL` (기본 `http://localhost:11434`)
- `OLLAMA_MODEL` (기본 `exaone-4-32b`)
- `LLM_TEMPERATURE` (기본 `0.1`)
- `LLM_CONTEXT_TOKENS` (기본 `4096`)
- `ROBOT_HOST` (기본 `127.0.0.1`)
- `ROBOT_PORT` (기본 `5555`)
- `ROBOT_TRANSPORT` (`tcp` 또는 `udp`, 기본 `tcp`)
- `ACTION_NAME_FOLLOW` (기본 `따라가라`) – 소켓에 전송할 name 값
- `ACTION_NAME_BLOCK` (기본 `길을 막아라`) – 소켓에 전송할 name 값

설치 및 실행
-----------
```bash
python -m venv .venv
.venv/Scripts/activate  # Windows PowerShell
pip install -r requirements.txt

# 서버 실행 (기본 0.0.0.0:8000)
python main.py
```

브라우저에서 `http://localhost:8000` 접속 → 채팅 UI에서 메시지를 입력합니다.

동작 방식
--------
- 사용자가 "나를 따라와", "길을 막아" 등 명령을 하면 LLM이 대응하는 도구를 호출합니다.
- 도구 호출 시 관리자 PC에서 로봇으로 소켓 JSON을 전송합니다:
  - 예: `{"name": "따라가라", "value": 1}`
- 도구는 인자가 없으며, 호출만으로 동작합니다.

참고/주의
--------
- EXAONE 모델이 Ollama에서 OpenAI-style tool calling을 얼마나 잘 따르는지는 모델 버전에 따라 차이날 수 있습니다. 
  - 만약 도구 호출이 잘 이루어지지 않으면, 시스템 프롬프트를 강화하거나, Qwen/Llama3.1 등 툴콜 특화 모델로 교체 테스트를 권장합니다.
- 실제 로봇 주소/포트, TCP/UDP 여부는 환경 변수로 조정하세요.

파일 안내
--------
- `main.py`: FastAPI 진입점 및 `/chat` 엔드포인트
- `app/config.py`: 환경 변수/설정
- `app/robot.py`: 소켓 클라이언트 (TCP/UDP)
- `app/tools.py`: 두 개의 툴(따라가라/길을 막아라) 정의
- `app/graph.py`: LangGraph 구성 (모델+툴 연결, 대화 세션 유지)
- `web/index.html`: 최소한의 채팅 UI
- `Modelfile.exaone`: EXAONE GGUF용 Ollama 모델 정의 예시

