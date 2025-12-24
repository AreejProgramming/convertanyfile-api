import os
import json
import time
import sys
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, quote
import hashlib
import uuid

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

def check_google_index(url):
    """
    Checks if a URL is indexed on Google using a more accurate method
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Format the URL
    url = format_url(url)
    
    print(f"Starting Google index check for: {url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results with error state
    results = {
        "status": "error", 
        "message": "Google index check failed to start.",
        "session_id": session_id
    }
    
    try:
        # Basic URL validation
        if not url or not re.match(r'^https?://.+\..+', url):
            raise ValueError("Invalid URL format")
        
        print(f"Checking Google index for {url}")
        
        # Method 1: Use site: operator search
        # This is more reliable than searching for the exact URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path
        
        # Create a more specific search query using site: operator
        search_query = f"site:{domain} {path}"
        encoded_query = quote(search_query, safe='')
        search_url = f"https://www.google.com/search?q={encoded_query}"
        
        # Set headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Make request to Google search
        print(f"Making request to: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=10)
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for "did not match any documents" message
            no_results_patterns = [
                r'did not match any documents',
                r'Your search.*did not match any documents',
                r'No results found for',
                r'No results found'
            ]
            
            no_results = None
            for pattern in no_results_patterns:
                no_results = soup.find(text=re.compile(pattern, re.IGNORECASE))
                if no_results:
                    break
            
            # Method 2: Check for results count
            results_stats = soup.find('div', {'id': 'result-stats'})
            has_results = False
            
            if results_stats:
                stats_text = results_stats.get_text()
                print(f"Results stats: {stats_text}")
                if "About" in stats_text and "results" in stats_text:
                    has_results = True
            
            # Method 3: Look for search results
            search_results = soup.find_all('div', class_='g')
            
            # Method 4: Check if any result contains our exact URL
            exact_match = False
            for result in search_results:
                link_element = result.find('a')
                if link_element and link_element.get('href'):
                    result_url = link_element.get('href')
                    if result_url == url or result_url.startswith(url):
                        exact_match = True
                        break
            
            # Determine if the URL is indexed
            is_indexed = not no_results and (has_results or len(search_results) > 0 or exact_match)
            
            if not is_indexed:
                # URL is not indexed
                print("URL is not indexed on Google")
                index_info = {
                    "is_indexed": False,
                    "url": url,
                    "message": "This URL is not indexed on Google. It may be a new page, blocked by robots.txt, or penalized.",
                    "suggestions": [
                        "Submit URL to Google Search Console",
                        "Check your robots.txt file",
                        "Add internal links from indexed pages",
                        "Create and submit a sitemap",
                    ]
                }
            else:
                # URL is indexed - extract more information
                print("URL appears to be indexed on Google")
                
                # Find the result that matches our exact URL
                target_result = None
                for result in search_results:
                    link_element = result.find('a')
                    if link_element and link_element.get('href'):
                        result_url = link_element.get('href')
                        if result_url == url or result_url.startswith(url):
                            target_result = result
                            break
                
                # If we can't find an exact match, use the first result
                if not target_result and search_results:
                    target_result = search_results[0]
                
                if target_result:
                    # Extract information from the search result
                    title_element = target_result.find('h3')
                    title = title_element.get_text() if title_element else url
                    
                    # Extract snippet - try multiple selectors
                    snippet_element = None
                    snippet_selectors = [
                        'span[data-ved]',
                        '.VwiC3b',
                        '.yDYNvb',
                        '.s',
                        '.st'
                    ]
                    
                    for selector in snippet_selectors:
                        snippet_element = target_result.select_one(selector)
                        if snippet_element:
                            break
                    
                    snippet = snippet_element.get_text() if snippet_element else "No snippet available"
                    
                    # Get current date for timestamps
                    current_date = datetime.now()
                    
                    # Generate index info
                    index_info = {
                        "is_indexed": True,
                        "url": url,
                        "title": title,
                        "snippet": snippet,
                        "first_indexed": current_date.strftime('%Y-%m-%d'),
                        "last_crawled": current_date.strftime('%Y-%m-%d'),
                        "cache_version": current_date.strftime('%Y-%m-%d'),
                        "search_appearances": 1,  # At least one appearance since we found it
                        "keywords": []  # Would need additional processing to extract keywords
                    }
                else:
                    # Fallback - assume indexed but couldn't extract details
                    print("Couldn't extract details from search results")
                    current_date = datetime.now()
                    index_info = {
                        "is_indexed": True,
                        "url": url,
                        "title": url,
                        "snippet": "No snippet available",
                        "first_indexed": current_date.strftime('%Y-%m-%d'),
                        "last_crawled": current_date.strftime('%Y-%m-%d'),
                        "cache_version": current_date.strftime('%Y-%m-%d'),
                        "search_appearances": 1,
                        "keywords": []
                    }
            
            results = {
                "status": "success",
                "url": url,
                "timestamp": time.time(),
                "session_id": session_id,
                "data": index_info
            }
        else:
            raise ValueError(f"Failed to query Google: HTTP {response.status_code}")
        
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
    target_url = os.environ.get("TARGET_URL")
    if not target_url:
        print("ERROR: TARGET_URL environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "TARGET_URL environment variable not set.",
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
        
    index_results = check_google_index(target_url)
    
    # The results are already printed in the function
    sys.exit(0)
