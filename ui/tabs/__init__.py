"""
Tabs module for the ABB Robot Control UI.
This module contains all tab components used in the main window.
"""

from ui.tabs.connection_tab import ConnectionTab
from ui.tabs.panel_tab import PanelTab
from ui.tabs.io_tab import IOTab
from ui.tabs.rapid_tab import RAPIDTab
from ui.tabs.motion_tab import MotionTab
from ui.tabs.vision_tab import VisionTab
from ui.tabs.system_tab import SystemTab

__all__ = [
    'ConnectionTab',
    'PanelTab',
    'IOTab',
    'RAPIDTab',
    'MotionTab',
    'VisionTab',
    'SystemTab'
] 