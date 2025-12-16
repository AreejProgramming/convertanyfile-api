# File: runner/broken_link_checker.py

import os
import json
import time
import sys
import uuid
import requests
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Add this function to generate a unique session ID
def generate_session_id():
    return str(uuid.uuid4())

def check_link_status(url, timeout=10):
    """
    Check the status of a single URL.
    Returns a tuple of (status_code, status_text, error_message)
    """
    try:
        # Use HEAD request first as it's lighter
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        
        # If HEAD fails, try GET
        if response.status_code >= 400:
            response = requests.get(url, timeout=timeout, allow_redirects=True)
            
        return response.status_code, response.reason, None
    except requests.exceptions.Timeout:
        return None, None, "Request timed out"
    except requests.exceptions.ConnectionError:
        return None, None, "Connection error"
    except requests.exceptions.TooManyRedirects:
        return None, None, "Too many redirects"
    except requests.exceptions.RequestException as e:
        return None, None, str(e)

def is_internal_link(base_url, link_url):
    """
    Check if a link is internal to the base domain
    """
    base_domain = urlparse(base_url).netloc
    link_domain = urlparse(link_url).netloc
    return base_domain == link_domain

def run_broken_link_check(url):
    """
    Launches a browser, extracts all links, and checks their status.
    Includes robust error handling and logging.
    """
    # Generate a unique session ID for this analysis
    session_id = generate_session_id()
    
    print(f"Starting broken link check for URL: {url}") # Log for debugging
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "Analysis failed to start.",
        "session_id": session_id
    }
    
    try:
        # Use sync_playwright as a context manager
        with sync_playwright() as p:
            print("Launching browser...")
            # Launch the browser using the playwright instance 'p'
            browser = p.chromium.launch(headless=True) # Explicitly launch chromium
            
            print("Navigating to page...")
            page = browser.new_page()
            
            # Go to the page and wait for it to be reasonably loaded
            # Use a longer timeout for slow websites
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            print("Extracting links...")
            # Get all links on the page
            links = page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.map(link => {
                        return {
                            href: link.href,
                            text: link.textContent.trim().substring(0, 100)
                        };
                    });
                }
            """)
            
            # Deduplicate links
            unique_links = {}
            for link in links:
                href = link['href']
                if href not in unique_links:
                    unique_links[href] = link
            
            # Convert back to array
            deduplicated_links = list(unique_links.values())
            
            print(f"Found {len(deduplicated_links)} unique links. Checking status...")
            
            # Check each link
            checked_links = []
            broken_count = 0
            valid_count = 0
            
            for i, link in enumerate(deduplicated_links):
                href = link['href']
                text = link['text']
                
                # Skip empty links, anchors, and javascript
                if not href or href.startswith('#') or href.startswith('javascript:'):
                    continue
                    
                # Convert relative URLs to absolute
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(url, href)
                
                print(f"Checking link {i+1}/{len(deduplicated_links)}: {href}")
                
                # Check link status
                status_code, status_text, error = check_link_status(href)
                
                # Determine if link is broken
                is_broken = status_code is None or status_code >= 400
                
                if is_broken:
                    broken_count += 1
                else:
                    valid_count += 1
                
                # Add to results
                checked_links.append({
                    "url": href,
                    "text": text,
                    "status_code": status_code,
                    "status_text": status_text,
                    "error": error,
                    "is_broken": is_broken,
                    "is_internal": is_internal_link(url, href)
                })
            
            print("Analysis complete. Closing browser.")
            # The 'with' statement will handle closing the browser automatically
            
            # Calculate a simple score based on percentage of broken links
            total_links = len(checked_links)
            broken_percentage = (broken_count / total_links * 100) if total_links > 0 else 0
            score = max(0, 100 - broken_percentage)
            
            results = {
                "status": "success",
                "url": url,
                "timestamp": time.time(),
                "session_id": session_id,
                "data": {
                    "total_links": total_links,
                    "broken_links": broken_count,
                    "valid_links": valid_count,
                    "score": round(score, 1),
                    "links": checked_links
                }
            }

    except PlaywrightTimeoutError as e:
        print(f"ERROR: A timeout occurred. The page took too long to load. Details: {e}")
        results = {
            "status": "error", 
            "message": f"Timeout: The page took too long to load.",
            "session_id": session_id
        }
    except Exception as e:
        # Catch any other exception
        print(f"ERROR: An unexpected error occurred. Details: {e}")
        results = {
            "status": "error", 
            "message": f"An unexpected error occurred: {str(e)}",
            "session_id": session_id
        }
            
    return results

if __name__ == "__main__":
    target_url = os.environ.get("TARGET_URL")
    if not target_url:
        print("ERROR: TARGET_URL environment variable not set.")
        sys.exit(1)
        
    analysis_results = run_broken_link_check(target_url)
    
    # Print the results in a format that can be easily extracted
    print(f"results={json.dumps(analysis_results)}")
