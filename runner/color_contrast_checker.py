# File: runner/color_contrast_checker.py

import os
import json
import time
import sys
import uuid

def generate_session_id():
    return str(uuid.uuid4())

def hex_to_rgb(hex_color):
    """
    Convert hex color to RGB
    """
    # Remove the hash at the start if it's there
    clean_hex = hex_color.replace('#', '')
    
    # Handle shorthand hex (e.g., #03F -> #0033FF)
    if len(clean_hex) == 3:
        clean_hex = ''.join([char*2 for char in clean_hex])
    
    try:
        result = tuple(int(clean_hex[i:i+2], 16) for i in (0, 2, 4))
        return {
            "r": result[0],
            "g": result[1],
            "b": result[2]
        }
    except (ValueError, IndexError):
        return None

def calculate_luminance(rgb_color):
    """
    Calculate relative luminance of a color
    """
    if not rgb_color:
        return 0
    
    r, g, b = rgb_color["r"], rgb_color["g"], rgb_color["b"]
    
    # Normalize RGB values to 0-1 range
    rsRGB = r / 255
    gsRGB = g / 255
    bsRGB = b / 255
    
    # Apply gamma correction
    rLinear = rsRGB / 12.92 if rsRGB <= 0.03928 else ((rsRGB + 0.055) / 1.055) ** 2.4
    gLinear = gsRGB / 12.92 if gsRGB <= 0.03928 else ((gsRGB + 0.055) / 1.055) ** 2.4
    bLinear = bsRGB / 12.92 if bsRGB <= 0.03928 else ((bsRGB + 0.055) / 1.055) ** 2.4
    
    # Calculate luminance using the sRGB luma coefficients
    return 0.2126 * rLinear + 0.7152 * gLinear + 0.0722 * bLinear

def calculate_contrast_ratio(color1, color2):
    """
    Calculate contrast ratio between two colors
    """
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    
    if not rgb1 or not rgb2:
        return 1
    
    lum1 = calculate_luminance(rgb1)
    lum2 = calculate_luminance(rgb2)
    
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    
    return (lighter + 0.05) / (darker + 0.05)

def check_color_contrast(foreground_color, background_color):
    """
    Check color contrast against WCAG standards
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting color contrast check for foreground: {foreground_color}, background: {background_color}")
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "Analysis failed to start.",
        "session_id": session_id
    }
    
    try:
        # Validate input colors
        if not foreground_color or not background_color:
            raise ValueError("Both foreground and background colors must be provided")
        
        # Calculate contrast ratio
        ratio = calculate_contrast_ratio(foreground_color, background_color)
        
        # Calculate luminance values
        foreground_luminance = calculate_luminance(hex_to_rgb(foreground_color))
        background_luminance = calculate_luminance(hex_to_rgb(background_color))
        
        # Check WCAG compliance
        passes_aa_normal = ratio >= 4.5
        passes_aaa_normal = ratio >= 7
        passes_aa_large = ratio >= 3
        passes_aaa_large = ratio >= 4.5
        
        results = {
            "status": "success",
            "foreground_color": foreground_color,
            "background_color": background_color,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "ratio": round(ratio, 2),
                "passes_aa_normal": passes_aa_normal,
                "passes_aaa_normal": passes_aaa_normal,
                "passes_aa_large": passes_aa_large,
                "passes_aaa_large": passes_aaa_large,
                "foreground_luminance": round(foreground_luminance, 2),
                "background_luminance": round(background_luminance, 2)
            }
        }
        
        print(f"Analysis complete. Contrast ratio: {ratio}:1")
        
    except Exception as e:
        # Catch any exception
        print(f"ERROR: An unexpected error occurred. Details: {e}")
        results = {
            "status": "error", 
            "message": f"An unexpected error occurred: {str(e)}",
            "session_id": session_id
        }
            
    return results

if __name__ == "__main__":
    foreground_color = os.environ.get("FOREGROUND_COLOR")
    background_color = os.environ.get("BACKGROUND_COLOR")
    
    if not foreground_color or not background_color:
        print("ERROR: FOREGROUND_COLOR and BACKGROUND_COLOR environment variables must be set.")
        sys.exit(1)
        
    analysis_results = check_color_contrast(foreground_color, background_color)
    
    # Print the results in a format that can be easily extracted
    print(f"results={json.dumps(analysis_results)}")
