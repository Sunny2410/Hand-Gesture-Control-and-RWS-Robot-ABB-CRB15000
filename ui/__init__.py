"""
UI Package for the ABB Robot Control System.

This package contains the PyQt5-based user interface components:
- main_window: Main application window with tab interface
- splash_screen: Application splash screen
- tabs: Tab components for different robot control functions
- widgets: Reusable UI components 
- resources: Static resources like stylesheets and icons

Author: Sunny24
Date: May 2025
"""

from ui.main_window import ABBRobotControlUI
from ui.splash_screen import SplashScreen

# Import tab components
from ui.tabs.connection_tab import ConnectionTab
from ui.tabs.panel_tab import PanelTab
from ui.tabs.io_tab import IOTab
from ui.tabs.rapid_tab import RAPIDTab
from ui.tabs.motion_tab import MotionTab
from ui.tabs.vision_tab import VisionTab
from ui.tabs.system_tab import SystemTab

# Import widget components
from ui.widgets.log_widget import LogWidget
from ui.widgets.status_widget import StatusWidget

__all__ = [
    'ABBRobotControlUI',
    'SplashScreen',
    'ConnectionTab',
    'PanelTab',
    'IOTab',
    'RAPIDTab',
    'MotionTab',
    'VisionTab',
    'SystemTab',
    'LogWidget',
    'StatusWidget'
]
