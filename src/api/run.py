import time
import requests
import json

start_time = time.time()

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer  eyJhbGciOiJIUzI1NiIsImtpZCI6IjcyT1hpUXB5elBZeEhxRCsiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2p6aHpteXlieWF3eHBubGJta2NhLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJhODRlYzg2Zi0zMDRmLTQ0MjAtYWJmNS01NTIxYWNiODUwMzYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzUzMzI3NTEwLCJpYXQiOjE3NTMzMjM5MTAsImVtYWlsIjoicGVnZ3kuY2hlbkBjaGFpbnNlY3VyaXR5LmFzaWEiLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoicGVnZ3kuY2hlbkBjaGFpbnNlY3VyaXR5LmFzaWEiLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwicGhvbmVfdmVyaWZpZWQiOmZhbHNlLCJzdWIiOiJhODRlYzg2Zi0zMDRmLTQ0MjAtYWJmNS01NTIxYWNiODUwMzYifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc1MzMyMzkxMH1dLCJzZXNzaW9uX2lkIjoiYjhmNTcwMjAtN2UwYi00Y2VjLWJjNmUtN2U4OTk2NDY5YWRhIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.Mo_0rMyyr9j0CZAPXNWBAjkBBVvTrkndpulW5NDXisQ"
}
url_create = "http://127.0.0.1:2024/threads"
payload_create = {
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
thread_id = None
try:
    response = requests.post(url_create, headers=headers, json=payload_create)
    if response.content.strip():
        try:
            data = response.json()
            print(json.dumps(data, indent=2))
            thread_id = data.get("thread_id")
        except json.JSONDecodeError:
            print("❌ Failed to decode JSON response:")
            print(response.text)
    else:
        print("⚠️ No content returned from server.")
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    print(f"❌ HTTP error: {e.response.status_code} - {e.response.text}")
except requests.exceptions.RequestException as e:
    print(f"❌ Request failed: {e}")

url_run = f"http://127.0.0.1:2024/threads/{thread_id}/runs/wait"

payload_run = {
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
    "values", "messages"
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

output_file = "output.json"

response = requests.post(url_run, headers=headers, json=payload_run)
if response.status_code == 200:
    try:
        data = response.json()
        with open(output_file, "w", encoding="utf-8") as f:
            def process_item(item):
                result = {}
                if "research_brief" in item:
                    result["research_brief"] = item["research_brief"]
                if "supervisor_messages" in item:
                    filtered = [
                        msg["content"]
                        for msg in item["supervisor_messages"]
                        if msg.get("type") in {"tool", "ai"} and msg.get("content")
                    ]
                    result["chain_of_thought"] = filtered
                if "final_report" in item:
                    result["final_report"] = item["final_report"]
                return result

            filtered = process_item(data)
            output_data = {
                "filtered_result": filtered,
                "raw_response": data
            }
            f.write(json.dumps(output_data, ensure_ascii=False) + "\n")
    except json.JSONDecodeError:
        print("❌ Failed to decode JSON response.")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(response.text + "\n")
else:
    print("❌ Error:", response.status_code, response.text)


end_time = time.time()
elapsed_time = end_time - start_time
print(f"⏱️ Total execution time: {elapsed_time:.2f} seconds")
