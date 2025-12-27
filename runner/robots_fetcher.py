import os
import json
import sys
import time  # <-- ADD THIS LINE

import requests
from datetime import datetime
from urllib.parse import urlparse

def generate_session_id():
    return f"{int(time.time())}-{os.urandom(4).hex()}"

def validate_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def fetch_robots_txt(url):
    """
    Fetches the robots.txt file from a given URL.
    """
    try:
        parsed_url = urlparse(url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        
        response = requests.get(robots_url, timeout=10)
        
        if response.status_code == 200:
            return {
                "status": "success",
                "message": "robots.txt fetched successfully.",
                "content": response.text,
                "url": robots_url
            }
        elif response.status_code == 404:
            return {
                "status": "not_found",
                "message": "robots.txt not found (404). The website may not have this file.",
                "content": "",
                "url": robots_url
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to fetch robots.txt. HTTP Status: {response.status_code} {response.reason}",
                "content": "",
                "url": robots_url
            }
            
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message": "Request timed out.",
            "content": "",
            "url": url
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Request failed: {str(e)}",
            "content": "",
            "url": url
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "content": "",
            "url": url
        }

def main():
    target_url = os.environ.get("URL")
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    if not target_url:
        print("ERROR: URL environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "URL environment variable not set.",
            "session_id": session_id
        }
        
        with open('results.json', 'w') as f:
            json.dump(error_result, f)
        
        print(f"results={json.dumps(error_result)}")
        sys.exit(1)
        
    if not validate_url(target_url):
        print(f"ERROR: Invalid URL format: {target_url}")
        error_result = {
            "status": "error", 
            "message": "Invalid URL format.",
            "session_id": session_id
        }
        
        with open('results.json', 'w') as f:
            json.dump(error_result, f)
        
        print(f"results={json.dumps(error_result)}")
        sys.exit(1)
    
    print(f"Starting robots.txt fetch for: {target_url}")
    print(f"Session ID: {session_id}")
    
    results = fetch_robots_txt(target_url)
    results["session_id"] = results.get("session_id", session_id)
    results["timestamp"] = datetime.now().isoformat()
    
    try:
        with open('results.json', 'w') as f:
            json.dump(results, f)
        print("Results successfully written to results.json")
    except Exception as file_error:
        print(f"ERROR writing results file: {str(file_error)}")
        sys.exit(1)
    
    print(f"results={json.dumps(results)}")
    sys.exit(0)

if __name__ == "__main__":
    main()
