"""
Remote Sensing Indices Calculator and Band Guesser
"""

import numpy as np
import re # For more flexible band name matching

# Dictionary of band combinations for common indices
# Using SWIR1/SWIR2 naming convention where applicable
COMMON_INDICES = {
    "NDVI": {
        "name": "Normalized Difference Vegetation Index",
        "formula": "(NIR - Red) / (NIR + Red)",
        "bands": ["NIR", "Red"],
        "description": "Measures vegetation health and density. Values range from -1 to 1, with higher values indicating denser vegetation.",
        "colormap": "RdYlGn",  # Red-Yellow-Green
        "range": [-0.2, 1.0],  # Typical visualization range
    },
    "NDWI": {
        "name": "Normalized Difference Water Index (McFeeters)",
        "formula": "(Green - NIR) / (Green + NIR)",
        "bands": ["Green", "NIR"],
        "description": "Delineates open water features. Positive values typically represent water bodies.",
        "colormap": "Blues",
        "range": [-0.5, 1.0],
    },
     "MNDWI": { # Modified NDWI (Xu) - Often better for separating water from built-up
        "name": "Modified NDWI (Xu)",
        "formula": "(Green - SWIR1) / (Green + SWIR1)",
        "bands": ["Green", "SWIR1"],
        "description": "Enhanced water detection, suppresses noise from built-up/soil areas.",
        "colormap": "Blues",
        "range": [-0.5, 1.0],
    },
    "NDBI": {
        "name": "Normalized Difference Built-up Index",
        "formula": "(SWIR1 - NIR) / (SWIR1 + NIR)",
        "bands": ["SWIR1", "NIR"],
        "description": "Highlights urban areas and built-up land. Higher values indicate built-up areas.",
        "colormap": "YlOrBr", # Yellow-Orange-Brown often used
        "range": [-0.5, 0.5],
    },
    "SAVI": {
        "name": "Soil Adjusted Vegetation Index",
        "formula": "(NIR - Red) * (1 + L) / (NIR + Red + L)",
        "bands": ["NIR", "Red"],
        "params": {"L": 0.5}, # Default L factor, can be adjusted
        "description": "Minimizes soil brightness influences (L=0.5 typical). Less sensitive than NDVI to soil background.",
        "colormap": "YlGn", # Yellow-Green
        "range": [-0.2, 1.0],
    },
    "EVI": {
        "name": "Enhanced Vegetation Index",
        "formula": "G * (NIR - Red) / (NIR + C1 * Red - C2 * Blue + L)",
        "bands": ["NIR", "Red", "Blue"],
        "params": {"G": 2.5, "C1": 6.0, "C2": 7.5, "L": 1.0}, # Standard Landsat/MODIS params
        "description": "Improved sensitivity in high biomass areas, reduced atmospheric influence compared to NDVI.",
        "colormap": "RdYlGn",
        "range": [-0.2, 1.0],
    },
     "NDSI": {
        "name": "Normalized Difference Snow Index",
        "formula": "(Green - SWIR1) / (Green + SWIR1)", # Same formula as MNDWI, interpretation differs
        "bands": ["Green", "SWIR1"],
        "description": "Used to detect snow and ice. Positive values typically represent snow cover. Separates snow from clouds.",
        "colormap": "Blues", # Often displayed with blues or specific snow maps
        "range": [-0.5, 1.0],
    },
    "NDMI": { # Also known as Normalized Difference Water Index (Gao)
        "name": "Normalized Difference Moisture Index (NDWI-Gao)",
        "formula": "(NIR - SWIR1) / (NIR + SWIR1)",
        "bands": ["NIR", "SWIR1"],
        "description": "Sensitive to vegetation water content and soil moisture. Higher values indicate higher moisture.",
        "colormap": "YlGnBu", # Blue indicates moisture
        "range": [-0.5, 1.0],
    },
     "BSI": {
        "name": "Bare Soil Index",
        "formula": "((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))",
        "bands": ["SWIR1", "Red", "NIR", "Blue"],
        "description": "Detects bare soil areas. Higher values indicate more exposed soil. Useful for soil mapping.",
        "colormap": "YlOrBr", # Earth tones
        "range": [-0.5, 0.5],
    },
    "NBR": {
        "name": "Normalized Burn Ratio",
        "formula": "(NIR - SWIR2) / (NIR + SWIR2)", # Uses SWIR2 (e.g., Landsat B7, Sentinel B12)
        "bands": ["NIR", "SWIR2"],
        "description": "Used for burn severity assessment. Compare pre/post fire. High values = healthy veg, low = burned.",
        "colormap": "RdYlGn", # Often RdYlGn for health or RdGy for severity diff
        "range": [-1.0, 1.0],
    },
    # Example of adding another index:
    # "GNDVI": {
    #     "name": "Green Normalized Difference Vegetation Index",
    #     "formula": "(NIR - Green) / (NIR + Green)",
    #     "bands": ["NIR", "Green"],
    #     "description": "Similar to NDVI, but uses Green instead of Red. More sensitive to chlorophyll concentration.",
    #     "colormap": "RdYlGn",
    #     "range": [-0.2, 1.0],
    # },
}


