import os
import json
import time
import sys
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

def check_redirect_chain(url, max_redirects=10):
    """
    Follows a redirect chain and returns the details of each step.
    """
    session = requests.Session()
    session.max_redirects = max_redirects
    
    chain = []
    visited_urls = set()
    
    try:
        # Prepare the request to not follow redirects automatically
        response = session.get(url, allow_redirects=False, timeout=10)
        
        # Add the initial URL to the chain
        chain.append({
            "url": url,
            "statusCode": response.status_code,
            "statusText": response.reason,
            "location": response.headers.get('Location'),
            "responseTime": 0  # Initial request time is negligible for the first step
        })
        
        current_url = url
        redirect_count = 0
        
        # Follow redirects manually
        while (response.is_redirect or response.status_code in (301, 302, 303, 307, 308)) and redirect_count < max_redirects:
            redirect_count += 1
            location = response.headers.get('Location')
            
            if not location:
                break
                
            # Handle relative URLs
            if location.startswith('/'):
                parsed_url = urlparse(current_url)
                location = f"{parsed_url.scheme}://{parsed_url.netloc}{location}"
            
            # Check for redirect loops
            if location in visited_urls:
                return {
                    "status": "error",
                    "message": "Redirect loop detected",
                    "chain": chain
                }
                
            visited_urls.add(location)
            
            # Measure time for the next request
            start_time = time.time()
            response = session.get(location, allow_redirects=False, timeout=10)
            end_time = time.time()
            
            chain.append({
                "url": location,
                "statusCode": response.status_code,
                "statusText": response.reason,
                "location": response.headers.get('Location'),
                "responseTime": int((end_time - start_time) * 1000)  # in milliseconds
            })
            
            current_url = location
            
        return {
            "status": "success",
            "message": f"Redirect chain analyzed with {redirect_count} redirects.",
            "chain": chain
        }
        
    except requests.exceptions.TooManyRedirects:
        return {
            "status": "error",
            "message": f"Too many redirects (more than {max_redirects})",
            "chain": chain
        }
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message": "Request timed out",
            "chain": chain
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Request failed: {str(e)}",
            "chain": chain
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "chain": chain
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
    
    print(f"Starting redirect check for: {target_url}")
    print(f"Session ID: {session_id}")
    
    results = check_redirect_chain(target_url)
    results["session_id"] = session_id
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
