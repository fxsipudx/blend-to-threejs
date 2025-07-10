import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration: Set the folder to watch and supported file formats
EXPORTS_FOLDER = "/Users/shubhamjena/Desktop/Personal projects/blend-to-vred/blender_exports"
SUPPORTED_FORMATS = ['.fbx', '.obj', '.dae', '.3ds', '.ply', '.stl', '.x3d', '.gltf', '.glb']

# Handler class that reacts to file changes in the watched folder
class VREDModelHandler(FileSystemEventHandler):
    _last_reload = 0  # Used to prevent too-frequent reloads (debounce)
    _current_model_node = None  # Stores the currently loaded model node in VRED
    
    def _should_reload(self, path):
        # Checks if the file is a supported format and if enough time has passed since last reload
        if not any(path.lower().endswith(ext) for ext in SUPPORTED_FORMATS):
            return False
        now = time.time()
        if now - VREDModelHandler._last_reload < 1.5:
            return False
        VREDModelHandler._last_reload = now
        return True
    
    def _reload_model(self, filepath):
        # Loads a new model into VRED, removing the old one if present
        try:
            print(f"[VRED] Loading: {os.path.basename(filepath)}")
            # Remove previous model if it exists
            if VREDModelHandler._current_model_node:
                try:
                    # Try to remove using the node's remove method, or fallback to VRED's service
                    if hasattr(VREDModelHandler._current_model_node, 'remove'):
                        VREDModelHandler._current_model_node.remove()
                    else:
                        vrNodeService.removeNode(VREDModelHandler._current_model_node)
                    print("[VRED] Removed previous model")
                except Exception as e:
                    print(f"[VRED] Warning: Could not remove previous model - {e}")
            # Load the new model file
            try:
                VREDModelHandler._current_model_node = vrFileIO.load(filepath)
            except Exception as e:
                print(f"[VRED] Error loading file: {e}")
                return
            if VREDModelHandler._current_model_node:
                print(f"[VRED] Successfully loaded: {os.path.basename(filepath)}")
                # Fit the camera to the new model
                try:
                    camera = vrCameraService.getActiveCamera()
                    if camera:
                        camera.fitAll()
                    else:
                        vrCamera.fitAll()
                except Exception as e:
                    print(f"[VRED] Warning: Could not fit camera - {e}")
                # Update scene materials and lighting
                self._update_scene()
                # Refresh the VRED viewport
                try:
                    vrController.vrRefresh()
                except Exception as e:
                    print(f"[VRED] Warning: Could not refresh viewport - {e}")
            else:
                print(f"[VRED] Failed to load: {filepath}")
        except Exception as e:
            print(f"[VRED] Error loading model: {e}")
    
    def _update_scene(self):
        # Updates materials and lighting in the scene for consistency
        try:
            # Update all materials' properties if possible
            if hasattr(vrMaterialService, 'getAllMaterials'):
                materials = vrMaterialService.getAllMaterials()
                for material in materials:
                    try:
                        if hasattr(material, 'setRoughness'):
                            material.setRoughness(0.5)
                        if hasattr(material, 'setMetallic'):
                            material.setMetallic(0.0)
                    except Exception as e:
                        print(f"[VRED] Warning: Could not update material - {e}")
                        continue
            # Set ambient light intensity if possible
            if hasattr(vrLightService, 'setAmbientLightIntensity'):
                try:
                    vrLightService.setAmbientLightIntensity(0.3)
                except Exception as e:
                    print(f"[VRED] Warning: Could not set ambient light - {e}")
        except Exception as e:
            print(f"[VREZ] Error updating scene: {e}")
    
    def _ensure_valid_path(self, path):
        # Checks if the file exists and is not being written to (size is stable)
        if not os.path.exists(path):
            return False
        try:
            size1 = os.path.getsize(path)
            time.sleep(0.1)
            size2 = os.path.getsize(path)
            return size1 == size2
        except:
            return False
    
    def on_created(self, event):
        # Called when a new file is created in the watched folder
        if self._should_reload(event.src_path) and self._ensure_valid_path(event.src_path):
            time.sleep(0.5)  # Wait a bit to ensure file is fully written
            self._reload_model(event.src_path)
    
    def on_modified(self, event):
        # Called when a file is modified in the watched folder
        if self._should_reload(event.src_path) and self._ensure_valid_path(event.src_path):
            time.sleep(0.5)
            self._reload_model(event.src_path)
    
    def on_moved(self, event):
        # Called when a file is moved/renamed into the watched folder
        if self._should_reload(event.dest_path) and self._ensure_valid_path(event.dest_path):
            self._reload_model(event.dest_path)

