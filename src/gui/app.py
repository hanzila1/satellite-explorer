"""
Main application class for the Satellite Imagery Viewer
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os # Needed for basename in on_imagery_loaded status

from src.gui.control_panel import ControlPanel
from src.gui.plot_panel import PlotPanel
from src.gui.indices_panel import IndicesPanel


class SatelliteImageryApp:
    """Main application class for the Satellite Imagery Viewer"""

    def __init__(self):
        """Initialize the application"""
        self.root = tk.Tk()
        self.root.title("Satellite Imagery Viewer")
        self.root.geometry("1300x850") # Increased size slightly
        self.root.minsize(900, 650)

        # Set up the main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Configure application style
        self._configure_style()

        # --- Left Panel ---
        self.left_frame = ttk.Frame(self.main_frame, width=400) # Increased width
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.left_frame.pack_propagate(False)  # Keep the width

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.left_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create frames for each tab
        self.control_tab = ttk.Frame(self.notebook)
        self.indices_tab = ttk.Frame(self.notebook)

        # Add tabs to notebook
        self.notebook.add(self.control_tab, text="Bands & View")
        self.notebook.add(self.indices_tab, text="Indices")

        # --- Right Panel (Plot) ---
        self.plot_panel = PlotPanel(self.main_frame)

        # --- Create Panels within Tabs ---
        # Pass plot_panel directly to allow panels to interact with it
        self.control_panel = ControlPanel(self.control_tab, self.plot_panel)
        self.indices_panel = IndicesPanel(self.indices_tab, self.plot_panel)

        # Link control panel controls to plot panel actions
        self.control_panel.set_plot_update_callback(self.plot_panel.update_plot)

        # Configure main menu
        self._create_menu()

        # Connect panels for data sharing (using callbacks)
        # When imagery is set/loaded in plot_panel, it calls on_imagery_loaded
        self.plot_panel.set_imagery_load_callback(self.on_imagery_loaded)

    def on_imagery_loaded(self, imagery_data):
        """Callback function when imagery is loaded/cleared in plot_panel."""
        if imagery_data:
            # Update other panels with the new data
            self.control_panel.update_bands(imagery_data)
            self.indices_panel.update_with_imagery(imagery_data)
            # Enable relevant menu items
            self.file_menu.entryconfig("Save Plot As...", state=tk.NORMAL)
            # Export Index Raster starts disabled, enabled by indices_panel
            self.file_menu.entryconfig("Export Index Raster...", state=tk.DISABLED)
            # Update window title or status bar if desired
            self.root.title(f"Satellite Imagery Viewer - {os.path.basename(imagery_data['file_path'])}")
        else:
             # Disable relevant menu items if no data loaded or load failed
            self.file_menu.entryconfig("Save Plot As...", state=tk.DISABLED)
            self.file_menu.entryconfig("Export Index Raster...", state=tk.DISABLED)
            self.root.title("Satellite Imagery Viewer") # Reset title

    def _configure_style(self):
        """Configure the application style"""
        style = ttk.Style()
        # Try different themes, 'clam', 'alt', 'default', 'classic'
        try:
            # 'clam' or 'alt' often look good on Win/Linux, 'aqua' on macOS (Tk default)
            if os.name == 'nt': # Windows
                style.theme_use('vista') # or 'xpnative'
            elif sys.platform == 'darwin': # macOS
                 style.theme_use('aqua') # Default macOS theme
            else: # Linux/other
                style.theme_use('clam')
        except tk.TclError:
            print("Preferred theme not available, using default.")
            style.theme_use('default')

        # Configure specific widget styles
        style.configure('TButton', font=('Arial', 10), padding=5)
        style.configure('TLabel', font=('Arial', 10))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('TCheckbutton', font=('Arial', 10))
        style.configure('TCombobox', font=('Arial', 10))
        # Style the Scale widget (slider) for better visibility
        style.configure('Horizontal.TScale', troughcolor='#e0e0e0', background='#cccccc', sliderlength=20)
        # Style the Notebook tabs
        style.configure('TNotebook.Tab', font=('Arial', 10, 'bold'), padding=[10, 5])


    def _create_menu(self):
        """Create the application menu"""
        menu_bar = tk.Menu(self.root)

        # File menu
        # Store as instance variable to enable/disable items later
        self.file_menu = tk.Menu(menu_bar, tearoff=0)
        self.file_menu.add_command(label="Load Imagery",
                               command=self.control_panel.load_imagery)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save Plot As...",
                               command=self.plot_panel.save_plot, state=tk.DISABLED) # Initially disabled
        self.file_menu.add_command(label="Export Index Raster...",
                               # Link to indices_panel which calls plot_panel export
                               command=self.indices_panel.trigger_export_index, state=tk.DISABLED)
        # Placeholder for ROI export - needs more work
        # self.file_menu.add_command(label="Export ROI Data...", command=self.export_roi_data, state=tk.DISABLED)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit)
        menu_bar.add_cascade(label="File", menu=self.file_menu)

        # View menu
        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="Reset View",
                               command=self.plot_panel.reset_view)
        menu_bar.add_cascade(label="View", menu=view_menu)

        # Band Mapping Menu (actions handled by IndicesPanel)
        mapping_menu = tk.Menu(menu_bar, tearoff=0)
        mapping_menu.add_command(label="Save Band Mapping...", command=self.indices_panel.save_band_mapping)
        mapping_menu.add_command(label="Load Band Mapping...", command=self.indices_panel.load_band_mapping)
        menu_bar.add_cascade(label="Mapping", menu=mapping_menu)


        # Help menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menu_bar)

    # Placeholder function for future ROI export feature
    # def export_roi_data(self):
    #    messagebox.showinfo("Not Implemented", "ROI selection and data export is not yet implemented.")


    def _show_about(self):
        """Show about dialog"""
        about_window = tk.Toplevel(self.root)
        about_window.title("About Satellite Imagery Viewer")
        about_window.geometry("400x300")
        about_window.resizable(False, False)
        about_window.transient(self.root) # Keep it on top of the main window
        about_window.grab_set() # Make it modal (block interaction with main window)

        # Content
        ttk.Label(about_window, text="Satellite Imagery Viewer", font=("Arial", 16, "bold")).pack(pady=(20, 10))
        ttk.Label(about_window, text="A tool for visualizing satellite imagery bands and calculating spectral indices.", wraplength=350, justify=tk.CENTER).pack()
        ttk.Label(about_window, text="Version 1.2 (Enhanced)", font=("Arial", 10, "italic")).pack(pady=(10, 20))
        ttk.Button(about_window, text="Close", command=about_window.destroy).pack(pady=(10, 20))

        # Center the 'About' window relative to the main application window
        self.root.update_idletasks() # Ensure main window geometry is up-to-date
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()

        # Use reqwidth/reqheight for the 'About' window before it's fully drawn
        win_width = about_window.winfo_reqwidth()
        win_height = about_window.winfo_reqheight()

        # Calculate position
        x = root_x + (root_width // 2) - (win_width // 2)
        y = root_y + (root_height // 2) - (win_height // 2)
        about_window.geometry(f"+{x}+{y}") # Set position

        self.root.wait_window(about_window) # Wait until the 'About' window is closed

    def run(self):
        """Run the application main loop"""
        self.root.mainloop()