"""
Vision package for ABB Robot Control.
Contains modules for camera control and hand gesture recognition.
"""

import os
import sys
import platform
import ctypes

# First fix DLL loading for MediaPipe
def fix_mediapipe_dll_loading():
    if platform.system() == 'Windows':
        # Add Python directory to PATH
        python_dir = os.path.dirname(sys.executable)
        if python_dir not in os.environ.get('PATH', ''):
            os.environ['PATH'] = python_dir + os.pathsep + os.environ.get('PATH', '')
        
        # Add Scripts directory to PATH
        scripts_dir = os.path.join(python_dir, 'Scripts')
        if os.path.exists(scripts_dir) and scripts_dir not in os.environ.get('PATH', ''):
            os.environ['PATH'] = scripts_dir + os.pathsep + os.environ.get('PATH', '')
        
        # For Python 3.8+ on Windows, use add_dll_directory
        if hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(python_dir)
                if os.path.exists(scripts_dir):
                    os.add_dll_directory(scripts_dir)
            except Exception:
                pass
                
        # Set DLL directory to include Windows system directories
        if hasattr(ctypes.windll.kernel32, 'SetDllDirectoryW'):
            ctypes.windll.kernel32.SetDllDirectoryW(None)
        
        # Force load Visual C++ Runtime DLLs
        try:
            for dll_name in ['vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll']:
                try:
                    ctypes.CDLL(dll_name)
                except Exception:
                    pass
        except Exception:
            pass

# Run the fix
fix_mediapipe_dll_loading()

# Then import the rest
from .hand_detector import HandDetector

__all__ = ["HandDetector"]
