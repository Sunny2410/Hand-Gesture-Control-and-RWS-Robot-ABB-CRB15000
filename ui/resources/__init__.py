"""
Resources module for the ABB Robot Control UI.
This module contains resources like stylesheets, icons and other static assets.
"""

import os

# Get the path to the resources directory
RESOURCES_DIR = os.path.dirname(os.path.abspath(__file__))

def get_resource_path(filename):
    """
    Returns the absolute path to a resource file.
    
    Args:
        filename (str): Name of the resource file
        
    Returns:
        str: Absolute path to the resource file
    """
    return os.path.join(RESOURCES_DIR, filename)

def get_stylesheet():
    """
    Returns the application stylesheet as a string.
    
    Returns:
        str: Application stylesheet
    """
    stylesheet_path = get_resource_path('style.qss')
    if os.path.exists(stylesheet_path):
        with open(stylesheet_path, 'r') as f:
            return f.read()
    return "" 