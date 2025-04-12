"""
Control Panel for the Satellite Imagery Viewer
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import matplotlib.pyplot as plt # For colormaps

# Import utility function AFTER ensuring the correct code is in imagery.py
from src.utils.imagery import load_satellite_imagery


class ControlPanel:
    """Control panel for the Satellite Imagery Viewer application"""

    def __init__(self, parent, plot_panel):
        """Initialize the control panel"""
        self.parent = parent
        self.plot_panel = plot_panel # Store plot_panel reference
        self.plot_update_callback = None # Callback to update plot

        # Create panel frame
        self.frame = ttk.Frame(parent, padding="10")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # --- Variables ---
        self.image_path = None
        self.imagery_data = None # Store loaded data locally
        self.status_var = tk.StringVar(value="Ready")

        # Plotting Options
        self.scale_var = tk.BooleanVar(value=True)
        self.colorbar_var = tk.BooleanVar(value=True)
        self.equalize_hist_var = tk.BooleanVar(value=False)
        self.alpha_var = tk.DoubleVar(value=1.0) # For transparency
        self.colormap_var = tk.StringVar(value='gray') # Default colormap

        # Band Selection
        self.selected_bands_indices = [] # Store 0-based indices
        self.rgb_vars = [tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self.rgb_combos = []

        # Create widgets
        self._create_widgets()

    def set_plot_update_callback(self, callback):
        """Set the callback function to trigger plot updates."""
        self.plot_update_callback = callback

    def _create_widgets(self):
        """Create the control panel widgets"""
        # --- Load Section ---
        load_frame = ttk.Frame(self.frame)
        load_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(load_frame, text="Load Imagery", command=self.load_imagery).pack(fill=tk.X)

        # --- Band Selection Section ---
        band_frame = ttk.LabelFrame(self.frame, text="Available Bands")
        band_frame.pack(fill=tk.X, pady=5)

        list_frame = ttk.Frame(band_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.bands_listbox = tk.Listbox(
            list_frame, selectmode=tk.MULTIPLE, height=8,
            yscrollcommand=scrollbar.set, exportselection=False # Prevent deselection on other focus
        )
        self.bands_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.bands_listbox.yview)
        # Bind selection event to update internal state and trigger plot
        self.bands_listbox.bind('<<ListboxSelect>>', self.on_band_select)

        ttk.Button(band_frame, text="Plot Selected Band(s)", command=self.trigger_plot_update).pack(fill=tk.X, padx=5, pady=(0,5))

        # --- RGB Composite Section ---
        rgb_main_frame = ttk.LabelFrame(self.frame, text="RGB Composite")
        rgb_main_frame.pack(fill=tk.X, pady=5)

        rgb_select_frame = ttk.Frame(rgb_main_frame)
        rgb_select_frame.pack(fill=tk.X, pady=5, padx=5)

        band_options = ["R:", "G:", "B:"]
        self.rgb_combos = [] # Reset list before creating
        for i, option in enumerate(band_options):
            ttk.Label(rgb_select_frame, text=option, width=3).grid(row=0, column=i*2, sticky=tk.W)
            combo = ttk.Combobox(
                rgb_select_frame, textvariable=self.rgb_vars[i], width=5, state='readonly'
            )
            combo.grid(row=0, column=i*2+1, padx=(0,5), pady=2)
            self.rgb_combos.append(combo)

        ttk.Button(rgb_main_frame, text="Create RGB Composite", command=self.create_rgb_composite).pack(fill=tk.X, padx=5, pady=(0,5))


        # --- Visualization Options Section ---
        vis_frame = ttk.LabelFrame(self.frame, text="Visualization Options")
        vis_frame.pack(fill=tk.X, pady=5)

        # Use a grid inside for alignment
        options_grid = ttk.Frame(vis_frame, padding=5)
        options_grid.pack(fill=tk.X)
        options_grid.columnconfigure(0, weight=1) # Allow scale to expand

        # Checkbuttons - trigger plot update on change
        ttk.Checkbutton(options_grid, text="Scale Data (2-98%)", variable=self.scale_var, command=self.trigger_plot_update).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(options_grid, text="Show Colorbar", variable=self.colorbar_var, command=self.trigger_plot_update).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(options_grid, text="Equalize Histogram", variable=self.equalize_hist_var, command=self.trigger_plot_update).grid(row=2, column=0, sticky=tk.W, pady=2)

        # Colormap Dropdown
        ttk.Label(options_grid, text="Colormap:").grid(row=3, column=0, sticky=tk.W, pady=(5,2))
        # Provide a curated list first, then all others
        colormaps = ['gray', 'viridis', 'plasma', 'inferno', 'magma', 'cividis',
                     'RdYlGn', 'Blues', 'Greens', 'YlOrBr', 'RdBu', 'binary'] + sorted(list(plt.colormaps()))
        # Remove duplicates if any standard ones were also in plt.colormaps()
        unique_colormaps = sorted(list(set(colormaps)), key=lambda x: (colormaps.index(x) if x in colormaps[:12] else float('inf'), x))

        self.colormap_combo = ttk.Combobox(
            options_grid, textvariable=self.colormap_var, width=18, state='readonly',
            values=unique_colormaps
        )
        self.colormap_combo.grid(row=4, column=0, sticky=tk.W, pady=2)
        self.colormap_combo.bind("<<ComboboxSelected>>", lambda e: self.trigger_plot_update())

        # Transparency Slider
        ttk.Label(options_grid, text="Transparency:").grid(row=5, column=0, sticky=tk.W, pady=(5,2))
        self.alpha_scale = ttk.Scale(
            options_grid, from_=0.0, to=1.0, variable=self.alpha_var,
            orient=tk.HORIZONTAL, command=lambda e: self.trigger_plot_update(), # Update on change
            style='Horizontal.TScale' # Apply custom style if defined
        )
        self.alpha_scale.grid(row=6, column=0, sticky=tk.EW, pady=2)


        # --- Status Label ---
        ttk.Separator(self.frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        status_label = ttk.Label(self.frame, textvariable=self.status_var, wraplength=380, justify=tk.LEFT)
        status_label.pack(pady=5, fill=tk.X, anchor='s') # Anchor south

    def load_imagery(self):
        """Load satellite imagery file using the utility function."""
        file_path = filedialog.askopenfilename(
            title="Select Satellite Imagery",
            filetypes=[("GeoTIFF files", "*.tif *.tiff"), ("All files", "*.*")]
        )
        if not file_path: return # User cancelled

        self.image_path = file_path
        self.status_var.set(f"Loading {os.path.basename(file_path)}...")
        self.frame.update_idletasks() # Ensure status message is shown

        try:
            # Use the utility function which now handles errors
            loaded_data = load_satellite_imagery(file_path)

            # Pass loaded data to the plot panel (which triggers app callback)
            if self.plot_panel and hasattr(self.plot_panel, 'set_imagery_data'):
                 self.plot_panel.set_imagery_data(loaded_data)
            else:
                 # Should not happen if structure is correct
                 raise RuntimeError("Plot panel not available or missing set_imagery_data method.")

            self.status_var.set(f"Loaded: {os.path.basename(file_path)} ({len(loaded_data['bands'])} bands)")

        except FileNotFoundError as e:
             messagebox.showerror("Load Error", str(e))
             self.status_var.set("Error: File not found.")
             if self.plot_panel and hasattr(self.plot_panel, 'set_imagery_data'):
                 self.plot_panel.set_imagery_data(None) # Clear data on error
        except Exception as e:
             # Catch errors from load_satellite_imagery or set_imagery_data
             messagebox.showerror("Load Error", f"Failed to load or process imagery:\n{str(e)}")
             self.status_var.set("Error loading imagery.")
             if self.plot_panel and hasattr(self.plot_panel, 'set_imagery_data'):
                 self.plot_panel.set_imagery_data(None) # Clear data on error


    def update_bands(self, imagery_data):
        """Update band lists and RGB combos when new imagery is loaded via callback."""
        self.imagery_data = imagery_data # Store local reference
        self.bands_listbox.delete(0, tk.END) # Clear existing items

        if not imagery_data or 'band_names' not in imagery_data:
             # Handle case where data is cleared or invalid
             for combo in self.rgb_combos:
                 combo['values'] = []
                 combo.set('')
             self.selected_bands_indices = []
             return

        band_names = self.imagery_data.get('band_names', [])
        num_bands = len(band_names)

        # Populate listbox (Show 1-based index and name)
        for i, band_name in enumerate(band_names):
            # Truncate long band names if needed for display
            display_name = band_name if len(band_name) < 40 else band_name[:37] + "..."
            self.bands_listbox.insert(tk.END, f"{i+1}: {display_name}")

        # Update RGB combo boxes
        combo_values = [str(i+1) for i in range(num_bands)]
        for combo in self.rgb_combos:
            combo['values'] = combo_values
            combo.set('') # Clear previous selection

        # Suggest default RGB based on band count/names (simple heuristic)
        if num_bands >= 3:
            # Default for generic RGB
            red_idx, green_idx, blue_idx = 3, 2, 1
            # Check for common satellite band orders
            if num_bands >= 7 and any(b.lower().startswith("band") for b in band_names): # Landsat-like
                 red_idx, green_idx, blue_idx = 4, 3, 2
            elif any("B04" in name or "B4" in name for name in band_names) and \
                 any("B03" in name or "B3" in name for name in band_names) and \
                 any("B02" in name or "B2" in name for name in band_names): # Sentinel-2 like
                 red_idx, green_idx, blue_idx = 4, 3, 2

            # Set if indices are valid
            if red_idx <= num_bands: self.rgb_vars[0].set(str(red_idx))
            if green_idx <= num_bands: self.rgb_vars[1].set(str(green_idx))
            if blue_idx <= num_bands: self.rgb_vars[2].set(str(blue_idx))

        # Automatically select and plot the first band after loading
        if num_bands > 0:
            self.bands_listbox.selection_clear(0, tk.END) # Clear any previous selection
            self.bands_listbox.selection_set(0)
            self.bands_listbox.activate(0)
            self.on_band_select(None) # Trigger selection logic and plot update

    def on_band_select(self, event):
        """Update selected indices when listbox selection changes."""
        # Get current selections (indices of the listbox items)
        selected_items_indices = self.bands_listbox.curselection()
        # Map listbox indices to 0-based band indices
        self.selected_bands_indices = []
        for item_idx in selected_items_indices:
            try:
                # Extract the 1-based index from the string "i: name"
                band_idx_one_based = int(self.bands_listbox.get(item_idx).split(':')[0])
                self.selected_bands_indices.append(band_idx_one_based - 1) # Store 0-based index
            except (ValueError, IndexError):
                print(f"Warning: Could not parse band index from listbox item: {self.bands_listbox.get(item_idx)}")
                continue # Skip malformed items

        # Trigger plot update only if selection is valid
        if self.selected_bands_indices:
             self.trigger_plot_update()
        # else: handle case with no selection if needed (e.g., clear plot or show message)


    def get_current_options(self):
        """Gather current visualization options from the UI controls."""
        # Note: band_indices are now updated by on_band_select
        options = {
            'scale': self.scale_var.get(),
            'colorbar': self.colorbar_var.get(),
            'equalize': self.equalize_hist_var.get(),
            'colormap': self.colormap_var.get(),
            'alpha': self.alpha_var.get(),
            'band_indices': self.selected_bands_indices, # Use the updated list
            # 'plot_type' will be set by the calling function (plot bands vs RGB)
        }
        return options

    def trigger_plot_update(self):
        """Request the plot panel to update with current band selection and options."""
        if not self.imagery_data:
            return # Do nothing if no imagery is loaded
        if not self.selected_bands_indices:
             # Optionally clear plot or show message if nothing selected
             # self.plot_panel.clear_plot() # Need to add clear_plot method to PlotPanel
             # self.status_var.set("Select one or more bands to plot.")
             return

        if self.plot_update_callback:
            options = self.get_current_options()
            options['plot_type'] = 'bands' # Set plot type for band plotting
            self.plot_update_callback(self.imagery_data, options)
            self.status_var.set(f"Plotting {len(self.selected_bands_indices)} band(s)...")


    def create_rgb_composite(self):
        """Validate RGB selection and trigger RGB plot update."""
        if not self.imagery_data:
            messagebox.showwarning("No Imagery", "Please load imagery first.")
            return

        r_band_str = self.rgb_vars[0].get()
        g_band_str = self.rgb_vars[1].get()
        b_band_str = self.rgb_vars[2].get()

        if not (r_band_str and g_band_str and b_band_str):
            messagebox.showinfo("Info", "Please select bands for R, G, and B channels.")
            return

        try:
            # Convert 1-based selection from Combobox to 0-based index
            r_idx = int(r_band_str) - 1
            g_idx = int(g_band_str) - 1
            b_idx = int(b_band_str) - 1

            # Validate indices against the number of bands loaded
            num_bands = len(self.imagery_data['bands'])
            if not (0 <= r_idx < num_bands and 0 <= g_idx < num_bands and 0 <= b_idx < num_bands):
                 raise ValueError("Selected band index is out of range for the loaded image.")

            # Get common visualization options, then add RGB specific ones
            options = self.get_current_options()
            options.update({
                'plot_type': 'rgb', # Set plot type
                'r_idx': r_idx,
                'g_idx': g_idx,
                'b_idx': b_idx
            })
            # We don't need 'band_indices' or 'colormap' for RGB plot type
            options.pop('band_indices', None)
            options.pop('colormap', None)


            if self.plot_update_callback:
                self.plot_update_callback(self.imagery_data, options)
                self.status_var.set(f"Created RGB composite (Bands {r_band_str}, {g_band_str}, {b_band_str})")
            else:
                 messagebox.showerror("Error", "Plot update callback not set.")


        except ValueError as e:
            messagebox.showerror("RGB Error", f"Invalid band selection for RGB composite:\n{e}")
            self.status_var.set("Error creating RGB composite")
        except Exception as e:
             # Catch other potential errors during plotting
            messagebox.showerror("RGB Error", f"Failed to create RGB composite:\n{str(e)}")
            self.status_var.set("Error creating RGB composite")