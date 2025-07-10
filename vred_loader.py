import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
EXPORTS_FOLDER = "/Users/shubhamjena/Desktop/Personal projects/blend-to-vred/blender_exports"
SUPPORTED_FORMATS = ['.fbx', '.obj', '.dae', '.3ds', '.ply', '.stl', '.x3d', '.gltf', '.glb']

class VREDModelHandler(FileSystemEventHandler):
    _last_reload = 0
    _current_model_node = None
    
    def _should_reload(self, path):
        # Check if file should trigger a reload
        if not any(path.lower().endswith(ext) for ext in SUPPORTED_FORMATS):
            return False
        
        # Enhanced debounce - wait 1.5 seconds between reloads
        now = time.time()
        if now - VREDModelHandler._last_reload < 1.5:
            return False
        
        VREDModelHandler._last_reload = now
        return True
    
    def _reload_model(self, filepath):
        # Load new model in VRED using updated API
        try:
            print(f"[VRED] Loading: {os.path.basename(filepath)}")
            
            # Remove previous model if exists
            if VREDModelHandler._current_model_node:
                try:
                    # Updated API for node removal
                    if hasattr(VREDModelHandler._current_model_node, 'remove'):
                        VREDModelHandler._current_model_node.remove()
                    else:
                        vrNodeService.removeNode(VREDModelHandler._current_model_node)
                    print("[VRED] Removed previous model")
                except Exception as e:
                    print(f"[VRED] Warning: Could not remove previous model - {e}")
            
            # Load new model with better error handling
            try:
                VREDModelHandler._current_model_node = vrFileIO.load(filepath)
            except Exception as e:
                print(f"[VRED] Error loading file: {e}")
                return
            
            if VREDModelHandler._current_model_node:
                print(f"[VRED] Successfully loaded: {os.path.basename(filepath)}")
                
                # Use updated camera service API instead of deprecated vrCamera
                try:
                    # Updated way to fit all using camera service
                    camera = vrCameraService.getActiveCamera()
                    if camera:
                        camera.fitAll()
                    else:
                        # Fallback to deprecated method if new one not available
                        vrCamera.fitAll()
                except Exception as e:
                    print(f"[VRED] Warning: Could not fit camera - {e}")
                
                # Update scene with better error handling
                self._update_scene()
                
                # Refresh viewport
                try:
                    vrController.vrRefresh()
                except Exception as e:
                    print(f"[VRED] Warning: Could not refresh viewport - {e}")
            else:
                print(f"[VRED] Failed to load: {filepath}")
                
        except Exception as e:
            print(f"[VRED] Error loading model: {e}")
    
    def _update_scene(self):
        # Updated scene modifications for newer VRED versions
        try:
            # Example: Use updated material service
            if hasattr(vrMaterialService, 'getAllMaterials'):
                materials = vrMaterialService.getAllMaterials()
                for material in materials:
                    try:
                        # Updated material property setting
                        if hasattr(material, 'setRoughness'):
                            material.setRoughness(0.5)
                        if hasattr(material, 'setMetallic'):
                            material.setMetallic(0.0)
                    except Exception as e:
                        print(f"[VRED] Warning: Could not update material - {e}")
                        continue
            
            # Example: Updated lighting service
            if hasattr(vrLightService, 'setAmbientLightIntensity'):
                try:
                    vrLightService.setAmbientLightIntensity(0.3)
                except Exception as e:
                    print(f"[VRED] Warning: Could not set ambient light - {e}")
            
        except Exception as e:
            print(f"[VREZ] Error updating scene: {e}")
    
    def _ensure_valid_path(self, path):
        # Ensure path exists and is accessible
        if not os.path.exists(path):
            return False
        
        # Check if file is still being written to
        try:
            size1 = os.path.getsize(path)
            time.sleep(0.1)
            size2 = os.path.getsize(path)
            return size1 == size2
        except:
            return False
    
    def on_created(self, event):
        if self._should_reload(event.src_path) and self._ensure_valid_path(event.src_path):
            # Small delay to ensure file is fully written
            time.sleep(0.5)
            self._reload_model(event.src_path)
    
    def on_modified(self, event):
        if self._should_reload(event.src_path) and self._ensure_valid_path(event.src_path):
            # Small delay to ensure file is fully written
            time.sleep(0.5)
            self._reload_model(event.src_path)
    
    def on_moved(self, event):
        if self._should_reload(event.dest_path) and self._ensure_valid_path(event.dest_path):
            self._reload_model(event.dest_path)

def check_vred_environment():
    # Check if VRED environment is properly set up
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
    # Start monitoring the exports folder with better error handling
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
            time.sleep(1)
    except KeyboardInterrupt:
        print("[VRED] Stopping file watcher...")
        observer.stop()
    except Exception as e:
        print(f"[VRED] Error in file watcher: {e}")
        observer.stop()
    
    observer.join()

def load_latest_model():
    # Load the most recent model on startup with better error handling
    if not os.path.exists(EXPORTS_FOLDER):
        print(f"[VRED] ERROR: Exports folder not found: {EXPORTS_FOLDER}")
        return
    
    # Find all supported model files
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
    
    # Get the newest file
    latest_file = max(model_files, key=lambda x: x[1])[0]
    
    # Load it
    handler = VREDModelHandler()
    handler._reload_model(latest_file)

def get_vred_version():
    # Get VRED version info for compatibility checking
    try:
        if hasattr(vrController, 'getVersion'):
            return vrController.getVersion()
        else:
            return "Unknown"
    except:
        return "Unknown"

def main():
    # Main entry point with improved error handling
    print("[VRED] Auto-loader starting...")
    print(f"[VRED] Version: {get_vred_version()}")
    
    if not check_vred_environment():
        print("[VRED] ERROR: Cannot run outside VRED environment")
        return
    
    # Load the latest model first
    load_latest_model()
    
    # Start file watcher in background thread
    try:
        watcher_thread = threading.Thread(target=start_file_watcher, daemon=True)
        watcher_thread.start()
        
        print("[VRED] Auto-loader running. Export from Blender to see live updates!")
        print("[VRED] Press Ctrl+C in console to stop")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[VRED] Shutting down auto-loader...")
    except Exception as e:
        print(f"[VRED] Error in main loop: {e}")

# Run the script
if __name__ == "__main__":
    main()
else:
    # If running in VRED's Python environment, start automatically
    main()