"""
Utility functions for visualizing satellite imagery using Matplotlib
"""

import os # For short band names in RGB title
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from skimage import exposure # For histogram equalization

# Import AFTER ensuring code in imagery.py is correct
from src.utils.imagery import get_band_statistics
from src.utils.indices import COMMON_INDICES # To get index full name for title


def _apply_enhancements(band_data, options):
    """
    Helper function to apply histogram equalization and/or scaling.
    Handles NaN values. Returns enhanced data and vmin/vmax for plotting.
    """
    # Work with a float copy to avoid modifying original data
    # Ensure input is float for calculations
    enhanced_data = band_data.astype(np.float32, copy=True)
    vmin, vmax = None, None # Initialize vmin/vmax

    # 1. Apply Histogram Equalization (if requested)
    if options.get('equalize', False):
        try:
            # Check for edge cases: all NaN or uniform value
            valid_mask = ~np.isnan(enhanced_data)
            if not np.any(valid_mask) or np.nanmin(enhanced_data[valid_mask]) == np.nanmax(enhanced_data[valid_mask]):
                 # Cannot equalize uniform or all-NaN data, leave as is
                 pass
            else:
                 # Apply equalization only to valid pixels
                 # equalize_hist outputs values in [0, 1]
                 enhanced_data[valid_mask] = exposure.equalize_hist(enhanced_data[valid_mask])
                 # Set vmin/vmax for equalized data (typically 0-1)
                 vmin, vmax = 0.0, 1.0
        except Exception as e:
             print(f"Warning: Histogram equalization failed: {e}. Skipping equalization.")
             # Fall back to original data if equalization fails

    # 2. Apply Scaling (if requested AND not already handled by equalization)
    # Scaling uses percentile_2 and percentile_98
    if options.get('scale', False) and vmin is None: # Apply if 'scale' is true and equalization didn't set vmin/vmax
        stats = get_band_statistics(enhanced_data) # Get stats of potentially equalized data
        # Check if stats are valid and provide a range
        if stats['min'] is not None and stats['max'] is not None and \
           stats['percentile_2'] is not None and stats['percentile_98'] is not None and \
           stats['percentile_2'] < stats['percentile_98']:
            vmin = stats['percentile_2']
            vmax = stats['percentile_98']
        # Else: keep vmin/vmax as None, let imshow scale automatically based on actual min/max

    return enhanced_data, vmin, vmax


def plot_single_band(fig, band_data, band_name, options):
    """Plot a single band with enhancements and colorbar."""
    ax = fig.add_subplot(111)

    # Apply enhancements (scaling/equalization)
    enhanced_data, vmin, vmax = _apply_enhancements(band_data, options)
    cmap = options.get('colormap', 'gray')
    alpha = options.get('alpha', 1.0)

    # Plot the image
    im = ax.imshow(enhanced_data, cmap=cmap, vmin=vmin, vmax=vmax, alpha=alpha, interpolation='none') # Use 'none' interpolation
    ax.set_title(band_name, fontsize=11)
    ax.set_xticks([]) # Hide axes ticks
    ax.set_yticks([])

    # Add colorbar if requested
    if options.get('colorbar', True):
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04) # Adjust fraction/pad as needed
        # Set colorbar label based on enhancement
        cbar_label = 'Pixel Value'
        if options.get('equalize', False):
            cbar_label = 'Enhanced Value (Equalized)'
        elif options.get('scale', False):
             cbar_label = 'Pixel Value (Scaled 2-98%)'
        cbar.set_label(cbar_label)
        cbar.ax.tick_params(labelsize=8) # Smaller ticks on colorbar


def plot_multiple_bands(fig, bands, band_names, options):
    """Plot multiple bands in subplots with enhancements."""
    n_bands = len(bands)
    if n_bands == 0: return # Nothing to plot

    # Calculate subplot grid layout (e.g., 2x2, 3x2, 3x3)
    n_cols = int(np.ceil(np.sqrt(n_bands)))
    n_rows = int(np.ceil(n_bands / n_cols))

    for i, (band_data, name) in enumerate(zip(bands, band_names)):
        ax = fig.add_subplot(n_rows, n_cols, i + 1)

        # Apply enhancements per band
        enhanced_data, vmin, vmax = _apply_enhancements(band_data, options)
        cmap = options.get('colormap', 'gray')
        alpha = options.get('alpha', 1.0)

        # Plot the band
        im = ax.imshow(enhanced_data, cmap=cmap, vmin=vmin, vmax=vmax, alpha=alpha, interpolation='none')
        ax.set_title(name, fontsize=9) # Smaller font for subplots
        ax.set_xticks([])
        ax.set_yticks([])

        # Add colorbar if requested
        if options.get('colorbar', True):
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            # No label needed for multi-band colorbars usually, keep simple
            cbar.ax.tick_params(labelsize=7) # Even smaller ticks


