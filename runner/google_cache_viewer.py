# File: runner/google_cache_viewer.py

import os
import json
import time
import sys
import uuid
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup

def generate_session_id():
    return str(uuid.uuid4())

def normalize_url(url):
    """
    Normalize the URL to ensure it has a protocol
    """
    if not url:
        return None
        
    # Remove whitespace
    url = url.strip()
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return url

def check_google_cache(url):
    """
    Checks if Google has cached a version of the given URL.
    Returns detailed information about the cache status.
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Normalize the URL
    normalized_url = normalize_url(url)
    
    if not normalized_url:
        raise ValueError("Invalid URL format")
    
    print(f"Starting Google cache check for: {normalized_url}")
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "Google cache check failed to start.",
        "session_id": session_id
    }
    
    try:
        # Check if Google has a cached version
        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{normalized_url}"
        
        print(f"Checking Google cache at: {cache_url}")
        
        # Make request to Google cache
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(cache_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Parse the HTML to extract information
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if we got a valid cache page
            if "This is Google's cache of" in response.text:
                # Extract cache date
                cache_date_text = None
                date_element = soup.find(string=re.compile(r"It is a snapshot of the page as it appeared on"))
                if date_element:
                    date_match = re.search(r"(\w+ \d{1,2}, \d{4})", date_element)
                    if date_match:
                        try:
                            cache_date = datetime.strptime(date_match.group(1), "%b %d, %Y")
                            cache_date_text = cache_date.strftime("%Y-%m-%d")
                        except ValueError:
                            pass
                
                # Extract page title
                title_element = soup.find('title')
                page_title = title_element.text if title_element else "Unknown"
                
                # Estimate cache size
                cache_size = f"{len(response.content) // 1024} KB"
                
                results = {
                    "status": "success",
                    "url": normalized_url,
                    "timestamp": time.time(),
                    "session_id": session_id,
                    "data": {
                        "available": True,
                        "cache_url": cache_url,
                        "cache_date": cache_date_text,
                        "page_title": page_title,
                        "cache_size": cache_size,
                        "last_indexed": cache_date_text
                    }
                }
            else:
                # No cache available
                results = {
                    "status": "success",
                    "url": normalized_url,
                    "timestamp": time.time(),
                    "session_id": session_id,
                    "data": {
                        "available": False,
                        "message": "Google has not cached this page yet. This could be because the page is new, has a no-cache directive, or is blocked by robots.txt."
                    }
                }
        else:
            # Error response
            results = {
                "status": "success",
                "url": normalized_url,
                "timestamp": time.time(),
                "session_id": session_id,
                "data": {
                    "available": False,
                    "message": f"Failed to check Google cache: HTTP {response.status_code}"
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
        
    cache_results = check_google_cache(target_url)
    
    # The results are already printed in the function
