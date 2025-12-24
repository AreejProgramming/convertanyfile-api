import os
import json
import time
import sys
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
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

def analyze_status_code(url):
    """
    Analyze HTTP status code for a given URL
    """
    try:
        # Measure response time
        start_time = time.time()
        response = requests.get(url, timeout=10, allow_redirects=True)
        response_time = (time.time() - start_time) * 1000  # milliseconds
        
        # Extract headers
        headers = dict(response.headers)
        
        # Get server information
        server = headers.get("Server", "Unknown")
        
        # Get content type
        content_type = headers.get("Content-Type", "Unknown")
        
        # Get content size
        content_size = headers.get("Content-Length", "Unknown")
        if content_size != "Unknown":
            content_size = f"{int(content_size) / 1024:.2f} KB"
        
        # Get protocol information
        protocol = f"HTTP/{response.raw.version / 10:.1f}"
        
        return {
            "url": url,
            "status_code": response.status_code,
            "status_text": response.reason,
            "response_time": response_time,
            "protocol": protocol,
            "server": server,
            "content_type": content_type,
            "content_size": content_size,
            "headers": headers,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error analyzing status code: {str(e)}")
        return {
            "url": url,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def get_status_code_info(status_code):
    """
    Get information about a status code
    """
    status_codes = {
        100: {"name": "Continue", "description": "The server has received the request headers and the client should proceed to send the request body."},
        101: {"name": "Switching Protocols", "description": "The requester has asked the server to switch protocols and the server has agreed to do so."},
        200: {"name": "OK", "description": "The request has succeeded."},
        201: {"name": "Created", "description": "The request has been fulfilled and has resulted in one or more new resources being created."},
        202: {"name": "Accepted", "description": "The request has been accepted for processing, but the processing has not been completed."},
        204: {"name": "No Content", "description": "The server successfully processed the request, but is not returning any content."},
        301: {"name": "Moved Permanently", "description": "The URL of the requested resource has been changed permanently."},
        302: {"name": "Found", "description": "The URL of the requested resource has been changed temporarily."},
        304: {"name": "Not Modified", "description": "A conditional GET request has been received and would result in a 200 OK if it were fresh."},
        307: {"name": "Temporary Redirect", "description": "The server is currently responding to the request with a different URI."},
        308: {"name": "Permanent Redirect", "description": "The server is currently responding to the request with a different URI, and the user agent MAY use that URI in the future."},
        400: {"name": "Bad Request", "description": "The server cannot or will not process the request due to an apparent client error."},
        401: {"name": "Unauthorized", "description": "The request requires user authentication."},
        403: {"name": "Forbidden", "description": "The server understood the request, but is refusing to fulfill it."},
        404: {"name": "Not Found", "description": "The requested resource could not be found but may be available in the future."},
        405: {"name": "Method Not Allowed", "description": "A request method is not supported for the requested resource."},
        408: {"name": "Request Timeout", "description": "The server timed out waiting for the request."},
        429: {"name": "Too Many Requests", "description": "The user has sent too many requests in a given amount of time."},
        500: {"name": "Internal Server Error", "description": "A generic error message, given when an unexpected condition was encountered."},
        502: {"name": "Bad Gateway", "description": "The server was acting as a gateway or proxy and received an invalid response."},
        503: {"name": "Service Unavailable", "description": "The server is currently unavailable (because it is overloaded or down for maintenance)."},
        504: {"name": "Gateway Timeout", "description": "The server was acting as a gateway or proxy and did not receive a timely response."}
    }
    
    return status_codes.get(status_code, {"name": "Unknown", "description": "Status code not recognized."})

def check_http_status_code(url):
    """
    Check HTTP status code for a website
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Format the URL
    url = format_url(url)
    
    print(f"Starting HTTP status code check for: {url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Analyzing HTTP status code...",
        "session_id": session_id
    }
    
    try:
        # Basic URL validation
        if not url or not re.match(r'^https?://.+\..+', url):
            raise ValueError("Invalid URL format")
        
        print(f"Checking HTTP status code for {url}")
        
        # Analyze status code
        status_data = analyze_status_code(url)
        
        if "error" in status_data:
            raise ValueError(status_data["error"])
        
        # Get status code information
        status_info = get_status_code_info(status_data["status_code"])
        
        # Create final results
        results = {
            "status": "success",
            "url": url,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "status_code": status_data["status_code"],
                "status_text": status_data["status_text"],
                "status_info": status_info,
                "response_time": status_data["response_time"],
                "protocol": status_data["protocol"],
                "server": status_data["server"],
                "content_type": status_data["content_type"],
                "content_size": status_data["content_size"],
                "headers": status_data["headers"]
            }
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
        
    status_results = check_http_status_code(target_url)
    
    # The results are already printed in the function
    sys.exit(0)
