import os
import json
import time
import sys
import uuid
import base64
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def generate_session_id():
    """Generate a unique session ID"""
    return str(uuid.uuid4())

def extract_domain(url):
    """Extract domain from URL"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        parsed = urlparse(url)
        return parsed.hostname.lower()
    except:
        return url.lower()

def validate_url(url):
    """Validate URL format"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def get_device_viewport(device):
    """Get viewport dimensions for device type"""
    viewports = {
        'desktop': {'width': 1920, 'height': 1080, 'deviceScaleFactor': 1, 'isMobile': False, 'hasTouch': False},
        'tablet': {'width': 768, 'height': 1024, 'deviceScaleFactor': 2, 'isMobile': True, 'hasTouch': True},
        'mobile': {'width': 375, 'height': 667, 'deviceScaleFactor': 3, 'isMobile': True, 'hasTouch': True}
    }
    return viewports.get(device, viewports['desktop'])

def get_cache_key(url, device, format, full_page):
    """Generate a cache key for the screenshot request"""
    key_data = f"{url}-{device}-{format}-{full_page}"
    return hashlib.md5(key_data.encode()).hexdigest()

def check_cache(cache_key):
    """Check if screenshot exists in cache"""
    cache_dir = "/tmp/screenshot_cache"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
    
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache is still valid (24 hours)
            cache_time = datetime.fromisoformat(cache_data.get('timestamp', '1970-01-01'))
            if datetime.now() - cache_time < timedelta(hours=24):
                return cache_data
            else:
                # Cache expired, remove it
                os.remove(cache_file)
                image_file = os.path.join(cache_dir, f"{cache_key}.{cache_data.get('format', 'png')}")
                if os.path.exists(image_file):
                    os.remove(image_file)
        except Exception as e:
            print(f"Error checking cache: {str(e)}")
    
    return None

def save_to_cache(cache_key, screenshot_data, image_data):
    """Save screenshot to cache"""
    cache_dir = "/tmp/screenshot_cache"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
    
    try:
        # Save metadata
        cache_file = os.path.join(cache_dir, f"{cache_key}.json")
        with open(cache_file, 'w') as f:
            json.dump(screenshot_data, f)
        
        # Save image
        format_ext = screenshot_data.get('format', 'png')
        image_file = os.path.join(cache_dir, f"{cache_key}.{format_ext}")
        with open(image_file, 'wb') as f:
            f.write(image_data)
        
        return True
    except Exception as e:
        print(f"Error saving to cache: {str(e)}")
        return False

def capture_screenshot_with_selenium(url, device, format, full_page, quality):
    """Capture screenshot using Selenium and Chrome"""
    try:
        # Get viewport settings
        viewport = get_device_viewport(device)
        
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument(f'--window-size={viewport["width"]},{viewport["height"]}')
        
        # Set user agent
        user_agents = {
            'desktop': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'tablet': 'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
            'mobile': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1'
        }
        chrome_options.add_argument(f'--user-agent={user_agents.get(device, user_agents["desktop"])}')
        
        # Initialize driver
        driver = webdriver.Chrome(options=chrome_options)
        
        # Set viewport
        driver.set_window_size(viewport['width'], viewport['height'])
        
        # Navigate to URL
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Get page title
        title = driver.title
        
        # Get page dimensions
        dimensions = driver.execute_script('''
            return {
                width: document.body.scrollWidth,
                height: document.body.scrollHeight,
                viewportWidth: window.innerWidth,
                viewportHeight: window.innerHeight
            }
        ''')
        
        # Take screenshot
        if full_page:
            # Full page screenshot
            total_width = driver.execute_script("return document.body.offsetWidth")
            total_height = driver.execute_script("return document.body.scrollHeight")
            
            driver.set_window_size(total_width, total_height)
            time.sleep(1)  # Wait for resize
            
            screenshot = driver.get_screenshot_as_png()
        else:
            # Viewport screenshot
            screenshot = driver.get_screenshot_as_png()
        
        # Close driver
        driver.quit()
        
        return {
            'screenshot': screenshot,
            'title': title,
            'dimensions': dimensions,
            'device': device,
            'format': format,
            'fullPage': full_page,
            'quality': quality
        }
        
    except Exception as e:
        print(f"Error capturing screenshot: {str(e)}")
        if 'driver' in locals():
            try:
                driver.quit()
            except:
                pass
        raise e

def process_screenshot_request(url, device, format, full_page, quality):
    """Process a screenshot request"""
    session_id = generate_session_id()
    domain = extract_domain(url)
    
    # Validate URL
    if not validate_url(url):
        return {
            "status": "error",
            "message": "Invalid URL format",
            "session_id": session_id
        }
    
    # Check cache first
    cache_key = get_cache_key(url, device, format, full_page)
    cached_result = check_cache(cache_key)
    
    if cached_result:
        return {
            "status": "success",
            "session_id": session_id,
            "cached": True,
            "data": cached_result
        }
    
    # Capture new screenshot
    try:
        result = capture_screenshot_with_selenium(url, device, format, full_page, quality)
        
        # Prepare response data
        response_data = {
            "url": url,
            "domain": domain,
            "title": result['title'],
            "device": device,
            "format": format,
            "fullPage": full_page,
            "quality": quality,
            "dimensions": {
                "width": result['dimensions']['width'],
                "height": result['dimensions']['height'],
                "viewportWidth": result['dimensions']['viewportWidth'],
                "viewportHeight": result['dimensions']['viewportHeight']
            },
            "fileSize": f"{len(result['screenshot']) / (1024 * 1024):.2f} MB",
            "captureTime": f"{time.time():.2f}s",
            "timestamp": datetime.now().isoformat()
        }
        
        # Save to cache
        save_to_cache(cache_key, response_data, result['screenshot'])
        
        # Encode screenshot for JSON response
        screenshot_base64 = base64.b64encode(result['screenshot']).decode('utf-8')
        response_data['screenshot'] = f"data:image/{format};base64,{screenshot_base64}"
        
        return {
            "status": "success",
            "session_id": session_id,
            "cached": False,
            "data": response_data
        }
        
    except Exception as e:
        print(f"Error processing screenshot request: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "session_id": session_id
        }

def main():
    """Main function"""
    url = os.environ.get("URL")
    device = os.environ.get("DEVICE", "desktop")
    format = os.environ.get("FORMAT", "png")
    full_page = os.environ.get("FULL_PAGE", "true").lower() == "true"
    quality = os.environ.get("QUALITY", "high")
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    if not url:
        error_result = {
            "status": "error",
            "message": "URL environment variable not set",
            "session_id": session_id
        }
        
        with open('results.json', 'w') as f:
            json.dump(error_result, f)
        print(json.dumps(error_result))
        sys.exit(1)
    
    try:
        # Process screenshot request
        result = process_screenshot_request(url, device, format, full_page, quality)
        
        # Write results to file
        with open('results.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(json.dumps(result))
        
        # Exit with appropriate code
        if result["status"] == "error":
            sys.exit(1)
            
    except Exception as e:
        error_result = {
            "status": "error",
            "message": str(e),
            "session_id": session_id
        }
        
        with open('results.json', 'w') as f:
            json.dump(error_result, f)
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()