def check_vred_environment():
    # Checks if the script is running inside VRED by looking for required modules
    required_modules = ['vrFileIO', 'vrNodeService', 'vrController']
    missing_modules = []
    for module in required_modules:
        try:
            globals()[module]
        except NameError:
            missing_modules.append(module)
    if missing_modules:
        print(f"[VRED] Warning: Missing modules: {missing_modules}")
        print("[VRED] Make sure this script is running in VRED's Python environment")
        return False
    return True

def start_file_watcher():
    # Starts the Watchdog observer to monitor the exports folder for changes
    if not os.path.exists(EXPORTS_FOLDER):
        print(f"[VRED] ERROR: Exports folder not found: {EXPORTS_FOLDER}")
        print("[VRED] Please check the EXPORTS_FOLDER path and try again")
        return
    if not check_vred_environment():
        print("[VRED] ERROR: VRED environment not properly set up")
        return
    print(f"[VRED] Starting file watcher on: {EXPORTS_FOLDER}")
    print(f"[VRED] Watching for files: {', '.join(SUPPORTED_FORMATS)}")
    observer = Observer()
    observer.schedule(VREDModelHandler(), path=EXPORTS_FOLDER, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)  # Keep the watcher running
    except KeyboardInterrupt:
        print("[VRED] Stopping file watcher...")
        observer.stop()
    except Exception as e:
        print(f"[VRED] Error in file watcher: {e}")
        observer.stop()
    observer.join()

def load_latest_model():
    # Loads the most recently modified model file on startup
    if not os.path.exists(EXPORTS_FOLDER):
        print(f"[VRED] ERROR: Exports folder not found: {EXPORTS_FOLDER}")
        return
    model_files = []
    try:
        for file in os.listdir(EXPORTS_FOLDER):
            if any(file.lower().endswith(ext) for ext in SUPPORTED_FORMATS):
                filepath = os.path.join(EXPORTS_FOLDER, file)
                if os.path.isfile(filepath):
                    model_files.append((filepath, os.path.getmtime(filepath)))
    except Exception as e:
        print(f"[VRED] Error scanning exports folder: {e}")
        return
    if not model_files:
        print("[VRED] No model files found in exports folder")
        return
    latest_file = max(model_files, key=lambda x: x[1])[0]
    handler = VREDModelHandler()
    handler._reload_model(latest_file)

def get_vred_version():
    # Tries to get the VRED version for logging/debugging
    try:
        if hasattr(vrController, 'getVersion'):
            return vrController.getVersion()
        else:
            return "Unknown"
    except:
        return "Unknown"

def main():
    # Main entry point: checks environment, loads latest model, starts watcher
    print("[VRED] Auto-loader starting...")
    print(f"[VRED] Version: {get_vred_version()}")
    if not check_vred_environment():
        print("[VRED] ERROR: Cannot run outside VRED environment")
        return
    load_latest_model()  # Load the latest model at startup
    try:
        watcher_thread = threading.Thread(target=start_file_watcher, daemon=True)
        watcher_thread.start()
        print("[VRED] Auto-loader running. Export from Blender to see live updates!")
        print("[VRED] Press Ctrl+C in console to stop")
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        print("\n[VRED] Shutting down auto-loader...")
    except Exception as e:
        print(f"[VRED] Error in main loop: {e}")

# Run the script if executed directly or imported in VRED
if __name__ == "__main__":
    main()
else:
    main()