import time
import requests
import json
from fastapi import FastAPI
from fastapi import status
from fastapi.responses import StreamingResponse,JSONResponse
from src.api.auth_supabase import get_valid_token
from typing import Generator
from dotenv import load_dotenv

load_dotenv(".env")

app = FastAPI()

AI_SERVER_BASE = "http://127.0.0.1:2024"

def create_thread() -> str:
    headers = {
        "Authorization": f"Bearer {get_valid_token()}",
        "Content-Type": "application/json"
    }
    url = f"{AI_SERVER_BASE}/threads"
    payload = {
        "thread_id": "",
        "metadata": {
            "graph_id": "Deep Researcher"
        },
        "if_exists": "raise",
        "ttl": {
            "strategy": "delete",
            "ttl": 1
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json().get("thread_id")
        else:
            print("Create thread failed:", response.status_code, response.text)
            return None
    except Exception as e:
        print("Exception in create_thread:", str(e))
        return None

def stream_from_ai_server(thread_id: str) -> Generator[str, None, None]:
    headers = {
        "Authorization": f"Bearer {get_valid_token()}",
        "Content-Type": "application/json"
    }
    url = f"{AI_SERVER_BASE}/threads/{thread_id}/runs/stream"
    payload = {
        "assistant_id": "Deep Researcher",
        "checkpoint": {
            "thread_id": "",
            "checkpoint_ns": "",
            "checkpoint_id": "",
            "checkpoint_map": {}
        },
        "input": {},
        "command": {
            "goto": {
            "node": "__start__",
            "input": {
                "messages": [
                {
                    "type": "human",
                    "content": ""
                }
                ]
            }
            }
        },
        "metadata": {},
        "config": {
            "tags": [
            ""
            ],
            "recursion_limit": 100,
            "configurable": {}
        },
        "webhook": "https://webhook.site/622147f4-6dc3-42f9-8206-1a4fd211c50a",
        "interrupt_before": [],
        "interrupt_after": [],
        "stream_mode": [
            "values"
        ],
        "stream_subgraphs": True,
        "stream_resumable": False,
        "on_disconnect": "cancel",
        "feedback_keys": [
            ""
        ],
        "multitask_strategy": "reject",
        "if_not_exists": "reject",
        "after_seconds": 1,
        "checkpoint_during": False
    }

    with requests.post(url, headers=headers, json=payload, stream=True) as response:
        if response.status_code != 200:
            raise RuntimeError(f"AI Server Create Streaming Run Error: {response.status_code} {response.text}")

        got_research_brief = False
        global_start_time = time.time()
        phase_start_time = time.time()
        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data:"):
                data = line[5:].strip()
                try:
                    json_obj = json.loads(data)
                    if "research_brief" in json_obj and not got_research_brief:
                        got_research_brief = True
                        global_time = int(time.time() - global_start_time)
                        phase_time = int(time.time() - phase_start_time)
                        yield f"{json.dumps({'type': 'research_brief', 'content': json_obj['research_brief'], 'total_time': global_time, 'phase_time': phase_time})}\n\n"
                        phase_start_time = time.time()

                    if "compressed_research" in json_obj:
                        global_time = int(time.time() - global_start_time)
                        phase_time = int(time.time() - phase_start_time)
                        yield f"{json.dumps({'type': 'chain_of_thought', 'content': json_obj['compressed_research'], 'total_time': global_time, 'phase_time': phase_time})}\n\n"
                        phase_start_time = time.time()

                    if "final_report" in json_obj:
                        global_time = int(time.time() - global_start_time)
                        phase_time = int(time.time() - phase_start_time)
                        yield f"{json.dumps({'type': 'final_report', 'content': json_obj['final_report'], 'total_time': global_time, 'phase_time': phase_time})}\n\n"

                except json.JSONDecodeError:
                    global_time = int(time.time() - global_start_time)
                    phase_time = int(time.time() - phase_start_time)
                    yield f"{json.dumps({'type': 'raw', 'content': data, 'total_time': global_time, 'phase_time': phase_time})}\n\n"

@app.get("/aireport/stream")
def stream_handler():
    try:
        thread_id = create_thread()
        if not thread_id:
            return JSONResponse({"error": "Failed to create thread"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return StreamingResponse(
            stream_from_ai_server(thread_id),
            media_type="text/event-stream",
            status_code=200
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=status.HTTP_502_BAD_GATEWAY)