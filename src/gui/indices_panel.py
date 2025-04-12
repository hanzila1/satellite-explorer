"""
Indices Panel for the Satellite Imagery Viewer
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json # For saving/loading mappings
import os

from src.utils.indices import (
    COMMON_INDICES,
    guess_band_types,
    calculate_index,
    get_available_indices
)

class IndicesPanel:
    """Panel for calculating and displaying spectral indices"""

    def __init__(self, parent, plot_panel):
        """Initialize the indices panel"""
        self.parent = parent
        self.plot_panel = plot_panel # Store plot_panel reference

        # Create panel frame
        self.frame = ttk.Frame(parent, padding="10")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Imagery data and state
        self.imagery_data = None
        self.band_mapping = {}
        self.available_indices = []
        self.band_vars = {} # Store tk.StringVar for band mapping Comboboxes
        self.band_name_labels = {} # Store labels showing band names

        # Create widgets
        self._create_widgets()

    def _create_widgets(self):
        """Create the panel widgets"""
        # --- Band Mapping Section ---
        self.bands_frame = ttk.LabelFrame(self.frame, text="Band Mapping")
        self.bands_frame.pack(fill=tk.X, pady=5, padx=5)
        self.bands_frame_content = ttk.Frame(self.bands_frame, padding=5) # Content frame
        self.bands_frame_content.pack(fill=tk.X)
        # Placeholder message
        self.no_imagery_label_map = ttk.Label(self.bands_frame_content, text="Load imagery to configure band mapping.", wraplength=350)
        self.no_imagery_label_map.pack(pady=10)

        # --- Available Indices Section ---
        self.indices_frame = ttk.LabelFrame(self.frame, text="Available Indices")
        self.indices_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)

        # Scrollable frame setup for indices
        self.indices_canvas = tk.Canvas(self.indices_frame, borderwidth=0, background="#ffffff")
        self.indices_scrollbar = ttk.Scrollbar(self.indices_frame, orient="vertical", command=self.indices_canvas.yview)
        self.indices_scrollable_frame = ttk.Frame(self.indices_canvas, padding=(5,0))

        self.indices_scrollable_frame.bind("<Configure>", self._on_scrollable_frame_configure)
        self.indices_canvas_window = self.indices_canvas.create_window((0, 0), window=self.indices_scrollable_frame, anchor="nw")

        self.indices_canvas.configure(yscrollcommand=self.indices_scrollbar.set)
        self.indices_canvas.pack(side="left", fill="both", expand=True)
        self.indices_scrollbar.pack(side="right", fill="y")

        # Mouse wheel scrolling (bind to canvas and frame inside)
        self.indices_canvas.bind_all("<MouseWheel>", self._on_mousewheel, add='+')
        self.indices_scrollable_frame.bind_all("<MouseWheel>", self._on_mousewheel, add='+')

        # Placeholder message
        self.no_imagery_label_indices = ttk.Label(self.indices_scrollable_frame, text="Indices will appear here after mapping bands.", wraplength=300)
        self.no_imagery_label_indices.pack(pady=10)

        # --- Export Button (initially hidden/disabled) ---
        self.export_button = ttk.Button(self.frame, text="Export Current Index...", command=self.trigger_export_index, state=tk.DISABLED)
        self.export_button.pack(pady=(5, 0), fill=tk.X, padx=5)


    def _on_scrollable_frame_configure(self, event):
        """Reset the scroll region to encompass the inner frame"""
        self.indices_canvas.configure(scrollregion=self.indices_canvas.bbox("all"))
        # Adjust window width to prevent horizontal scrollbar if possible
        width = self.indices_canvas.winfo_width()
        self.indices_canvas.itemconfig(self.indices_canvas_window, width=width)


    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling for the indices list."""
        # Determine scroll amount based on OS
        if event.num == 5 or event.delta < 0:
            delta = 1
        elif event.num == 4 or event.delta > 0:
            delta = -1
        else: # Should not happen
             delta = 0

        # Check if the mouse is over the relevant canvas
        widget_under_mouse = self.frame.winfo_containing(event.x_root, event.y_root)
        is_over_canvas = widget_under_mouse == self.indices_canvas or \
                         str(widget_under_mouse).startswith(str(self.indices_scrollable_frame))

        if is_over_canvas:
            self.indices_canvas.yview_scroll(delta, "units")

    def update_with_imagery(self, imagery_data):
        """Update the panel with new imagery data."""
        self.imagery_data = imagery_data
        self.export_button.config(state=tk.DISABLED) # Disable export on new load

        # Clear previous dynamic widgets first
        for widget in self.bands_frame_content.winfo_children():
            widget.destroy()
        for widget in self.indices_scrollable_frame.winfo_children():
            widget.destroy()

        if not imagery_data or not imagery_data.get('bands'):
            # Show placeholder messages if no imagery
            self.no_imagery_label_map = ttk.Label(self.bands_frame_content, text="Load imagery to configure band mapping.", wraplength=350)
            self.no_imagery_label_map.pack(pady=10)
            self.no_imagery_label_indices = ttk.Label(self.indices_scrollable_frame, text="Indices will appear here after mapping bands.", wraplength=300)
            self.no_imagery_label_indices.pack(pady=10)
            self.band_mapping = {}
            self.available_indices = []
            self.band_vars = {}
            self.band_name_labels = {}
            return

        # --- Populate Band Mapping Section ---
        ttk.Label(self.bands_frame_content, text="Assign band types (required for indices):").pack(anchor=tk.W, pady=(0, 5))
        mapping_grid = ttk.Frame(self.bands_frame_content)
        mapping_grid.pack(fill=tk.X)

        # Header row
        ttk.Label(mapping_grid, text="Type", width=8).grid(row=0, column=0, padx=5, sticky=tk.W)
        ttk.Label(mapping_grid, text="Band Sel.", width=15).grid(row=0, column=1, padx=5, sticky=tk.W)
        ttk.Label(mapping_grid, text="Band Name", width=20).grid(row=0, column=2, padx=5, sticky=tk.W)

        standard_bands = ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"] # Common order
        self.band_vars = {}
        self.band_name_labels = {}
        band_names = self.imagery_data.get('band_names', [])
        combo_values = [""] + [f"{i+1}: {name}" for i, name in enumerate(band_names)] # Add empty option + format

        # Try to guess initial mapping
        guessed_mapping = guess_band_types(band_names)

        for i, band_type in enumerate(standard_bands):
            row_num = i + 1
            ttk.Label(mapping_grid, text=band_type).grid(row=row_num, column=0, padx=5, pady=1, sticky=tk.W)

            var = tk.StringVar()
            self.band_vars[band_type] = var

            # Set initial value from guessed mapping
            initial_value = ""
            if band_type in guessed_mapping:
                idx = guessed_mapping[band_type]
                if 0 <= idx < len(band_names):
                     initial_value = f"{idx+1}: {band_names[idx]}"
            var.set(initial_value)

            combo = ttk.Combobox(
                mapping_grid, textvariable=var, width=18, # Adjusted width
                values=combo_values, state='readonly'
            )
            combo.grid(row=row_num, column=1, padx=5, pady=1, sticky=tk.W)
            combo.bind("<<ComboboxSelected>>", lambda e, bt=band_type: self._update_single_band_mapping(bt))

            name_label_var = tk.StringVar() # Separate var for the display label
            name_label = ttk.Label(mapping_grid, textvariable=name_label_var, wraplength=150, foreground="grey")
            name_label.grid(row=row_num, column=2, padx=5, pady=1, sticky=tk.W)
            self.band_name_labels[band_type] = name_label_var # Store the label variable

        ttk.Button(self.bands_frame_content, text="Update Available Indices", command=self._update_indices_list).pack(pady=5, fill=tk.X)

        # Initial update
        self._update_all_band_mappings() # Populate band_mapping dict
        self._update_all_name_labels() # Update name labels
        self._update_indices_list()   # Update available indices


    def _update_single_band_mapping(self, band_type):
        """Update mapping for a single band type when its Combobox changes."""
        var = self.band_vars.get(band_type)
        if not var: return
        selected_value = var.get()

        if selected_value and ":" in selected_value:
            try:
                band_index_str = selected_value.split(":")[0]
                band_index = int(band_index_str) - 1 # Convert to 0-based index
                if 0 <= band_index < len(self.imagery_data['bands']):
                    self.band_mapping[band_type] = band_index
                    self.band_name_labels[band_type].set(self.imagery_data['band_names'][band_index])
                else:
                     # Should not happen with readonly combobox, but good practice
                     if band_type in self.band_mapping: del self.band_mapping[band_type]
                     self.band_name_labels[band_type].set("")
            except (ValueError, IndexError):
                if band_type in self.band_mapping: del self.band_mapping[band_type]
                self.band_name_labels[band_type].set("")
        else:
            # Empty selection
            if band_type in self.band_mapping: del self.band_mapping[band_type]
            self.band_name_labels[band_type].set("")

        # Note: We don't automatically update indices list here, user clicks button

    def _update_all_band_mappings(self):
        """Update the internal band_mapping dictionary from all comboboxes."""
        if not self.imagery_data: return
        self.band_mapping = {}
        num_bands = len(self.imagery_data['bands'])
        for band_type, var in self.band_vars.items():
            selected_value = var.get()
            if selected_value and ":" in selected_value:
                try:
                    band_index_str = selected_value.split(":")[0]
                    band_index = int(band_index_str) - 1 # 0-based index
                    if 0 <= band_index < num_bands:
                        self.band_mapping[band_type] = band_index
                except ValueError:
                    pass # Ignore invalid selections

    def _update_all_name_labels(self):
         """Update all band name display labels based on current mapping."""
         if not self.imagery_data: return
         band_names = self.imagery_data.get('band_names', [])
         for band_type, label_var in self.band_name_labels.items():
              if band_type in self.band_mapping:
                   idx = self.band_mapping[band_type]
                   if 0 <= idx < len(band_names):
                        label_var.set(band_names[idx])
                   else: label_var.set("") # Should not happen
              else:
                   label_var.set("")


    def _update_indices_list(self):
        """Update the list of available indices based on current mapping."""
        self._update_all_band_mappings() # Ensure mapping is current
        self.available_indices = get_available_indices(self.band_mapping)

        # Clear previous widgets
        for widget in self.indices_scrollable_frame.winfo_children():
            widget.destroy()

        if not self.available_indices:
            ttk.Label(self.indices_scrollable_frame, text="No indices available with current band mapping.\nAssign required band types (e.g., Red, NIR).", wraplength=300, justify=tk.CENTER).pack(pady=10)
        else:
            ttk.Label(self.indices_scrollable_frame, text="Click an index to calculate and visualize:", wraplength=300).pack(anchor=tk.W, pady=(0, 5))
            for index_name in sorted(self.available_indices): # Sort alphabetically
                index_info = COMMON_INDICES[index_name]
                idx_frame = ttk.Frame(self.indices_scrollable_frame)
                idx_frame.pack(fill=tk.X, pady=2)

                btn = ttk.Button(idx_frame, text=index_name, width=8,
                                 command=lambda idx=index_name: self._calculate_index(idx))
                btn.pack(side=tk.LEFT, padx=(0, 10))
                ttk.Label(idx_frame, text=f"{index_info['name']} ({', '.join(index_info['bands'])})", wraplength=250).pack(side=tk.LEFT, fill=tk.X, expand=True, anchor=tk.W)

        self.indices_scrollable_frame.update_idletasks() # Needed before bbox
        self._on_scrollable_frame_configure(None) # Update scroll region


    def _calculate_index(self, index_name):
        """Calculate and display the selected index."""
        if not self.imagery_data or not self.plot_panel:
            messagebox.showwarning("Warning", "Load imagery and ensure mapping is correct.")
            return
        if not self.plot_panel.update_plot: # Check if update_plot method exists
             messagebox.showerror("Error", "Plot panel is not configured correctly.")
             return

        self.export_button.config(state=tk.DISABLED) # Disable export until calculation succeeds

        try:
            # Ensure mapping is current before calculation
            self._update_all_band_mappings()

            index_array, description, colormap, value_range = calculate_index(
                self.imagery_data['bands'],
                self.band_mapping,
                index_name
            )

            # Prepare options for plot panel
            options = {
                'plot_type': 'index',
                'index_array': index_array,
                'index_name': index_name,
                'index_description': description,
                'index_colormap': colormap,
                'index_range': value_range,
                # Include general visualization options
                'alpha': 1.0 # Index plots usually opaque
                 # 'scale', 'colorbar', 'equalize' might not be relevant here,
                 # but pass them if plot_spectral_index uses them
            }

            # Update plot panel
            self.plot_panel.update_plot(self.imagery_data, options)

            # Enable export button after successful calculation
            self.export_button.config(state=tk.NORMAL)
            # Make sure the main app menu item is also enabled (handled via callback potentially)
            if hasattr(self.parent.master.master, 'file_menu'): # Access app's file_menu
                self.parent.master.master.file_menu.entryconfig("Export Index Raster...", state=tk.NORMAL)


        except ValueError as e:
             # Specific errors for missing bands are caught here
             messagebox.showerror("Calculation Error", f"Failed to calculate {index_name}:\n{str(e)}\n\nPlease check band mapping.")
        except Exception as e:
             messagebox.showerror("Calculation Error", f"An unexpected error occurred calculating {index_name}:\n{str(e)}")


    def trigger_export_index(self):
        """Calls the export method on the plot panel."""
        if self.plot_panel:
            self.plot_panel.export_index_raster()


    def save_band_mapping(self):
        """Save the current band mapping to a JSON file."""
        if not self.band_mapping:
             messagebox.showwarning("Save Mapping", "No band mapping defined to save.")
             return

        file_path = filedialog.asksaveasfilename(
            title="Save Band Mapping As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            # Ensure mapping is current before saving
            self._update_all_band_mappings()
            with open(file_path, 'w') as f:
                json.dump(self.band_mapping, f, indent=4) # Use indent for readability
            messagebox.showinfo("Save Mapping", f"Band mapping saved successfully to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save band mapping: {str(e)}")


    def load_band_mapping(self):
        """Load band mapping from a JSON file."""
        if not self.imagery_data:
             messagebox.showwarning("Load Mapping", "Load imagery before loading a band mapping.")
             return

        file_path = filedialog.askopenfilename(
            title="Load Band Mapping",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r') as f:
                loaded_mapping = json.load(f)

            # Validate the loaded mapping (basic check)
            if not isinstance(loaded_mapping, dict):
                 raise TypeError("Invalid mapping file format.")

            # Update the UI based on the loaded mapping
            self.band_mapping = {} # Clear current internal mapping
            band_names = self.imagery_data.get('band_names', [])
            num_bands = len(band_names)

            for band_type, var in self.band_vars.items():
                 if band_type in loaded_mapping:
                      idx = loaded_mapping[band_type]
                      # Check if the loaded index is valid for the current image
                      if isinstance(idx, int) and 0 <= idx < num_bands:
                           value_str = f"{idx+1}: {band_names[idx]}"
                           var.set(value_str)
                           self.band_mapping[band_type] = idx # Update internal mapping
                      else:
                           print(f"Warning: Loaded index {idx} for {band_type} is invalid for current image. Ignoring.")
                           var.set("") # Clear invalid entry
                 else:
                      var.set("") # Clear if type not in loaded file

            # Refresh UI elements
            self._update_all_name_labels()
            self._update_indices_list()
            messagebox.showinfo("Load Mapping", f"Band mapping loaded successfully from:\n{file_path}")

        except FileNotFoundError:
             messagebox.showerror("Load Error", f"File not found:\n{file_path}")
        except json.JSONDecodeError:
             messagebox.showerror("Load Error", "Failed to decode JSON. The file might be corrupted or not a valid mapping file.")
        except TypeError as e:
             messagebox.showerror("Load Error", f"Invalid mapping file content: {e}")
        except Exception as e:
             messagebox.showerror("Load Error", f"Failed to load band mapping: {str(e)}")