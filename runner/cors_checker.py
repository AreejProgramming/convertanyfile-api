# File: runner/cors_checker.py

import os
import json
import time
import sys
import uuid
import requests
from urllib.parse import urlparse

def generate_session_id():
    return str(uuid.uuid4())

def check_cors_policy(url):
    """
    Checks the CORS policy of a URL by making HTTP requests.
    Returns detailed information about the CORS headers and response.
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting CORS check for URL: {url}")
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "CORS check failed to start.",
        "session_id": session_id
    }
    
    try:
        # Parse the URL to validate it
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL format")
        
        # Make a simple GET request to check CORS
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://convertanyfiles.online/',
            'Origin': 'https://convertanyfiles.online'
        }
        
        print(f"Making request to: {url}")
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        # Extract CORS-related headers
        cors_headers = {}
        for header, value in response.headers.items():
            if header.lower().startswith('access-control-'):
                cors_headers[header] = value
        
        # Check if the response allows our origin
        allowed_origin = cors_headers.get('Access-Control-Allow-Origin', '')
        allows_credentials = cors_headers.get('Access-Control-Allow-Credentials', 'false').lower() == 'true'
        
        # Determine if CORS check passed
        cors_passed = False
        if allowed_origin == '*' or allowed_origin == 'https://convertanyfiles.online':
            cors_passed = True
        
        results = {
            "status": "success",
            "url": url,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "cors_passed": cors_passed,
                "response_status": response.status_code,
                "response_status_text": response.reason,
                "cors_headers": cors_headers,
                "allowed_origin": allowed_origin,
                "allows_credentials": allows_credentials,
                "message": "CORS Check Passed: The server allows cross-origin requests from this origin." if cors_passed else "CORS Check Failed: The server does not allow cross-origin requests from this origin."
            }
        }
        
    except requests.exceptions.Timeout:
        results = {
            "status": "error", 
            "message": "Request timed out. The server took too long to respond.",
            "session_id": session_id
        }
    except requests.exceptions.ConnectionError:
        results = {
            "status": "error", 
            "message": "Connection error. Could not connect to the server.",
            "session_id": session_id
        }
    except ValueError as e:
        results = {
            "status": "error", 
            "message": f"Invalid URL: {str(e)}",
            "session_id": session_id
        }
    except Exception as e:
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
        
    cors_results = check_cors_policy(target_url)
    
    # Print the results in a format that can be easily extracted
    print(f"results={json.dumps(cors_results)}")
