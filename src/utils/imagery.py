"""
Utility functions for loading and processing satellite imagery
"""

import os
import sys # Needed for sys.platform check below
import numpy as np
import rasterio
from rasterio.errors import RasterioIOError

def load_satellite_imagery(file_path):
    """
    Load satellite imagery from a file using rasterio.

    Parameters
    ----------
    file_path : str
        Path to the satellite imagery file (e.g., GeoTIFF).

    Returns
    -------
    dict
        Dictionary containing:
        - 'bands': List of NumPy arrays, one for each band.
        - 'band_names': List of descriptive names for each band.
        - 'metadata': Dictionary of metadata from the raster file.
        - 'file_path': The original file path.

    Raises
    ------
    FileNotFoundError
        If the file_path does not exist.
    RasterioIOError
        If rasterio fails to open or read the file.
    Exception
        For other potential errors during loading.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Imagery file not found: {file_path}")

    try:
        with rasterio.open(file_path) as src:
            # --- Metadata ---
            metadata = src.meta.copy() # Get a mutable copy
            metadata['file_path'] = file_path # Add file path to metadata for reference

            # --- Bands ---
            # Read all bands into a list
            bands = [src.read(i).astype(np.float32) for i in range(1, src.count + 1)] # Read as float32 for calculations

            # --- Band Names ---
            # Robustly get band names, ensuring they are strings
            band_names = []
            # Prioritize descriptions if they exist and match band count
            if src.descriptions and len(src.descriptions) == src.count:
                for i, desc in enumerate(src.descriptions):
                    if desc is not None:
                        band_names.append(str(desc)) # *** Explicitly convert to string ***
                    else:
                        # Provide a default if description is None
                        band_names.append(f"Band {i+1}")
            else:
                # Fallback to generating names using tags or generic names
                for i in range(1, src.count + 1):
                     tags = src.tags(i)
                     # Check common tags for band names/descriptions
                     name_tag = tags.get('DESCRIPTION', tags.get('Name', tags.get('BandName', tags.get('LAYER_TYPE')))) # Added LAYER_TYPE
                     if name_tag is not None: # Check if tag exists and is not None
                         band_names.append(str(name_tag)) # *** Explicitly convert to string ***
                     else:
                         band_names.append(f"Band {i}") # Generic fallback

            # --- Result ---
            result = {
                'bands': bands,
                'band_names': band_names,
                'metadata': metadata,
                'file_path': file_path
            }
            return result

    except RasterioIOError as e:
        raise RasterioIOError(f"Rasterio failed to read file '{os.path.basename(file_path)}': {e}") from e
    except Exception as e:
        raise Exception(f"An unexpected error occurred loading '{os.path.basename(file_path)}': {e}") from e


def get_band_statistics(band_data):
    """
    Calculate basic statistics for a single band (NumPy array).

    Handles potential NaN values.

    Parameters
    ----------
    band_data : numpy.ndarray
        The 2D array representing the band data. Assumed to be float.

    Returns
    -------
    dict
        Dictionary with statistics ('min', 'max', 'mean', 'std',
        'percentile_2', 'percentile_98'). Values can be None if
        the band contains only NaN or is empty.
    """
    # Input validation
    if not isinstance(band_data, np.ndarray):
        # This case should ideally not be reached if loading converts to ndarray
        print("Warning: get_band_statistics received non-ndarray input.")
        return { 'min': None, 'max': None, 'mean': None, 'std': None, 'percentile_2': None, 'percentile_98': None }

    # Filter out NaN values for calculations
    valid_data = band_data[~np.isnan(band_data)]

    if valid_data.size == 0:
        # Handle case where band is empty or all NaN
        return {
            'min': None, 'max': None, 'mean': None, 'std': None,
            'percentile_2': None, 'percentile_98': None
        }

    try:
        # Calculate statistics on the valid (non-NaN) data
        stats = {
            'min': float(np.min(valid_data)), # Cast to standard float
            'max': float(np.max(valid_data)),
            'mean': float(np.mean(valid_data)),
            'std': float(np.std(valid_data)),
            'percentile_2': float(np.percentile(valid_data, 2)),
            'percentile_98': float(np.percentile(valid_data, 98))
        }
        # Check for potential NaN results from calculations if std is zero etc.
        for key, value in stats.items():
            if np.isnan(value):
                stats[key] = None # Replace NaN results with None
        return stats
    except Exception as e:
        # Catch potential numpy errors during calculation
        print(f"Warning: Could not calculate statistics for band. Error: {e}")
        return {
            'min': None, 'max': None, 'mean': None, 'std': None,
            'percentile_2': None, 'percentile_98': None
        }