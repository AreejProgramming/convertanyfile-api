# File: runner/website_source_downloader.py
import os
import json
import time
import sys
import uuid
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import cssutils
import js2py

def generate_session_id():
    return str(uuid.uuid4())

def extract_domain_from_url(url):
    """
    Extract domain from a URL
    """
    parsed_url = urlparse(url)
    return parsed_url.netloc

def is_valid_url(url):
    """
    Check if the URL is valid
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def fetch_website_source(url):
    """
    Fetches the source code (HTML, CSS, JS) of a website
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting website source download for: {url}")
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "Website source download failed to start.",
        "session_id": session_id
    }
    
    try:
        # Validate URL
        if not is_valid_url(url):
            raise ValueError("Invalid URL format")
        
        print(f"Fetching HTML for {url}")
        
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch HTML
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html_content = response.text
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title
        title = soup.title.string if soup.title else extract_domain_from_url(url)
        
        # Extract CSS
        css_content = ""
        css_links = soup.find_all('link', rel='stylesheet')
        
        for link in css_links:
            css_url = link.get('href')
            if css_url:
                # Convert relative URL to absolute
                css_url = urljoin(url, css_url)
                try:
                    print(f"Fetching CSS from {css_url}")
                    css_response = requests.get(css_url, headers=headers, timeout=30)
                    css_response.raise_for_status()
                    css_content += f"/* Source: {css_url} */\n"
                    css_content += css_response.text + "\n\n"
                except Exception as e:
                    print(f"Error fetching CSS from {css_url}: {str(e)}")
        
        # Extract inline CSS
        inline_styles = soup.find_all('style')
        for style in inline_styles:
            css_content += "/* Inline CSS */\n"
            css_content += style.string + "\n\n"
        
        # Extract JavaScript
        js_content = ""
        js_scripts = soup.find_all('script', src=True)
        
        for script in js_scripts:
            js_url = script.get('src')
            if js_url:
                # Convert relative URL to absolute
                js_url = urljoin(url, js_url)
                try:
                    print(f"Fetching JavaScript from {js_url}")
                    js_response = requests.get(js_url, headers=headers, timeout=30)
                    js_response.raise_for_status()
                    js_content += f"// Source: {js_url}\n"
                    js_content += js_response.text + "\n\n"
                except Exception as e:
                    print(f"Error fetching JavaScript from {js_url}: {str(e)}")
        
        # Extract inline JavaScript
        inline_scripts = soup.find_all('script', string=True)
        for script in inline_scripts:
            if script.string:
                js_content += "// Inline JavaScript\n"
                js_content += script.string + "\n\n"
        
        results = {
            "status": "success",
            "url": url,
            "title": title,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "html": html_content,
                "css": css_content,
                "js": js_content
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
        
    source_results = fetch_website_source(target_url)
    
    # The results are already printed in the function