def guess_band_types(band_names):
    """
    Attempt to guess standard band types (Blue, Green, Red, NIR, SWIR1, SWIR2)
    based on common naming conventions in band names. More robust version.

    Parameters
    ----------
    band_names : list of str
        List of band names from the imagery metadata.

    Returns
    -------
    dict
        Dictionary mapping standard band types (str) to band indices (int, 0-based).
    """
    if not band_names:
        return {}

    band_mapping = {}
    num_bands = len(band_names)

    # Define keywords and patterns for each band type
    # Order patterns from more specific to less specific within a type
    # Use word boundaries (\b) where appropriate to avoid partial matches
    patterns = {
        # NIR: Check narrow NIR (B8A) before broad NIR (B8) for Sentinel-2
        "NIR": [r'\bb8a\b', r'\bb08a\b', r'nir.?narrow', r'nir.?broad', r'near.?infra', r'\bnir\b', r'\bb8\b', r'\bb0?8\b', r'\bband.?8\b', r'\bb5\b', r'\bb0?5\b', r'\bband.?5\b'],
        # SWIR 2: (e.g., ~2.2 um)
        "SWIR2": [r'\bb12\b', r'\bb0?12\b', r'\bband.?12', r'\bswir.?2\b', r'\bswir.?2.2', r'\bb7\b', r'\bb0?7\b', r'\bband.?7\b'], # S2 B12, L8/9 B7
        # SWIR 1: (e.g., ~1.6 um)
        "SWIR1": [r'\bb11\b', r'\bb0?11\b', r'\bband.?11', r'\bswir.?1\b', r'\bswir.?1.6', r'\bswir\b(?!.?2)', r'\bb6\b', r'\bb0?6\b', r'\bband.?6\b'], # S2 B11, L8/9 B6. Handle general 'swir' if not SWIR2
        # Red:
        "Red": [r'\bred\b', r'\bb4\b', r'\bb0?4\b', r'\bband.?4'],
        # Green:
        "Green": [r'\bgreen\b', r'\bb3\b', r'\bb0?3\b', r'\bband.?3'],
        # Blue: Also check for Coastal Aerosol bands often used as Blue
        "Blue": [r'\bblue\b', r'\bb2\b', r'\bb0?2\b', r'\bband.?2', r'coastal', r'aerosol', r'\bb1\b', r'\bb0?1\b', r'\bband.?1'], # L8/9 B2, S2 B2. Allow B1 as fallback.
    }

    # Keep track of indices already assigned to prevent multiple assignments
    assigned_indices = set()

    # Iterate through patterns (prioritized by the order above)
    for band_type, type_patterns in patterns.items():
        if band_type in band_mapping: continue # Skip if already found

        # Search for patterns within each band name
        for i, name in enumerate(band_names):
            if i in assigned_indices: continue # Skip if this band index is already assigned

            name_lower = name.lower()
            for pattern in type_patterns:
                if re.search(pattern, name_lower):
                    band_mapping[band_type] = i
                    assigned_indices.add(i)
                    # print(f"Matched: {name} -> {band_type} (Pattern: {pattern})") # Debugging
                    break # Stop searching patterns for this type once found
            if band_type in band_mapping: break # Move to next band type


    # --- Fallback based on band count (Less reliable) ---
    # If crucial bands like RGB are still missing, try positional guessing
    if num_bands >= 4: # Assume at least B, G, R, N
        if 'Blue' not in band_mapping and 1 not in assigned_indices: band_mapping['Blue'] = 1 # B2 is common
        if 'Green' not in band_mapping and 2 not in assigned_indices: band_mapping['Green'] = 2 # B3 is common
        if 'Red' not in band_mapping and 3 not in assigned_indices: band_mapping['Red'] = 3 # B4 is common
        if 'NIR' not in band_mapping and 4 not in assigned_indices: band_mapping['NIR'] = 4 # B5 (L8) or B8 (S2) - less certain
    elif num_bands == 3: # Assume RGB
        if 'Red' not in band_mapping and 0 not in assigned_indices: band_mapping['Red'] = 0
        if 'Green' not in band_mapping and 1 not in assigned_indices: band_mapping['Green'] = 1
        if 'Blue' not in band_mapping and 2 not in assigned_indices: band_mapping['Blue'] = 2

    # Final check: if 'SWIR' was mapped but not 'SWIR1', rename it to 'SWIR1'
    # as most indices use the ~1.6um SWIR band.
    if "SWIR" in band_mapping and "SWIR1" not in band_mapping:
        band_mapping["SWIR1"] = band_mapping.pop("SWIR")

    print(f"Guessed Band Mapping: {band_mapping}") # Useful for debugging
    return band_mapping


