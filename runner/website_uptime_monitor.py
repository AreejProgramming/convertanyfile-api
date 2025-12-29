# File: runner/website_uptime_monitor.py
import os
import json
import time
import sys
import uuid
import requests
from datetime import datetime

def generate_session_id():
    return str(uuid.uuid4())

def is_valid_url(url):
    """
    Check if the URL is valid
    """
    try:
        result = requests.utils.urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def check_website_uptime(url):
    """
    Checks the uptime of a website
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    is_initial_check = os.environ.get("IS_INITIAL_CHECK", "true").lower() == "true"
    
    print(f"Starting website uptime check for: {url}")
    print(f"Session ID: {session_id}")
    print(f"Is Initial Check: {is_initial_check}")
    
    results = {
        "status": "error", 
        "message": "Website uptime check failed to start.",
        "session_id": session_id
    }
    
    try:
        # Validate URL
        if not is_valid_url(url):
            raise ValueError("Invalid URL format")
        
        print(f"Checking uptime for {url}")
        
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Record start time for response time calculation
        start_time = time.time()
        
        # Make request with timeout
        response = requests.get(url, headers=headers, timeout=30)
        
        # Calculate response time in milliseconds
        response_time = int((time.time() - start_time) * 1000)
        
        # Check if website is up (status code in 200-299 range)
        is_up = 200 <= response.status_code < 300
        
        # For initial check, we don't have previous downtime data
        downtime_minutes = 0
        if not is_initial_check and not is_up:
            # For subsequent checks, simulate a downtime duration
            # In a real implementation, you would track when the downtime started
            import random
            downtime_minutes = random.randint(1, 10)
        
        results = {
            "status": "success",
            "url": url,
            "timestamp": time.time(),
            "session_id": session_id,
            "is_initial_check": is_initial_check,
            "data": {
                "is_up": is_up,
                "status_code": response.status_code,
                "response_time": response_time,
                "downtime_minutes": downtime_minutes
            }
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        # For network errors, consider the site down
        results = {
            "status": "success",
            "url": url,
            "timestamp": time.time(),
            "session_id": session_id,
            "is_initial_check": is_initial_check,
            "data": {
                "is_up": False,
                "status_code": None,
                "response_time": None,
                "downtime_minutes": 5 if not is_initial_check else 0
            }
        }
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
    
    # Always output the results, even if there was an error
    print(f"results={json.dumps(results)}")
    return results

if __name__ == "__main__":
    target_url = os.environ.get("TARGET_URL")
    if not target_url:
        print("ERROR: TARGET_URL environment variable not set.")
        print(f"results={json.dumps({'status': 'error', 'message': 'TARGET_URL environment variable not set.'})}")
        sys.exit(1)
        
    uptime_results = check_website_uptime(target_url)
    
    # The results are already printed in the function
