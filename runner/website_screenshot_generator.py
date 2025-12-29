# File: runner/website_screenshot_generator.py

import os
import json
import time
import sys
import uuid
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import io

def generate_session_id():
    return str(uuid.uuid4())

def normalize_url(url):
    """
    Normalize the URL to ensure it has a protocol
    """
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def capture_screenshot(url, device, format_type, quality, full_page, session_id):
    """
    Capture a screenshot of a website
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", session_id)
    
    # Normalize the URL
    url = normalize_url(url)
    
    print(f"Starting screenshot capture for: {url}")
    print(f"Device: {device}")
    print(f"Format: {format_type}")
    print(f"Quality: {quality}")
    print(f"Full page: {full_page}")
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "Screenshot capture failed to start.",
        "session_id": session_id
    }
    
    try:
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Set device-specific viewport
        if device == 'mobile':
            chrome_options.add_argument('--window-size=375,667')
            viewport_width = 375
            viewport_height = 667
        elif device == 'tablet':
            chrome_options.add_argument('--window-size=768,1024')
            viewport_width = 768
            viewport_height = 1024
        else:  # desktop
            chrome_options.add_argument('--window-size=1920,1080')
            viewport_width = 1920
            viewport_height = 1080
        
        # Initialize the WebDriver
        driver = webdriver.Chrome(options=chrome_options)
        
        print(f"Navigating to {url}")
        driver.get(url)
        
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Additional wait for dynamic content
        time.sleep(2)
        
        # Get page title
        title = driver.title
        
        # Capture the screenshot
        if full_page:
            # Full page screenshot
            total_width = driver.execute_script("return document.body.offsetWidth")
            total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
            
            # Set window size to full page dimensions
            driver.set_window_size(total_width, total_height)
            
            # Wait for resize to complete
            time.sleep(1)
            
            # Capture screenshot
            screenshot_data = driver.get_screenshot_as_png()
            
            # Open with PIL to potentially resize
            img = Image.open(io.BytesIO(screenshot_data))
            
            # If image is too large, resize it while maintaining aspect ratio
            max_width = 2000
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)
        else:
            # Viewport screenshot
            screenshot_data = driver.get_screenshot_as_png()
            img = Image.open(io.BytesIO(screenshot_data))
        
        # Convert to the desired format
        if format_type.lower() == 'jpg' or format_type.lower() == 'jpeg':
            # Convert to RGB for JPEG
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            
            # Set quality
            if quality == 'high':
                jpeg_quality = 95
            elif quality == 'medium':
                jpeg_quality = 80
            else:  # low
                jpeg_quality = 60
            
            # Save to BytesIO
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=jpeg_quality)
            img_bytes.seek(0)
            
            # Create filename
            filename = f"screenshot_{session_id}.jpg"
        else:  # PNG
            # Save to BytesIO
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Create filename
            filename = f"screenshot_{session_id}.png"
        
        # Save the screenshot to a file
        with open(filename, 'wb') as f:
            f.write(img_bytes.getvalue())
        
        # Create metadata
        metadata = {
            "title": title,
            "url": url,
            "device": device,
            "format": format_type,
            "quality": quality,
            "full_page": full_page,
            "dimensions": f"{img.width}×{img.height}",
            "file_size": f"{len(img_bytes.getvalue()) / (1024 * 1024):.2f} MB",
            "capture_time": f"{time.time() - start_time:.1f}s"
        }
        
        # Save metadata to a JSON file
        with open(f"screenshot_metadata_{session_id}.json", 'w') as f:
            json.dump(metadata, f)
        
        # Clean up
        driver.quit()
        
        results = {
            "status": "success",
            "url": url,
            "session_id": session_id,
            "data": metadata
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
        
        # Clean up driver if it was initialized
        try:
            driver.quit()
        except:
            pass
    
    # Always output the results, even if there was an error
    print(f"results={json.dumps(results)}")
    return results

if __name__ == "__main__":
    # Record start time
    start_time = time.time()
    
    # Get parameters from environment variables
    target_url = os.environ.get("TARGET_URL")
    device = os.environ.get("DEVICE", "desktop")
    format_type = os.environ.get("FORMAT", "png")
    quality = os.environ.get("QUALITY", "high")
    full_page = os.environ.get("FULL_PAGE", "true").lower() == "true"
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    if not target_url:
        print("ERROR: TARGET_URL environment variable not set.")
        print(f"results={json.dumps({'status': 'error', 'message': 'TARGET_URL environment variable not set.'})}")
        sys.exit(1)
        
    screenshot_results = capture_screenshot(
        target_url, 
        device, 
        format_type, 
        quality, 
        full_page, 
        session_id
    )
    
    # The results are already printed in the function