def calculate_index(bands, band_mapping, index_name):
    """
    Calculate a spectral index using provided bands and mapping.

    Parameters
    ----------
    bands : list of numpy.ndarray
        List containing the raster data for each band (assumed float32).
    band_mapping : dict
        Dictionary mapping standard band type names (str, e.g., "NIR")
        to their corresponding 0-based index in the `bands` list (int).
    index_name : str
        The abbreviation of the index to calculate (e.g., "NDVI").

    Returns
    -------
    tuple
        Containing:
        - index_array (numpy.ndarray): The calculated index values (float32).
        - description (str): A description of the index.
        - colormap (str): A suggested colormap name for visualization.
        - value_range (tuple): A suggested (min, max) value range for the colormap.

    Raises
    ------
    ValueError
        If the index_name is unknown or required bands are missing
        in the band_mapping or if indices are invalid.
    TypeError
        If input bands are not numpy arrays or mapping is not dict.
    """
    if index_name not in COMMON_INDICES:
        raise ValueError(f"Unknown index: '{index_name}'")

    index_info = COMMON_INDICES[index_name]
    required_bands = index_info["bands"]
    params = index_info.get("params", {})

    # --- Validate Inputs ---
    if not isinstance(bands, list) or not all(isinstance(b, np.ndarray) for b in bands):
         raise TypeError("Input 'bands' must be a list of NumPy arrays.")
    if not isinstance(band_mapping, dict):
        raise TypeError("Input 'band_mapping' must be a dictionary.")

    # Check if all required bands are present in the mapping
    missing_bands = [b for b in required_bands if b not in band_mapping]
    if missing_bands:
        raise ValueError(f"Missing required band mapping(s) for {index_name}: {', '.join(missing_bands)}")

    # Get the actual band data arrays using the mapping
    try:
        # Create a dictionary mapping band type name to the actual band data array
        B = {}
        num_bands_available = len(bands)
        for band_type in required_bands:
            band_idx = band_mapping[band_type]
            if not (0 <= band_idx < num_bands_available):
                 raise ValueError(f"Mapped index {band_idx} for '{band_type}' is out of range (0-{num_bands_available-1}).")
            # Ensure band data is float32 for calculations
            B[band_type] = bands[band_idx].astype(np.float32, copy=False) # Avoid unnecessary copy if already float32

    except KeyError as ke:
         # This shouldn't happen if missing_bands check passed, but good practice
         raise ValueError(f"Band type '{ke}' required for {index_name} not found in mapping keys.") from ke
    except IndexError as ie:
         # This error is caught by the explicit index check above now
         raise ValueError(f"Invalid band index found in mapping for {index_name}. Ensure mapping matches loaded bands.") from ie


    # --- Calculate Index ---
    # Use np.errstate to handle potential division by zero or invalid operations
    # Results will be NaN where these occur.
    with np.errstate(divide='ignore', invalid='ignore'):
        # Use the 'B' dictionary for cleaner access to band data
        if index_name == "NDVI":
            num = B["NIR"] - B["Red"]
            den = B["NIR"] + B["Red"]
        elif index_name == "NDWI": # McFeeters
            num = B["Green"] - B["NIR"]
            den = B["Green"] + B["NIR"]
        elif index_name == "MNDWI": # Xu
            num = B["Green"] - B["SWIR1"]
            den = B["Green"] + B["SWIR1"]
        elif index_name == "NDBI":
            num = B["SWIR1"] - B["NIR"]
            den = B["SWIR1"] + B["NIR"]
        elif index_name == "SAVI":
            L = params.get("L", 0.5)
            num = (B["NIR"] - B["Red"]) * (1 + L)
            den = B["NIR"] + B["Red"] + L
        elif index_name == "EVI":
            G = params.get("G", 2.5)
            C1 = params.get("C1", 6.0)
            C2 = params.get("C2", 7.5)
            L = params.get("L", 1.0)
            num = G * (B["NIR"] - B["Red"])
            den = B["NIR"] + C1 * B["Red"] - C2 * B["Blue"] + L
        elif index_name == "NDSI":
            num = B["Green"] - B["SWIR1"]
            den = B["Green"] + B["SWIR1"]
        elif index_name == "NDMI": # Gao
            num = B["NIR"] - B["SWIR1"]
            den = B["NIR"] + B["SWIR1"]
        elif index_name == "BSI":
            num = (B["SWIR1"] + B["Red"]) - (B["NIR"] + B["Blue"])
            den = (B["SWIR1"] + B["Red"]) + (B["NIR"] + B["Blue"])
        elif index_name == "NBR":
            # NBR requires SWIR2 specifically
            if "SWIR2" not in B:
                 raise ValueError(f"NBR calculation requires 'SWIR2' band mapping.")
            num = B["NIR"] - B["SWIR2"]
            den = B["NIR"] + B["SWIR2"]
        # Add other index calculations here using elif blocks...
        # elif index_name == "GNDVI":
        #     num = B["NIR"] - B["Green"]
        #     den = B["NIR"] + B["Green"]
        else:
            # This case should be unreachable due to the initial check
            raise ValueError(f"Index calculation logic not implemented for: {index_name}")

        # Perform the division, placing NaN where the denominator is zero
        # Use np.full_like to create an output array of the correct shape and type, filled with NaN
        index = np.divide(num, den, out=np.full_like(num, np.nan, dtype=np.float32), where=den != 0)

    # Return results
    return (
        index,
        index_info["description"],
        index_info["colormap"],
        index_info["range"]
    )


def get_available_indices(band_mapping):
    """
    Get a list of indices that can be calculated with the available band mapping.

    Parameters
    ----------
    band_mapping : dict
        Dictionary mapping standard band type names (str) to their
        0-based band indices (int).

    Returns
    -------
    list
        List of index abbreviations (str) that can be calculated. Returns
        an empty list if band_mapping is None or empty.
    """
    if not band_mapping:
        return []

    available_indices = []
    # Get the set of band types actually available in the current mapping
    mapped_band_types = set(band_mapping.keys())

    # Check each known index
    for index_name, index_info in COMMON_INDICES.items():
        # Get the set of band types required by this index
        required_bands = set(index_info["bands"])
        # If all required band types are present in the current mapping, add the index
        if required_bands.issubset(mapped_band_types):
            available_indices.append(index_name)

    return available_indices