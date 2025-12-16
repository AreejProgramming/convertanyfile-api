# File: runner/google_cache_checker.py

import os
import json
import time
import sys
import uuid
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, quote

def generate_session_id():
    return str(uuid.uuid4())

def format_url(url):
    """
    Ensure URL has proper format
    """
    if not url:
        return None
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return url

def check_google_cache(url):
    """
    Checks if Google has cached the specified URL and retrieves cache information.
    Returns detailed information about the cached version.
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Format the URL
    url = format_url(url)
    
    print(f"Starting Google cache check for: {url}")
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "Google cache check failed to start.",
        "session_id": session_id
    }
    
    try:
        # Basic URL validation
        if not url or not re.match(r'^https?://.+\..+', url):
            raise ValueError("Invalid URL format")
        
        print(f"Checking Google cache for {url}")
        
        # Create the Google cache URL
        encoded_url = quote(url, safe='')
        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{encoded_url}"
        
        # Set headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Make request to Google cache
        response = requests.get(cache_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to retrieve Google cache: HTTP {response.status_code}")
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check if the page exists in Google's cache
        not_found_indicators = [
            soup.find(text=re.compile(r"Google hasn't cached this page")),
            soup.find(text=re.compile(r"Your search did not match any documents")),
            soup.find(text=re.compile(r"404. That's an error")),
            soup.find("title", text=re.compile(r"404|Error|Not Found", re.IGNORECASE)),
        ]
        
        if any(indicator for indicator in not_found_indicators if indicator):
            raise ValueError("Google has not cached this page yet. This could be because the page is new, has a no-cache directive, or is blocked by robots.txt.")
        
        # Extract cache information
        cache_info = {}
        
        # Extract cache date
        cache_date_element = soup.find(text=re.compile(r"as it appeared on ([\w\s,]+)"))
        if cache_date_element:
            date_match = re.search(r"as it appeared on ([\w\s,]+)", str(cache_date_element))
            if date_match:
                try:
                    cache_date_str = date_match.group(1)
                    # Try to parse the date
                    cache_date = datetime.strptime(cache_date_str, "%b %d, %Y")
                    cache_info["cache_date"] = cache_date.strftime("%Y-%m-%d")
                except ValueError:
                    cache_info["cache_date"] = None
        
        # Extract page title
        title_element = soup.find("title")
        if title_element:
            title = title_element.get_text()
            # Remove " - Google Cache" suffix if present
            if " - Google Cache" in title:
                title = title.replace(" - Google Cache", "")
            cache_info["page_title"] = title
        
        # Calculate cache size (approximate based on response content length)
        cache_info["cache_size"] = f"{len(response.content) // 1024} KB"
        
        # Get the cached content
        # Remove Google's header and footer
        main_content = soup
        
        # Try to find the main content area
        content_selectors = [
            "#main", 
            "#content", 
            "main", 
            ".main-content",
            "#center_col",
            ".g",
            "div[style*='padding:8px']"
        ]
        
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                main_content = content
                break
        
        # Extract the HTML content
        if main_content:
            cache_info["cache_content"] = str(main_content)
        else:
            cache_info["cache_content"] = response.text
        
        # Get the direct cache URL
        cache_info["cache_url"] = cache_url
        
        # Get the original URL
        cache_info["original_url"] = url
        
        # Add timestamp
        cache_info["checked_at"] = time.time()
        
        results = {
            "status": "success",
            "url": url,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": cache_info
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
