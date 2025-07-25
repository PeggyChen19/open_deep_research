import os
import json
import requests
import shutil

API_URL = "http://192.168.200.152:8000/aireport/stream"
params = {
    "agent": "6e760228dd0a4bd5982306bba7c85381",
    "gte": 1753006213,
    "lte": 1753427819
}
OUTPUT_DIR = "output_md"

if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR)

with requests.post(API_URL, params=params, stream=True) as response:
    response.encoding = "utf-8"
    if response.status_code != 200:
        print("API Call Failed:", response.status_code, response.text)
        exit(1)

    print(f"Streaming from API, storing Markdown files in ./{OUTPUT_DIR}/")

    file_count = 0
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue

        try:
            data = line[5:].strip()
            data = json.loads(data)
        except json.JSONDecodeError:
            print("JSON Decode Error:", line)
            continue

        if "content" in data:
            file_count += 1
            file_path = os.path.join(OUTPUT_DIR, f"{file_count}_{data['type']}_{data['total_time']}_{data['phase_time']}.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(data["content"])
            print(f"Wrote {file_path}")

print("Streaming complete. Total files created:", file_count)