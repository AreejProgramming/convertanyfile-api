import os
import json
import time
import sys
import re
import requests
import uuid
from datetime import datetime
from urllib.parse import urlparse

def generate_session_id():
    return str(uuid.uuid4())

def validate_url(url):
    """
    Validate if input is a valid URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def normalize_url(url):
    """
    Normalize URL format
    """
    if not url:
        return None
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Remove trailing slash
    if url.endswith('/'):
        url = url[:-1]
    
    return url

def check_website_status(url):
    """
    Check if a website is up or down
    """
    try:
        # Measure response time
        start_time = time.time()
        
        # Make request with timeout
        response = requests.get(url, timeout=10, allow_redirects=True)
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Get server info if available
        server = response.headers.get('Server', 'Unknown')
        
        # Get IP address
        ip_address = None
        try:
            import socket
            ip_address = socket.gethostbyname(urlparse(url).netloc)
        except:
            ip_address = None
        
        # Get location info (simplified)
        location = None
        try:
            # In a real implementation, you might use a geolocation API
            # For now, we'll use a simple lookup
            location = "Unknown"
        except:
            location = None
        
        # Determine if site is up
        is_up = response.status_code < 400
        
        return {
            "url": url,
            "is_up": is_up,
            "status_code": response.status_code,
            "status_text": get_status_text(response.status_code),
            "response_time": round(response_time, 2),
            "server": server,
            "ip_address": ip_address,
            "location": location,
            "timestamp": datetime.now().isoformat()
        }
        
    except requests.exceptions.RequestException as e:
        # Handle different types of request exceptions
        status_code = 404
        if "timeout" in str(e).lower():
            status_code = 408  # Request Timeout
        elif "connection" in str(e).lower():
            status_code = 503  # Service Unavailable
        else:
            status_code = 500  # Internal Server Error
            
        return {
            "url": url,
            "is_up": False,
            "status_code": status_code,
            "status_text": get_status_text(status_code),
            "response_time": None,
            "server": None,
            "ip_address": None,
            "location": None,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
    except Exception as e:
        return {
            "url": url,
            "is_up": False,
            "status_code": 500,
            "status_text": get_status_text(500),
            "response_time": None,
            "server": None,
            "ip_address": None,
            "location": None,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

def get_status_text(status_code):
    """
    Get human-readable status text
    """
    status_texts = {
        200: "OK",
        301: "Moved Permanently",
        302: "Found",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        408: "Request Timeout",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable"
    }
    return status_texts.get(status_code, "Unknown")

def check_website_down(url):
    """
    Main function to check if a website is down
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting website down check for: {url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Checking website status...",
        "session_id": session_id
    }
    
    try:
        # Validate and normalize URL
        normalized_url = normalize_url(url)
        
        if not normalized_url or not validate_url(normalized_url):
            raise ValueError("Invalid URL format")
        
        # Check website status
        print(f"Checking status of {normalized_url}")
        status_data = check_website_status(normalized_url)
        
        # Create final results
        results = {
            "status": "success",
            "url": normalized_url,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": status_data
        }
        
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
    url = os.environ.get("URL")
    if not url:
        print("ERROR: URL environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "URL environment variable not set.",
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
        
    website_results = check_website_down(url)
    
    # The results are already printed in the function
    sys.exit(0)
