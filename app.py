import os
import threading
import time
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from main import Downloader

app = Flask(__name__)
CORS(app)

# Global state for progress tracking
current_status = {
    "status": "idle", # idle, downloading, error, success
    "message": "Ready",
    "progress": 0,
    "total": 0,
    "filename": "",
    "logs": [],
    "completed_link": None
}

def progress_callback(downloaded, total, filepath):
    current_status["status"] = "downloading"
    current_status["progress"] = (downloaded / total) * 100 if total > 0 else 0
    current_status["total"] = total
    current_status["filename"] = os.path.basename(filepath)
    current_status["message"] = f"Downloading {os.path.basename(filepath)}"

def log_callback(type, message, obj):
    log_entry = f"[{type.upper()}] {message}: {obj}"
    current_status["logs"].append(log_entry)
    if len(current_status["logs"]) > 50:
        current_status["logs"].pop(0)
    
    if type == 'error':
        # Don't set global status to error immediately if we are processing a queue, 
        # just log it. The queue loop handles flow.
        pass 

def run_download(links, folder):
    current_status["logs"] = []
    current_status["progress"] = 0
    current_status["status"] = "starting"
    
    downloader = Downloader(download_folder=folder, progress_callback=progress_callback, log_callback=log_callback)
    
    for link in links:
        link = link.strip()
        if not link: continue
        
        current_status["message"] = f"Processing {link[:30]}..."
        current_status["completed_link"] = None # Reset
        
        try:
            downloader.process_link(link)
            # Signal that this link is done
            current_status["completed_link"] = link
            time.sleep(0.1) # Give frontend time to pick it up
        except Exception as e:
            log_callback("error", "Unexpected error", str(e))
            
    current_status["status"] = "success"
    current_status["message"] = "All downloads finished"
    current_status["progress"] = 100

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def start_download():
    data = request.json
    links = data.get('links') # Expecting a list
    folder = data.get('folder')
    
    if not links or not folder:
        return jsonify({"error": "Missing links or folder"}), 400
    
    if current_status["status"] == "downloading":
        return jsonify({"error": "Download already in progress"}), 409

    thread = threading.Thread(target=run_download, args=(links, folder))
    thread.start()
    
    return jsonify({"message": "Download started"})

@app.route('/api/progress')
def progress():
    def generate():
        while True:
            import json
            yield f"data: {json.dumps(current_status)}\n\n"
            time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/browse', methods=['GET'])
def browse():
    path = request.args.get('path', os.path.expanduser("~"))
    if not os.path.exists(path):
        return jsonify({"error": "Path does not exist"}), 404
        
    try:
        items = []
        # Add parent directory
        parent = os.path.dirname(path)
        items.append({"name": "..", "path": parent, "type": "dir"})
        
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path) and not item.startswith('.'):
                items.append({"name": item, "path": full_path, "type": "dir"})
        
        items.sort(key=lambda x: x['name'])
        return jsonify({"current_path": path, "items": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mkdir', methods=['POST'])
def make_directory():
    data = request.json
    path = data.get('path')
    name = data.get('name')
    
    if not path or not name:
        return jsonify({"error": "Missing path or name"}), 400
        
    new_dir_path = os.path.join(path, name)
    
    try:
        os.makedirs(new_dir_path, exist_ok=False)
        return jsonify({"message": "Directory created", "path": new_dir_path})
    except FileExistsError:
        return jsonify({"error": "Directory already exists"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
