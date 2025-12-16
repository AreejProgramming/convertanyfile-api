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

def check_cors(url):
    """
    Checks the CORS configuration of a server by making HTTP requests.
    Includes robust error handling and logging.
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting CORS check for URL: {url}") # Log for debugging
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "Analysis failed to start.",
        "session_id": session_id
    }
    
    try:
        # Parse the URL to get the domain
        parsed_url = urlparse(url)
        
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL format")
        
        print(f"Analyzing URL: {url}")
        
        # Make a simple GET request to test CORS
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Referer': 'https://convertanyfiles.online/cors-checker',
            'Origin': 'https://convertanyfiles.online'
        }
        
        # First, try a simple GET request
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        # Extract CORS-related headers
        cors_headers = {}
        for key, value in response.headers.items():
            if key.lower().startswith('access-control-'):
                cors_headers[key] = value
        
        # Check if the request was successful
        if response.status_code < 400:
            results = {
                "status": "success",
                "url": url,
                "timestamp": time.time(),
                "session_id": session_id,
                "data": {
                    "passes": True,
                    "message": "CORS Check Passed: The server allows cross-origin requests from this origin.",
                    "response_status": response.status_code,
                    "response_status_text": response.reason,
                    "cors_headers": cors_headers
                }
            }
        else:
            results = {
                "status": "success",
                "url": url,
                "timestamp": time.time.time(),
                "session_id": session_id,
                "data": {
                    "passes": False,
                    "message": f"CORS Check Failed: Server returned {response.status_code} {response.reason}",
                    "response_status": response.status_code,
                    "response_status_text": response.reason,
                    "cors_headers": cors_headers
                }
            }

    except requests.exceptions.Timeout:
        print(f"ERROR: A timeout occurred. The request took too long to complete.")
        results = {
            "status": "error", 
            "message": "Timeout: The request took too long to complete.",
            "session_id": session_id
        }
    except requests.exceptions.ConnectionError:
        print(f"ERROR: A connection error occurred.")
        results = {
            "status": "error", 
            "message": "Connection error: Could not connect to the server.",
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
        
    analysis_results = check_cors(target_url)
    
    # Print the results in a format that can be easily extracted
    print(f"results={json.dumps(analysis_results)}")