def create_rgb_composite(fig, all_bands_data, rgb_band_names, options):
    """Create RGB composite image, applying enhancements per channel."""
    ax = fig.add_subplot(111)

    r_idx = options.get('r_idx', 0)
    g_idx = options.get('g_idx', 1)
    b_idx = options.get('b_idx', 2)

    # Extract the required bands safely
    try:
        # Use copies to avoid modifying original data in imagery_data['bands']
        r_data = all_bands_data[r_idx].copy()
        g_data = all_bands_data[g_idx].copy()
        b_data = all_bands_data[b_idx].copy()
    except IndexError:
        raise ValueError(f"Invalid RGB band index provided (R:{r_idx+1}, G:{g_idx+1}, B:{b_idx+1}). Max index: {len(all_bands_data)-1}")

    # Apply enhancements (scaling/equalization) independently to each channel
    # We don't use the vmin/vmax return here, as RGB needs scaling 0-1 later
    r_enhanced, _, _ = _apply_enhancements(r_data, options)
    g_enhanced, _, _ = _apply_enhancements(g_data, options)
    b_enhanced, _, _ = _apply_enhancements(b_data, options)

    # Stack the enhanced bands
    rgb_composite = np.dstack((r_enhanced, g_enhanced, b_enhanced))

    # --- Scale the result to the display range [0, 1] ---
    # This is crucial for correct color display with imshow
    # Handle potential NaNs during scaling
    rgb_display = np.zeros_like(rgb_composite, dtype=float) # Output array
    valid_mask_rgb = ~np.isnan(rgb_composite).any(axis=2) # Mask where any channel is NaN

    for i in range(3): # Scale each channel
         band = rgb_composite[:, :, i]
         valid_mask_band = ~np.isnan(band) & valid_mask_rgb # Combine masks

         if np.any(valid_mask_band):
             bmin = np.min(band[valid_mask_band]) # Use nanmin equivalent
             bmax = np.max(band[valid_mask_band])
             if bmax > bmin:
                 # Scale valid pixels to 0-1
                 rgb_display[valid_mask_band, i] = (band[valid_mask_band] - bmin) / (bmax - bmin)
             else:
                 # Handle uniform band (avoid division by zero)
                 rgb_display[valid_mask_band, i] = 0.5 # Assign a mid-value
         # Pixels that were NaN remain 0 in rgb_display (or could be set to NaN again)

    # Clip the final result to ensure it's strictly within [0, 1]
    rgb_display = np.clip(rgb_display, 0, 1)

    # Apply overall transparency
    alpha = options.get('alpha', 1.0)

    # Display the RGB image
    ax.imshow(rgb_display, alpha=alpha, interpolation='none')

    # --- Set Title ---
    # Use the original, full band names passed in rgb_band_names
    r_name_full = rgb_band_names[0]
    g_name_full = rgb_band_names[1]
    b_name_full = rgb_band_names[2]
    # Create shorter versions for the title if names are long
    r_short = r_name_full if len(r_name_full)<15 else r_name_full[:12]+"..."
    g_short = g_name_full if len(g_name_full)<15 else g_name_full[:12]+"..."
    b_short = b_name_full if len(b_name_full)<15 else b_name_full[:12]+"..."
    ax.set_title(f"RGB Composite\nR: {r_short}, G: {g_short}, B: {b_short}", fontsize=10)

    # Hide axes
    ax.set_xticks([])
    ax.set_yticks([])


def plot_spectral_index(fig, index_array, index_name, description, colormap, value_range, options):
    """Plot a spectral index with specified colormap, range, and description."""
    ax = fig.add_subplot(111)

    # --- Enhancements ---
    # For indices, primarily rely on vmin/vmax from index definition.
    # Scaling/Equalization usually distorts the meaning of index values.
    # However, allow overall transparency.
    alpha = options.get('alpha', 1.0)

    # --- Plotting ---
    im = ax.imshow(index_array, cmap=colormap,
                   vmin=value_range[0] if value_range else None, # Use provided range
                   vmax=value_range[1] if value_range else None,
                   alpha=alpha, interpolation='none')

    # --- Titles and Labels ---
    full_name = COMMON_INDICES.get(index_name, {}).get('name', 'Unknown Index')
    ax.set_title(f"{index_name}: {full_name}", fontsize=11)
    ax.set_xticks([])
    ax.set_yticks([])

    # --- Colorbar ---
    if options.get('colorbar', True):
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label(f"{index_name} Value")
        cbar.ax.tick_params(labelsize=8)

    # --- Description Box ---
    if description: # Only show box if description exists
        props = dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.75, edgecolor='gray')
        ax.text(0.02, 0.02, description, transform=ax.transAxes, fontsize=8,
                verticalalignment='bottom', bbox=props, wrap=True)