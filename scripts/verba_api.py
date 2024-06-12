import argparse
import requests
import json
import os
import base64
import time
import logging
import asyncio
import websockets

# Base URL for the API
BASE_URL = "http://192.168.2.79:8000"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("verbaAPI.log"),
    logging.StreamHandler()
])

STATE_FILE = 'state.json'

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as file:
        json.dump(state, file)

def update_state(state, filename, status):
    state[filename] = status
    save_state(state)

def serve_frontend():
    response = requests.get(f"{BASE_URL}/")
    print(json.dumps(response.json(), indent=4))

def health_check():
    response = requests.get(f"{BASE_URL}/api/health")
    print(json.dumps(response.json(), indent=4))

def get_status():
    response = requests.get(f"{BASE_URL}/api/get_status")
    print(json.dumps(response.json(), indent=4))

def retrieve_config():
    logging.info("Retrieving config...")
    response = requests.get(f"{BASE_URL}/api/config")
    if response.status_code == 200:
        config = response.json().get("data", {})
        logging.info("Config retrieved successfully.")
        return config
    else:
        logging.error("Failed to retrieve config.")
        return {}

async def websocket_generate_stream(query, context, conversation):
    uri = f"ws://192.168.2.79:8000/ws/generate_stream"
    async with websockets.connect(uri) as websocket:
        payload = json.dumps({
            "query": query,
            "context": context,
            "conversation": conversation
        })
        await websocket.send(payload)
        while True:
            try:
                response = await websocket.recv()
                print(json.dumps(json.loads(response), indent=4))
            except websockets.exceptions.ConnectionClosed:
                break

def reset_verba(reset_mode):
    payload = {"resetMode": reset_mode}
    response = requests.post(f"{BASE_URL}/api/reset", json=payload)
    print(json.dumps(response.json(), indent=4))

def get_md_files(directories_file):
    logging.info("Retrieving Markdown files...")
    md_files = []
    with open(directories_file, 'r') as file:
        directories = file.readlines()
        for directory in directories:
            directory = directory.strip()
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(".md") and file != "README.md":
                        md_files.append(os.path.join(root, file))
    return md_files

def get_json_files(directories_file):
    logging.info("Retrieving JSON files...")
    json_files = []
    with open(directories_file, 'r') as file:
        directories = file.readlines()
        for directory in directories:
            directory = directory.strip()
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(".json") and file != "config.json":
                        json_files.append(os.path.join(root, file))
    return json_files

def base64_encode_file(file_path):
    logging.info(f"Encoding file: {file_path}")
    with open(file_path, 'rb') as file:
        encoded_content = base64.b64encode(file.read()).decode('utf-8')
    return encoded_content

def generate_payload(md_files, json_files, state):
    logging.info("Generating payload...")
    data = []
    for file in md_files:
        if state.get(file) == "success":
            logging.info(f"Skipping already imported file: {file}")
            continue
        encoded_content = base64_encode_file(file)
        data.append({
            "filename": os.path.basename(file),
            "extension": "md",
            "content": encoded_content
        })
    for file in json_files:
        if state.get(file) == "success":
            logging.info(f"Skipping already imported json file: {file}")
            continue
        with open(file, 'r') as json_file:
            content = json.load(json_file)
        data.append({
            "filename": os.path.basename(file),
            "extension": "json",
            "content": content
        })
    return data

def import_data(directories_file, text_values, interval=60):
    logging.info("Importing data...")
    state = load_state()
    config = retrieve_config()
    if not config:
        logging.error("No configuration available. Exiting.")
        return
    
    while True:
        try:
            md_files = get_md_files(directories_file)
            json_files = get_json_files(directories_file)
            data = generate_payload(md_files, json_files, state)

            if not data:
                logging.info("No new files to import.")
            else:
                payload = {
                    "config": config,
                    "data": data,
                    "textValues": []
                }
                response = requests.post(f"{BASE_URL}/api/import", json=payload)
                result = response.json()
                logging.info(f"Import response: {json.dumps(result, indent=4)}")

                if response.status_code == 200:
                    for item in data:
                        update_state(state, item["filename"], "success")
                else:
                    logging.error("Failed to import data")
        
        except Exception as e:
            logging.error(f"Failed to import data: {e}")

        time.sleep(interval)

