import os
import sys
import platform
import ctypes

# FIX FOR MEDIAPIPE DLL LOADING ISSUES
# This needs to run before importing any other modules
def fix_mediapipe_dll_loading():
    if platform.system() == 'Windows':
        # Add Python directory to PATH
        python_dir = os.path.dirname(sys.executable)
        os.environ['PATH'] = python_dir + os.pathsep + os.environ.get('PATH', '')
        
        # Add Scripts directory to PATH
        scripts_dir = os.path.join(python_dir, 'Scripts')
        if os.path.exists(scripts_dir):
            os.environ['PATH'] = scripts_dir + os.pathsep + os.environ.get('PATH', '')
        
        # Add current directory to PATH
        current_dir = os.path.dirname(os.path.abspath(__file__))
        os.environ['PATH'] = current_dir + os.pathsep + os.environ.get('PATH', '')
        
        # Add DLL directories (Windows 10 1709 and later)
        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(python_dir)
            if os.path.exists(scripts_dir):
                os.add_dll_directory(scripts_dir)
            os.add_dll_directory(current_dir)
        
        # Reset DLL directory to include Windows system directories
        if hasattr(ctypes.windll.kernel32, 'SetDllDirectoryW'):
            ctypes.windll.kernel32.SetDllDirectoryW(None)
        
        # Preload required DLLs
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
            except Exception as e:
                print(f"Could not preload: {dll} ({str(e)})")

# Apply the fix before importing any other modules
fix_mediapipe_dll_loading()

# Now import the rest of the modules
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QSplashScreen
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QPixmap, QIcon, QFont

# Import custom UI components
from ui.main_window import ABBRobotControlUI
from ui.splash_screen import SplashScreen

# Import robot API
from API.abb_robot import ABBRobot


def setup_logging():
    """Configure application logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler("abb_robot_ui.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('ABBRobotUI')


def main():
    """Main entry point for the application"""
    # Setup logging
    logger = setup_logging()
    logger.info("Starting ABB Robot UI Application")
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("ABB Robot Control ")
    app.setOrganizationName("SANGNHATHIEU")
    
    try:
        # Load application style
        with open("ui/resources/style.qss", "r") as style_file:
            app.setStyleSheet(style_file.read())
        
        # Create and show splash screen
        splash = SplashScreen()
        splash.show()
        
        # Force processing events to ensure splash is displayed
        app.processEvents()
        
        # Create main window after short delay
        QTimer.singleShot(2000, lambda: load_main_window(app, splash, logger))
        
        # Start application main loop
        return app.exec_()
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        QMessageBox.critical(None, "Error", f"Failed to start application: {str(e)}")
        return 1


def load_main_window(app, splash, logger):
    """Load the main application window"""
    try:
        # Create main window
        main_window = ABBRobotControlUI(logger)
        
        # Show main window
        main_window.show()
        
        # Process events to make sure main window is displayed
        app.processEvents()
        
        # Close splash screen with a delay to ensure no race conditions
        QTimer.singleShot(100, lambda: finish_splash(splash, main_window))
        
        logger.info("Application main window loaded successfully")
        
    except Exception as e:
        logger.error(f"Error loading main window: {str(e)}")
        QMessageBox.critical(None, "Error", 
                           f"Failed to start application: {str(e)}")
        app.quit()


def finish_splash(splash, main_window):
    """Safely finish the splash screen"""
    try:
        # Finish the splash screen
        splash.finish(main_window)
    except Exception as e:
        # If any error occurs, make sure splash is hidden
        splash.hide()


if __name__ == "__main__":
    sys.exit(main()) 