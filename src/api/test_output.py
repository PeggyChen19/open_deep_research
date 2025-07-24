import os
import json
import requests
import shutil

API_URL = "http://192.168.200.152:8000/aireport/stream"
OUTPUT_DIR = "output_md"

if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR)

with requests.get(API_URL, stream=True) as response:
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
            data = json.loads(line)
        except json.JSONDecodeError:
            print("JSON Decode Error:", line)
            continue

        if "content" in data:
            file_count += 1
            file_path = os.path.join(OUTPUT_DIR, f"{file_count}_{data['type']}.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(data["content"])
            print(f"Wrote {file_path}")

print("Streaming complete. Total files created:", file_count)