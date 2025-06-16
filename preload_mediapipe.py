import os
import sys
import ctypes
import platform

def preload_mediapipe_dependencies():
    """Pre-load all necessary DLLs for MediaPipe to work properly on Windows"""
    if platform.system() != 'Windows':
        return
    
    print("Preloading MediaPipe dependencies...")
    
    # Add Python directory to PATH
    python_dir = os.path.dirname(sys.executable)
    if python_dir not in os.environ.get('PATH', ''):
        os.environ['PATH'] = python_dir + os.pathsep + os.environ.get('PATH', '')
    
    # Add Scripts directory to PATH
    scripts_dir = os.path.join(python_dir, 'Scripts')
    if os.path.exists(scripts_dir) and scripts_dir not in os.environ.get('PATH', ''):
        os.environ['PATH'] = scripts_dir + os.pathsep + os.environ.get('PATH', '')
    
    # Set DLL directory for the process (Windows 10 1709 and later)
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(python_dir)
            if os.path.exists(scripts_dir):
                os.add_dll_directory(scripts_dir)
        except Exception as e:
            print(f"Error adding DLL directories: {e}")
    
    # Reset DLL directory to include Windows system directories
    if hasattr(ctypes.windll.kernel32, 'SetDllDirectoryW'):
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    
    # Force load VCRuntime DLLs that MediaPipe depends on
    preload_dlls = [
        'vcruntime140.dll',
        'vcruntime140_1.dll',
        'msvcp140.dll',
        'concrt140.dll',
    ]
    
    for dll in preload_dlls:
        try:
            ctypes.CDLL(dll)
            print(f"Preloaded: {dll}")
        except Exception:
            print(f"Could not preload: {dll}")
    
    print("MediaPipe dependencies preloaded")

if __name__ == "__main__":
    preload_mediapipe_dependencies()
    
    # Import mediapipe after preloading
    try:
        import mediapipe as mp
        print("MediaPipe loaded successfully!")
        print(f"MediaPipe version: {mp.__version__}")
    except ImportError as e:
        print(f"Failed to import MediaPipe: {e}") 