import json
import os
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import argparse
from dotenv import load_dotenv
load_dotenv(".env")

event_id_fields = {
    "1001": [
        "ErrorCode", "Stage", "FailureType", "Reason", "Retries", "OSVersion",
        "PackageName", "PackageVersion", "Architecture", "InstallContext", "ErrorHex",
        "InstallSource", "PackageState", "ExpectedState", "InstallMethod", "LogPaths",
        "ReportPath", "Reserved1", "RetryCount", "ReportId", "SomethingElse", "ExtraField", "FinalField"
    ]
}

def retreive_raw_data_from_elasticsearch(agent, gte, lte):
    url = os.getenv("ELASTICSEARCH_URL") + '/ed_collection/_search?pretty'
    headers = {
        'Content-Type': 'application/json'
    }
    payload = {
        "size": 10000,
        "_source": ["eventsystem", "eventapplication", "eventsecurity"],
        "query": {
            "bool": {
                "must": [
                    {"term": {"agent": agent}}
                ],
                "filter": [
                    {"range": {"date_main": {"gte": gte, "lte": lte}}},
                    {
                        "bool": {
                            "should": [
                                {"exists": {"field": "eventsystem"}},
                                {"exists": {"field": "eventapplication"}},
                                {"exists": {"field": "eventsecurity"}}
                            ],
                            "minimum_should_match": 1
                        }
                    }
                ]
            }
        },
        "sort": [{"date_main": {"order": "asc"}}]
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

def xml_element_to_custom_json(elem):
    node = {}
    
    # Handle attributes
    for attr, val in elem.attrib.items():
        node[f"_{attr}"] = val

    # Handle children nodes
    children = list(elem)
    if children:
        for child in children:
            tag = child.tag.split("}")[-1]
            child_data = xml_element_to_custom_json(child)
            if tag in node:
                if not isinstance(node[tag], list):
                    node[tag] = [node[tag]]
                node[tag].append(child_data)
            else:
                node[tag] = child_data
    else:
        text = elem.text.strip() if elem.text else ""
        if node:
            if text:
                node["__text"] = text
        else:
            node = text
    return node

def parse_evtrenderdata_preserve_structure(xml_str):
    root = ET.fromstring(xml_str)
    ns = root.tag.split("}")[0][1:] if "}" in root.tag else None
    result = {}
    tag = root.tag.split("}")[-1]
    result[tag] = xml_element_to_custom_json(root)
    if ns:
        result[tag]["_xmlns"] = ns
    return result

def extract_evtrenderdata_only(entry):
    for key in ["eventapplication", "eventsecurity", "eventsystem"]:
        if key in entry and "evtrenderdata" in entry[key]:
            xml_str = entry[key]["evtrenderdata"]
            return {key: parse_evtrenderdata_preserve_structure(xml_str)}
    return {}

def trim_nanosecond_z_format_fixed(time_str):
    try:
        if time_str.endswith("Z"):
            time_str = time_str[:-1]
        if "." in time_str:
            prefix, fractional = time_str.split(".")
            time_str = f"{prefix}.{fractional[:6]}"
            dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f")
        else:
            dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return time_str

def flatten_event(event_wrapper: dict):
    root_key = list(event_wrapper.keys())[0]
    event = event_wrapper[root_key]["Event"]

    provider = event["System"]["Provider"].get("_Name", "")
    event_id = event["System"].get("EventID", "")
    if isinstance(event_id, dict):
        event_id = event_id.get("__text", "")

    raw_time = event["System"]["TimeCreated"].get("_SystemTime", "")
    time_created = trim_nanosecond_z_format_fixed(raw_time)

    channel = event["System"].get("Channel", "")
    computer = event["System"].get("Computer", "")

    security = event["System"].get("Security", {})
    security_user_id = security.get("_UserID", "") if isinstance(security, dict) else ""

    # Handle EventData
    flat_data = {}
    event_data = event.get("EventData", {})
    data_block = []

    if isinstance(event_data, dict):
        data_block = event_data.get("Data", [])
    elif isinstance(event_data, str):
        flat_data = {"message": event_data}
        return {
            "provider": provider,
            "event_id": event_id,
            "time_created": time_created,
            "channel": channel,
            "computer": computer,
            "security_user_id": security_user_id,
            "event_data": flat_data
        }
    elif isinstance(event_data, list):
        data_block = event_data
    else:
        flat_data = {"message": str(event_data)}
        return {
            "provider": provider,
            "event_id": event_id,
            "time_created": time_created,
            "channel": channel,
            "computer": computer,
            "security_user_id": security_user_id,
            "event_data": flat_data
        }

    # Handle data_block
    if isinstance(data_block, dict) and "_Name" in data_block:
        flat_data[data_block["_Name"]] = data_block.get("__text", "")

    elif isinstance(data_block, list):
        if all(isinstance(d, dict) and "_Name" in d for d in data_block):
            for d in data_block:
                key = d.get("_Name")
                value = d.get("__text", "")
                if key == "PrivilegeList" and "\n" in value:
                    value = [v.strip() for v in value.strip().split("\n") if v.strip()]
                flat_data[key] = value
        elif all(isinstance(d, str) for d in data_block):
            if event_id in event_id_fields:
                fields = event_id_fields[event_id]
                flat_data = {
                    fields[i]: data_block[i]
                    for i in range(min(len(fields), len(data_block)))
                }
            else:
                flat_data = {"data": data_block}

    elif isinstance(data_block, str):
        flat_data["message"] = data_block

    return {
        "provider": provider,
        "event_id": event_id,
        "time_created": time_created,
        "channel": channel,
        "computer": computer,
        "security_user_id": security_user_id,
        "event_data": flat_data
    }

def stringify(value):
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    elif isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    else:
        return str(value)

def flatten_event_verbose(event):
    lines = []
    lines.append(f"Time: {event.get('time_created')}")
    lines.append(f"Event ID: {event.get('event_id')}")
    lines.append(f"Provider: {event.get('provider')}")
    lines.append(f"Computer: {event.get('computer')}")
    lines.append(f"Channel: {event.get('channel')}")

    # Flatten event_data if present
    event_data = event.get("event_data", {})
    if event_data:
        lines.append("Event Data:")
        for key, value in event_data.items():
            lines.append(f"  - {key}: {stringify(value)}")

    return "\n".join(lines)

def convert_json_to_llm_docs(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs = [flatten_event_verbose(entry) for entry in data]

    with open(output_path, "w", encoding="utf-8") as f:
        for doc in docs:
            f.write(doc + "\n---\n")

    print(f"Output {len(docs)} events to {output_path}")

def retrieve_data(agent: str, gte: int, lte: int):
    raw_data_path = Path("src/open_deep_research/data/raw_data.json")
    simplified_data_path = Path("src/open_deep_research/data/simplified_data.json")
    llm_docs_path = Path("src/open_deep_research/data/llm_docs.txt")

    raw_data = retreive_raw_data_from_elasticsearch(agent, gte, lte)
    with open(raw_data_path, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)
    print(f"Saved raw data to {raw_data_path}")

    logs = [hit["_source"] for hit in raw_data["hits"]["hits"]]
    extracted = [extract_evtrenderdata_only(entry) for entry in logs]
    simplified_data = [flatten_event(evt) for evt in extracted]

    with simplified_data_path.open("w", encoding="utf-8") as f:
        json.dump(simplified_data, f, ensure_ascii=False, indent=2)

    print(f"Write {len(logs)} simplified logs to {simplified_data_path}")

    convert_json_to_llm_docs(simplified_data_path, llm_docs_path)
    print("Converted simplified data to LLM docs format.")

def main():
    parser = argparse.ArgumentParser(description="Retrieve and process event data.")
    parser.add_argument("--agent", type=str, required=True, help="Agent name to filter logs")
    parser.add_argument("--gte", type=int, required=True, help="Start timestamp for filtering")
    parser.add_argument("--lte", type=int, required=True, help="End timestamp for filtering")
    args = parser.parse_args()

    retrieve_data(args.agent, args.gte, args.lte)

if __name__ == "__main__":
    main()