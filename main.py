#!/usr/bin/env python3
"""
Satellite Imagery Viewer - Main Entry Point

This script launches the Satellite Imagery Viewer application.
It ensures the 'src' directory is correctly added to the Python path.
"""

import os
import sys
import platform

# --- Path Setup ---
# Determine the absolute path to the directory containing this script (main.py)
# This assumes main.py is directly inside the 'src' folder.
script_dir = os.path.dirname(os.path.abspath(__file__))
# Determine the project root directory (one level up from 'src')
project_root = os.path.dirname(script_dir)

# Insert the project root directory into sys.path
# This allows imports like 'from src.gui.app import ...' to work correctly
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Imports after path setup ---
try:
    from src.gui.app import SatelliteImageryApp
except ImportError as e:
    print("Error: Could not import application components.")
    print("Ensure the script is run from the correct directory or that the 'src' folder exists.")
    print(f"Project Root added to path: {project_root}")
    print(f"Current sys.path: {sys.path}")
    print(f"Import Error: {e}")
    sys.exit(1) # Exit if imports fail

# --- Platform-specific adjustments (Optional) ---
# Example: Set environment variable for High DPI scaling on Windows if needed
# if platform.system() == "Windows":
#     try:
#         from ctypes import windll
#         windll.shcore.SetProcessDpiAwareness(1) # Adjust DPI awareness
#     except Exception as dpi_error:
#         print(f"Could not set DPI awareness: {dpi_error}")

def main():
    """Main entry point for the application"""
    try:
        app = SatelliteImageryApp()
        app.run()
    except Exception as app_error:
        print("An unexpected error occurred running the application:")
        # Consider showing a simple Tkinter error message as well
        import traceback
        traceback.print_exc()
        # You could add a tk messagebox here for the user
        # tk.messagebox.showerror("Fatal Error", f"Application encountered an error:\n{app_error}")


if __name__ == "__main__":
    # Ensure the script runs only when executed directly
    main()