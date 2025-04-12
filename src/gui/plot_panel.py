"""
Plot Panel for the Satellite Imagery Viewer
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import rasterio # For index export

# Import visualization functions (ensure they are updated)
from src.utils.visualization import (
    plot_single_band,
    plot_multiple_bands,
    create_rgb_composite,
    plot_spectral_index # Assuming this name based on previous context
)

class PlotPanel:
    """Plot panel for displaying satellite imagery"""

    def __init__(self, parent):
        """Initialize the plot panel"""
        self.parent = parent
        self.imagery_load_callback = None # Callback for app

        # Create panel frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Imagery data and plot state tracking
        self.imagery_data = None
        self.current_plot_options = {} # Store options used for the current plot
        self.current_index_array = None # Store calculated index data
        self.current_index_name = None # Store name of the current index

        # Configure matplotlib canvas and toolbar
        self.fig = Figure(figsize=(7, 6), dpi=100) # Adjust size as needed
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        # Matplotlib navigation toolbar
        self.toolbar_frame = ttk.Frame(self.frame)
        self.toolbar_frame.pack(fill=tk.X, side=tk.BOTTOM) # Place toolbar at bottom
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame)
        self.toolbar.update()

        # Show initial welcome message
        self._show_welcome()

    def set_imagery_load_callback(self, callback):
        """Sets the callback function (e.g., in app.py) to notify about data changes."""
        self.imagery_load_callback = callback

    def _show_welcome(self):
        """Display a welcome message on the canvas when no data is loaded."""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.text(0.5, 0.5, "Welcome!\nLoad Satellite Imagery using the 'File' menu\nor the 'Load Imagery' button.",
                ha='center', va='center', fontsize=12, linespacing=1.5)
        ax.set_axis_off()
        self.fig.tight_layout()
        self.canvas.draw()
        self.current_plot_options = {} # Reset plot state
        self.current_index_array = None
        self.current_index_name = None


    def set_imagery_data(self, imagery_data):
        """
        Receive new imagery data, store it, trigger an initial plot,
        and notify the main application via callback.
        """
        self.imagery_data = imagery_data
        self.current_index_array = None # Clear any previous index result
        self.current_index_name = None

        if self.imagery_data and len(self.imagery_data.get('bands', [])) > 0:
            # Define default options for the initial plot (e.g., first band)
            initial_options = {
                'scale': True, 'colorbar': True, 'equalize': False,
                'colormap': 'gray', 'alpha': 1.0,
                'plot_type': 'bands', 'band_indices': [0] # Plot first band (index 0)
            }
            # Update the plot immediately with default view
            self.update_plot(self.imagery_data, initial_options)
        else:
            # If data is invalid or None, show welcome screen
            self._show_welcome()

        # Notify the main application about the imagery load status
        if self.imagery_load_callback:
            self.imagery_load_callback(self.imagery_data)


    def update_plot(self, imagery_data, options):
        """
        Core function to update the plot based on imagery data and visualization options.
        This function is called by ControlPanel and IndicesPanel.
        """
        if not imagery_data or not imagery_data.get('bands'):
            self._show_welcome() # Show welcome if no valid data
            return

        # Update internal data reference and store current options
        self.imagery_data = imagery_data
        self.current_plot_options = options.copy()
        plot_type = options.get('plot_type', 'bands') # Determine what to plot

        # Reset index data if not plotting an index
        if plot_type != 'index':
            self.current_index_array = None
            self.current_index_name = None

        try:
            self.fig.clear() # Clear previous figure content

            # --- Plotting logic based on plot_type ---
            if plot_type == 'bands':
                indices = options.get('band_indices', [])
                if not indices:
                     # Display message if no bands are selected
                     self._show_message("Select band(s) from the 'Bands & View' tab to plot.")
                else:
                    # Prepare data for plotting functions
                    selected_bands = [self.imagery_data['bands'][i] for i in indices]
                    # Create descriptive names for titles
                    selected_names = [f"Band {i+1}: {self.imagery_data['band_names'][i]}" for i in indices]

                    # Call appropriate plotting function based on number of bands
                    if len(selected_bands) == 1:
                        plot_single_band(self.fig, selected_bands[0], selected_names[0], options)
                    else:
                        plot_multiple_bands(self.fig, selected_bands, selected_names, options)

            elif plot_type == 'rgb':
                # Get original band names for the title
                r_name = self.imagery_data['band_names'][options['r_idx']]
                g_name = self.imagery_data['band_names'][options['g_idx']]
                b_name = self.imagery_data['band_names'][options['b_idx']]
                # Pass all bands, selected names, and options to the function
                create_rgb_composite(self.fig, self.imagery_data['bands'], [r_name, g_name, b_name], options)

            elif plot_type == 'index':
                 # Extract index-specific data from options
                 index_array = options.get('index_array')
                 index_name = options.get('index_name', 'Unknown Index')
                 description = options.get('index_description', '')
                 colormap = options.get('index_colormap', 'viridis')
                 value_range = options.get('index_range', None) # Let matplotlib decide if None

                 # Store index data for potential export
                 self.current_index_array = index_array
                 self.current_index_name = index_name

                 # Call the index plotting function
                 plot_spectral_index(self.fig, index_array, index_name, description, colormap, value_range, options)

            else:
                # Handle unknown plot type
                 self._show_error_message(f"Unknown plot type specified: {plot_type}")

            # Final adjustments and drawing
            self.fig.tight_layout() # Adjust layout to prevent overlap
            self.canvas.draw() # Redraw the canvas

        except IndexError:
             # Specific error for bad band indices
             messagebox.showerror("Plot Error", "Selected band index is out of range for the loaded image.")
             self._show_error_message("Invalid band index selected.")
        except ValueError as ve:
            # Catch ValueErrors often related to data shapes or invalid options
             messagebox.showerror("Plot Error", f"Could not plot data:\n{str(ve)}")
             self._show_error_message(f"Plotting Error: {ve}")
        except Exception as e:
             # Catch any other unexpected errors during plotting
             messagebox.showerror("Plot Error", f"An unexpected error occurred during plotting:\n{str(e)}")
             self._show_error_message(f"Unexpected Plotting Error")
             import traceback
             traceback.print_exc() # Print full traceback to console


    def _show_message(self, message, is_error=False):
        """Helper to display a text message on the canvas."""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        props = {'ha': 'center', 'va': 'center', 'wrap': True}
        if is_error:
             props['color'] = 'red'
             props['fontsize'] = 10
        else:
             props['fontsize'] = 12
        ax.text(0.5, 0.5, message, **props)
        ax.set_axis_off()
        self.fig.tight_layout()
        self.canvas.draw()

    def _show_error_message(self, message):
        """Convenience function to show an error message."""
        self._show_message(message, is_error=True)

    def reset_view(self):
        """Reset the plot to the default initial view (usually first band)."""
        # Reuse the logic from set_imagery_data for the initial plot
        self.set_imagery_data(self.imagery_data)

    def save_plot(self):
        """Save the current view in the plot panel to an image file."""
        # Check if there's actually something plotted
        if not self.fig.get_axes() or not any(ax.has_data() for ax in self.fig.get_axes()):
             messagebox.showwarning("Save Plot", "Nothing to save. Please load and plot imagery first.")
             return

        # Ask user for file path and format
        file_path = filedialog.asksaveasfilename(
            title="Save Plot As",
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"),
                       ("JPEG files", "*.jpg;*.jpeg"),
                       ("TIFF files", "*.tif;*.tiff"),
                       ("PDF files", "*.pdf"),
                       ("SVG files", "*.svg"),
                       ("All files", "*.*")]
        )
        if not file_path:
            return # User cancelled

        try:
            # Save the figure using matplotlib's savefig
            self.fig.savefig(file_path, dpi=300, bbox_inches='tight') # Use higher DPI and tight bounding box
            messagebox.showinfo("Save Plot", f"Plot saved successfully to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save plot:\n{str(e)}")


    def export_index_raster(self):
        """Export the currently displayed spectral index as a GeoTIFF file."""
        # --- Input Validation ---
        if self.current_index_array is None or self.current_index_name is None:
            messagebox.showwarning("Export Error", "No spectral index is currently displayed or calculated.")
            return
        if not self.imagery_data or 'metadata' not in self.imagery_data:
             messagebox.showerror("Export Error", "Cannot export index: Original imagery metadata is missing.")
             return
        if self.current_index_array.shape != (self.imagery_data['metadata']['height'], self.imagery_data['metadata']['width']):
             messagebox.showerror("Export Error", "Index dimensions do not match original image metadata.")
             return


        # --- Get Filename ---
        # Suggest a filename based on original image and index name
        original_basename = os.path.splitext(os.path.basename(self.imagery_data['file_path']))[0]
        default_filename = f"{original_basename}_{self.current_index_name}.tif"

        file_path = filedialog.asksaveasfilename(
            title="Export Index Raster As",
            initialfile=default_filename,
            defaultextension=".tif",
            filetypes=[("GeoTIFF files", "*.tif *.tiff"), ("All files", "*.*")]
        )
        if not file_path:
            return # User cancelled

        # --- Prepare Metadata ---
        try:
            # Start with metadata from the original image
            metadata = self.imagery_data['metadata'].copy()

            # Update metadata for the single-band index raster
            metadata.update({
                'dtype': self.current_index_array.dtype, # Use the dtype of the calculated index
                'count': 1,         # Index is a single band
                'nodata': np.nan if np.issubdtype(self.current_index_array.dtype, np.floating) else None, # Use NaN for float, None otherwise (or choose specific int nodata)
                'driver': 'GTiff'   # Ensure GeoTIFF driver
            })
            # Remove potentially incompatible metadata keys
            metadata.pop('compress', None) # Compression might cause issues with dtype/nodata changes
            metadata.pop('blockxsize', None)
            metadata.pop('blockysize', None)
            metadata.pop('tiled', None)

            # --- Write Raster ---
            with rasterio.open(file_path, 'w', **metadata) as dst:
                dst.write(self.current_index_array, 1) # Write the index array to the first band

            messagebox.showinfo("Export Successful", f"Index raster '{self.current_index_name}' exported successfully to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export index raster:\n{str(e)}")
            import traceback
            traceback.print_exc() # Log full error to console