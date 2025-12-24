# runner/check_http_status.py
import os
import json
import time
import sys
import uuid
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
import socket

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

def check_http_status(url):
    """
    Fetches and analyzes HTTP status code for the specified URL.
    Returns detailed information about the status code, response time, and server info.
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Format the URL
    url = format_url(url)
    
    print(f"Starting HTTP status check for: {url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results with error state
    results = {
        "status": "error", 
        "message": "HTTP status check failed to start.",
        "session_id": session_id
    }
    
    try:
        # Basic URL validation
        if not url or not re.match(r'^https?://.+\..+', url):
            raise ValueError("Invalid URL format")
        
        print(f"Checking HTTP status for {url}")
        
        # Parse the URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Start timing
        start_time = time.time()
        
        # Create a session for connection reuse
        session = requests.Session()
        
        # Set headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Make the request
        response = session.get(
            url, 
            headers=headers, 
            timeout=15, 
            allow_redirects=True,
            stream=True  # Don't download the entire content
        )
        
        # Calculate response time
        response_time = int((time.time() - start_time) * 1000)
        
        # Get content length from headers
        content_length = response.headers.get('Content-Length')
        if content_length:
            content_size = f"{int(content_length) / 1024:.2f} KB"
        else:
            # If content-length is not available, estimate from partial content
            try:
                # Read a small portion to estimate size
                content_sample = b''.join(response.iter_content(chunk_size=1024, amount=1024))
                # This is just a rough estimate
                content_size = f"{len(content_sample) / 1024:.2f} KB"
            except:
                content_size = "Unknown"
        
        # Get server information
        server = response.headers.get('Server', 'Unknown')
        
        # Get content type
        content_type = response.headers.get('Content-Type', 'Unknown')
        
        # Get status code information
        status_code = response.status_code
        status_info = get_status_info(status_code)
        
        # Create comprehensive result
        status_data = {
            "url": url,
            "final_url": response.url,
            "status_code": status_code,
            "status_info": status_info,
            "response_time": f"{response_time}ms",
            "server": server,
            "content_type": content_type,
            "content_size": content_size,
            "headers": dict(response.headers),
            "redirects": get_redirect_chain(response),
            "checked_at": time.time()
        }
        
        results = {
            "status": "success",
            "url": url,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": status_data
        }
        
        # Write results to file
        with open('results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"results={json.dumps(results)}")
        return results
        
    except requests.exceptions.Timeout:
        error_msg = "Request timed out. The server may be slow or unresponsive."
        print(f"ERROR: {error_msg}")
        results = {
            "status": "error", 
            "message": error_msg,
            "session_id": session_id
        }
        
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection error: Could not connect to the server. {str(e)}"
        print(f"ERROR: {error_msg}")
        results = {
            "status": "error", 
            "message": error_msg,
            "session_id": session_id
        }
        
    except requests.exceptions.TooManyRedirects:
        error_msg = "Too many redirects. The URL may be in a redirect loop."
        print(f"ERROR: {error_msg}")
        results = {
            "status": "error", 
            "message": error_msg,
            "session_id": session_id
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
        
        # Write error results to file
        with open('results.json', 'w') as f:
            json.dump(results, f)
    
    # Always output the results, even if there was an error
    print(f"results={json.dumps(results)}")
    return results

def get_status_info(status_code):
    """
    Get information about a status code
    """
    status_codes = {
        100: { name: 'Continue', description: 'The server has received the request headers and the client should proceed to send the request body.' },
        101: { name: 'Switching Protocols', description: 'The requester has asked the server to switch protocols.' },
        200: { name: 'OK', description: 'The request has succeeded.' },
        201: { name: 'Created', description: 'The request has been fulfilled and has resulted in one or more new resources being created.' },
        202: { name: 'Accepted', description: 'The request has been accepted for processing, but the processing has not been completed.' },
        204: { name: 'No Content', description: 'The server successfully processed the request, but is not returning any content.' },
        301: { name: 'Moved Permanently', description: 'The URL of the requested resource has been changed permanently.' },
        302: { name: 'Found', description: 'The URL of the requested resource has been changed temporarily.' },
        304: { name: 'Not Modified', description: 'A conditional GET request has been received and would result in a 200 OK if it were fresh.' },
        307: { name: 'Temporary Redirect', description: 'The URL of the requested resource has been changed temporarily.' },
        308: { name: 'Permanent Redirect', description: 'The URL of the requested resource has been changed permanently.' },
        400: { name: 'Bad Request', description: 'The server cannot or will not process the request due to an apparent client error.' },
        401: { name: 'Unauthorized', description: 'The request requires user authentication.' },
        403: { name: 'Forbidden', description: 'The server understood the request, but is refusing to fulfill it.' },
        404: { name: 'Not Found', description: 'The requested resource could not be found but may be available in the future.' },
        405: { name: 'Method Not Allowed', description: 'A request method is not supported for the requested resource.' },
        408: { name: 'Request Timeout', description: 'The server timed out waiting for the request.' },
        429: { name: 'Too Many Requests', description: 'The user has sent too many requests in a given amount of time.' },
        500: { name: 'Internal Server Error', description: 'A generic error message, given when an unexpected condition was encountered.' },
        502: { name: 'Bad Gateway', description: 'The server was acting as a gateway or proxy and received an invalid response.' },
        503: { name: 'Service Unavailable', description: 'The server is currently unavailable (because it is overloaded or down for maintenance).' },
        504: { name: 'Gateway Timeout', description: 'The server was acting as a gateway or proxy and did not receive a timely response.' }
    }
    
    return status_codes.get(status_code, { 
        name: 'Unknown', 
        description: 'Status code not recognized.' 
    })

def get_redirect_chain(response):
    """
    Get the redirect chain if any
    """
    if hasattr(response, 'history') and response.history:
        redirects = []
        for resp in response.history:
            redirects.append({
                "status_code": resp.status_code,
                "url": resp.url,
                "location": resp.headers.get('Location')
            })
        redirects.append({
            "status_code": response.status_code,
            "url": response.url,
            "location": None
        })
        return redirects
    return []

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
        with open('results.json', 'w') as f:
            json.dump(error_result, f)
        
        print(f"results={json.dumps(error_result)}")
        sys.exit(0)  # Exit with 0 to prevent workflow failure
        
    status_results = check_http_status(target_url)
    
    # The results are already printed in the function
    sys.exit(0)  # Exit with 0 to prevent workflow failure
