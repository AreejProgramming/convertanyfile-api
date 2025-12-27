import os
import json
import time
import sys
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import io

def generate_session_id():
    return str(uuid.uuid4())

def validate_url(url):
    """
    Validate if URL is properly formatted
    """
    url_regex = re.compile(
        r'^(?:http|ftp)s?://'  # http://, https://, or ftp://
        r'(?:\S+(?::\S*)?@)?'  # optional user:pass@
        r'(?:'  # IP address exclusion
        r'(?:(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])'  # IP part 1
        r'\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])'  # IP part 2
        r'\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])'  # IP part 3
        r'\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-5])'  # IP part 4
        r')|'  # ...or...
        r'(?:(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)'  # domain name
        r'(?:\.(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)*'  # sub-domain
        r'(?:\.[a-z\u00a1-\uffff]{2,})'  # top-level domain
        r')'  # ...or...
        r'(?::\d{2,5})?'  # optional port
        r'(?:/[^\s]*)?$', re.IGNORECASE)
    
    return url_regex.match(url) is not None

def format_url(url):
    """
    Ensure URL has proper format with protocol
    """
    if not url:
        return None
    
    url = url.strip()
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Validate URL
    if not validate_url(url):
        return None
    
    return url

def capture_screenshot(driver, width, height, name):
    """
    Capture screenshot for specific viewport size
    """
    try:
        # Set window size
        driver.set_window_size(width, height)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Small delay to ensure rendering
        time.sleep(2)
        
        # Capture screenshot
        screenshot = driver.get_screenshot_as_png()
        
        # Convert to PIL Image
        img = Image.open(io.BytesIO(screenshot))
        
        # Save screenshot
        screenshot_path = f"screenshots/{name}_{width}x{height}.png"
        img.save(screenshot_path, 'PNG')
        
        return {
            "name": name,
            "width": width,
            "height": height,
            "screenshot": screenshot_path,
            "status": "success"
        }
    except Exception as e:
        print(f"Error capturing screenshot for {width}x{height}: {str(e)}")
        return {
            "name": name,
            "width": width,
            "height": height,
            "status": "error",
            "error": str(e)
        }

def preview_responsive_design(url):
    """
    Main function to preview responsive design for a URL
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting responsive preview for: {url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Capturing responsive previews...",
        "session_id": session_id
    }
    
    try:
        # Format and validate URL
        formatted_url = format_url(url)
        if not formatted_url:
            raise ValueError("Invalid URL format")
        
        print(f"Processing URL: {formatted_url}")
        
        # Create screenshots directory
        os.makedirs("screenshots", exist_ok=True)
        
        # Define viewport sizes
        viewports = [
            {"name": "Mobile", "width": 375, "height": 667},
            {"name": "Tablet", "width": 768, "height": 1024},
            {"name": "Desktop", "width": 1920, "height": 1080},
            {"name": "Large Desktop", "width": 2560, "height": 1440}
        ]
        
        # Setup Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Initialize WebDriver
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to URL
        print(f"Loading {formatted_url}...")
        driver.get(formatted_url)
        
        # Wait for page to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Capture screenshots for each viewport
        print("Capturing screenshots for different viewports...")
        viewport_results = []
        
        for viewport in viewports:
            print(f"Capturing {viewport['name']} viewport ({viewport['width']}x{viewport['height']})...")
            result = capture_screenshot(driver, viewport["width"], viewport["height"], viewport["name"])
            viewport_results.append(result)
        
        # Close driver
        driver.quit()
        
        # Count successful captures
        successful = sum(1 for v in viewport_results if v["status"] == "success")
        failed = len(viewport_results) - successful
        
        # Create final results
        results = {
            "status": "success",
            "url": formatted_url,
            "timestamp": time.time(),
            "session_id": session_id,
            "summary": {
                "total": len(viewport_results),
                "successful": successful,
                "failed": failed
            },
            "viewports": viewport_results
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
    
    # Always write results to file, even if there was an error
    try:
        with open('results.json', 'w') as f:
            json.dump(results, f)
        print("Results successfully written to results.json")
    except Exception as file_error:
        print(f"ERROR writing results file: {str(file_error)}")
        # Try to write to a different location as fallback
        try:
            with open(f'/tmp/results_{session_id}.json', 'w') as f:
                json.dump(results, f)
            print(f"Results written to fallback location: /tmp/results_{session_id}.json")
        except Exception as fallback_error:
            print(f"ERROR writing to fallback location: {str(fallback_error)}")
    
    # Always output the results, even if there was an error
    print(f"results={json.dumps(results)}")
    return results

if __name__ == "__main__":
    url = os.environ.get("URL")
    if not url:
        print("ERROR: URL environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "URL environment variable not set.",
            "session_id": os.environ.get("SESSION_ID", "unknown")
        }
        
        # Write error results to file
        try:
            with open('results.json', 'w') as f:
                json.dump(error_result, f)
            print("Error results written to results.json")
        except Exception as file_error:
            print(f"ERROR writing error results file: {str(file_error)}")
        
        print(f"results={json.dumps(error_result)}")
        sys.exit(1)
        
    preview_results = preview_responsive_design(url)
    
    # The results are already printed in the function
    sys.exit(0)
