# server.py
from flask import Flask, jsonify, send_from_directory
from flask_socketio import SocketIO
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading, time, os

# Path setup 
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EXPORTS_FOLDER = os.path.join(PROJECT_ROOT, 'blender_exports')
STATIC_FOLDER = os.path.join(PROJECT_ROOT, 'viewer')

print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"STATIC_FOLDER: {STATIC_FOLDER} | exists: {os.path.exists(STATIC_FOLDER)}")
print(f"EXPORTS_FOLDER: {EXPORTS_FOLDER} | exists: {os.path.exists(EXPORTS_FOLDER)}")

# Flask app setup
app = Flask(__name__, static_folder='viewer', static_url_path='')
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/debug')
def debug():
    return {
        'PROJECT_ROOT': PROJECT_ROOT,
        'STATIC_FOLDER': STATIC_FOLDER,
        'EXPORTS_FOLDER': EXPORTS_FOLDER,
        'static_exists': os.path.exists(STATIC_FOLDER),
        'exports_exists': os.path.exists(EXPORTS_FOLDER),
        'static_files': os.listdir(STATIC_FOLDER) if os.path.exists(STATIC_FOLDER) else None,
    }

# API endpoint to get the most recent GLB file
@app.route('/latest-model')
def latest_model():
    if not os.path.exists(EXPORTS_FOLDER):
        return jsonify(error='Exports folder not found'), 404
    
    glbs = [f for f in os.listdir(EXPORTS_FOLDER) if f.endswith('.glb')]
    if not glbs:
        return jsonify(error='No .glb files found'), 404
    
    # Find newest file by modification time
    latest = max(glbs, key=lambda f: os.path.getmtime(os.path.join(EXPORTS_FOLDER, f)))
    return jsonify(filename=latest)

# Serve GLB files directly
@app.route('/blender_exports/<path:filename>')
def serve_glb(filename):
    return send_from_directory(EXPORTS_FOLDER, filename)

# File watcher for hot reloading
class GLBHandler(FileSystemEventHandler):
    _last_emit = 0  # Simple debounce mechanism
    
    def _maybe_emit(self, path):
        if not path.endswith('.glb'):
            return
        
        now = time.time()
        if now - GLBHandler._last_emit < 0.5:  # Half-second debounce
            return
        
        GLBHandler._last_emit = now
        print(f'[watchdog] GLB updated: {os.path.basename(path)}')
        socketio.emit('model_updated')
    
    def on_created(self, event):
        self._maybe_emit(event.src_path)
    
    def on_modified(self, event):
        self._maybe_emit(event.src_path)
    
    def on_moved(self, event):
        self._maybe_emit(event.dest_path)

def start_watcher():
    print(f'[watchdog] Monitoring: {EXPORTS_FOLDER}')
    observer = Observer()
    observer.schedule(GLBHandler(), path=EXPORTS_FOLDER, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# Start everything up
if __name__ == '__main__':
    # Run file watcher in background thread
    threading.Thread(target=start_watcher, daemon=True).start()
    
    # Start Flask server 
    socketio.run(app, port=5000, debug=True, use_reloader=False)