def update_config(config):
    payload = {"config": config}
    response = requests.post(f"{BASE_URL}/api/set_config", json=payload)
    print(json.dumps(response.json(), indent=4))

def query(query_text):
    payload = {"query": query_text}
    response = requests.post(f"{BASE_URL}/api/query", json=payload)
    print(json.dumps(response.json(), indent=4))

def suggestions(query_text):
    payload = {"query": query_text}
    response = requests.post(f"{BASE_URL}/api/suggestions", json=payload)
    print(json.dumps(response.json(), indent=4))

def get_document(document_id):
    payload = {"document_id": document_id}
    response = requests.post(f"{BASE_URL}/api/get_document", json=payload)
    print(json.dumps(response.json(), indent=4))

def get_all_documents(query, doc_type, page, page_size):
    payload = {
        "query": query,
        "doc_type": doc_type,
        "page": page,
        "pageSize": page_size
    }
    response = requests.post(f"{BASE_URL}/api/get_all_documents", json=payload)
    print(json.dumps(response.json(), indent=4))

def delete_document(document_id):
    payload = {"document_id": document_id}
    response = requests.post(f"{BASE_URL}/api/delete_document", json=payload)
    print(json.dumps(response.json(), indent=4))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="API Client")
    parser.add_argument("--serve_frontend", action="store_true", help="Serve Frontend")
    parser.add_argument("--health_check", action="store_true", help="Health Check")
    parser.add_argument("--get_status", action="store_true", help="Get Status Meta Data")
    parser.add_argument("--retrieve_config", action="store_true", help="Retrieve Configuration")
    parser.add_argument("--websocket_generate_stream", nargs=3, metavar=('QUERY', 'CONTEXT', 'CONVERSATION'), help="WebSocket Generate Stream")
    parser.add_argument("--reset_verba", metavar='RESET_MODE', help="Reset Verba")
    parser.add_argument("--import_data", nargs=2, metavar=('DIRECTORIES_FILE', 'INTERVAL'), help="Import Data Continually")
    parser.add_argument("--update_config", metavar='CONFIG', help="Update Config")
    parser.add_argument("--query", metavar='QUERY_TEXT', help="Query")
    parser.add_argument("--suggestions", metavar='QUERY_TEXT', help="Suggestions")
    parser.add_argument("--get_document", metavar='DOCUMENT_ID', help="Get Document")
    parser.add_argument("--get_all_documents", nargs=4, metavar=('QUERY', 'DOC_TYPE', 'PAGE', 'PAGE_SIZE'), help="Get All Documents")
    parser.add_argument("--delete_document", metavar='DOCUMENT_ID', help="Delete Document")

    args = parser.parse_args()

    if args.serve_frontend:
        serve_frontend()
    elif args.health_check:
        health_check()
    elif args.get_status:
        get_status()
    elif args.retrieve_config:
        retrieve_config()
    elif args.websocket_generate_stream:
        query, context, conversation = args.websocket_generate_stream
        asyncio.run(websocket_generate_stream(query, context, conversation))
    elif args.reset_verba:
        reset_verba(args.reset_verba)
    elif args.import_data:
        directories_file, interval = args.import_data
        text_values = '{"textKey1": "textValue1", "textKey2": "textValue2"}'  # Example text values
        import_data(directories_file, text_values, int(interval))
    elif args.update_config:
        update_config(args.update_config)
    elif args.query:
        query(args.query)
    elif args.suggestions:
        suggestions(args.suggestions)
    elif args.get_document:
        get_document(args.get_document)
    elif args.get_all_documents:
        query, doc_type, page, page_size = args.get_all_documents
        get_all_documents(query, doc_type, int(page), int(page_size))
    elif args.delete_document:
        delete_document(args.delete_document)
