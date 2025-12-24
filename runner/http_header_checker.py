import os
import json
import time
import sys
import requests
import socket
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

def get_http_headers(url):
    """
    Get HTTP headers from a URL
    """
    try:
        # Measure response time
        start_time = time.time()
        
        # Make HTTP request with timeout
        response = requests.get(
            url, 
            timeout=30,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            allow_redirects=True
        )
        
        response_time = (time.time() - start_time) * 1000  # milliseconds
        
        # Extract headers as dictionary
        headers = dict(response.headers)
        
        return {
            "status": response.status_code,
            "statusText": response.reason,
            "headers": headers,
            "responseTime": round(response_time, 2),
            "url": response.url,
            "finalUrl": response.url,
            "redirects": len(response.history)
        }
        
    except requests.exceptions.Timeout:
        raise Exception("Request timed out after 30 seconds")
    except requests.exceptions.ConnectionError:
        raise Exception("Could not connect to the server")
    except requests.exceptions.RequestException as e:
        raise Exception(f"HTTP request failed: {str(e)}")
    except Exception as e:
        raise Exception(f"Error fetching headers: {str(e)}")

def analyze_security_headers(headers):
    """
    Analyze security-related headers
    """
    security_analysis = {
        "has_security_headers": False,
        "missing_headers": [],
        "security_score": 0
    }
    
    # Important security headers to check
    security_headers = [
        "Content-Security-Policy",
        "X-Frame-Options", 
        "X-Content-Type-Options",
        "Strict-Transport-Security",
        "X-XSS-Protection",
        "Referrer-Policy"
    ]
    
    found_headers = [header for header in security_headers if header in headers]
    missing_headers = [header for header in security_headers if header not in headers]
    
    security_analysis["has_security_headers"] = len(found_headers) > 0
    security_analysis["missing_headers"] = missing_headers
    security_analysis["security_score"] = int((len(found_headers) / len(security_headers)) * 100)
    
    return security_analysis

def detect_server_info(headers):
    """
    Extract server information from headers
    """
    server_info = {
        "server": headers.get("Server", "Unknown"),
        "powered_by": headers.get("X-Powered-By", "Unknown"),
        "content_type": headers.get("Content-Type", "Unknown"),
        "content_encoding": headers.get("Content-Encoding", "None")
    }
    
    return server_info

def check_headers(url):
    """
    Main function to check HTTP headers
    """
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    try:
        # Format URL
        formatted_url = format_url(url)
        if not formatted_url:
            raise ValueError("Invalid URL provided")
        
        print(f"Checking HTTP headers for: {formatted_url}")
        print(f"Session ID: {session_id}")
        
        # Get HTTP headers
        header_data = get_http_headers(formatted_url)
        
        # Analyze security
        security_info = analyze_security_headers(header_data["headers"])
        
        # Extract server info
        server_info = detect_server_info(header_data["headers"])
        
        # Create comprehensive results
        results = {
            "status": "success",
            "url": header_data["url"],
            "finalUrl": header_data["finalUrl"],
            "status": header_data["status"],
            "statusText": header_data["statusText"],
            "responseTime": header_data["responseTime"],
            "headers": header_data["headers"],
            "security": security_info,
            "serverInfo": server_info,
            "redirects": header_data["redirects"],
            "timestamp": time.time(),
            "session_id": session_id
        }
        
        return results
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "session_id": session_id
        }

if __name__ == "__main__":
    target_url = os.environ.get("TARGET_URL")
    if not target_url:
        print("ERROR: TARGET_URL environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "TARGET_URL environment variable not set.",
            "session_id": os.environ.get("SESSION_ID", "unknown")
        }
        print(f"results={json.dumps(error_result)}")
        sys.exit(1)
        
    header_results = check_headers(target_url)
    
    # Write results to file
    try:
        with open('results.json', 'w') as f:
            json.dump(header_results, f)
        print("Results successfully written to results.json")
    except Exception as file_error:
        print(f"ERROR writing results file: {str(file_error)}")
        try:
            with open(f'/tmp/results_{header_results.get("session_id", "unknown")}.json', 'w') as f:
                json.dump(header_results, f)
            print("Results written to fallback location")
        except Exception as fallback_error:
            print(f"ERROR writing to fallback location: {str(fallback_error)}")
    
    # Output results
    print(f"results={json.dumps(header_results)}")
    sys.exit(0)
