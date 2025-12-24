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

def analyze_headers(url):
    """
    Analyze HTTP headers for a given URL
    """
    try:
        # Measure response time
        start_time = time.time()
        response = requests.get(url, timeout=10, allow_redirects=True)
        response_time = (time.time() - start_time) * 1000  # milliseconds
        
        # Extract headers
        headers = dict(response.headers)
        
        # Analyze security headers
        security_headers = analyze_security_headers(headers)
        
        # Analyze performance headers
        performance_headers = analyze_performance_headers(headers)
        
        # Analyze content headers
        content_headers = analyze_content_headers(headers)
        
        # Get server information
        server_info = analyze_server_info(headers)
        
        # Get protocol information
        protocol_info = {
            "protocol": f"HTTP/{response.raw.version / 10:.1f}",
            "status_code": response.status_code,
            "status_text": response.reason
        }
        
        return {
            "url": url,
            "response_time": response_time,
            "protocol": protocol_info,
            "headers": headers,
            "security_analysis": security_headers,
            "performance_analysis": performance_headers,
            "content_analysis": content_headers,
            "server_info": server_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error analyzing headers: {str(e)}")
        return {
            "url": url,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def analyze_security_headers(headers):
    """
    Analyze security-related headers
    """
    security_headers = {
        "Content-Security-Policy": headers.get("Content-Security-Policy", "Not Set"),
        "X-Frame-Options": headers.get("X-Frame-Options", "Not Set"),
        "X-Content-Type-Options": headers.get("X-Content-Type-Options", "Not Set"),
        "Strict-Transport-Security": headers.get("Strict-Transport-Security", "Not Set"),
        "X-XSS-Protection": headers.get("X-XSS-Protection", "Not Set"),
        "Referrer-Policy": headers.get("Referrer-Policy", "Not Set"),
        "Permissions-Policy": headers.get("Permissions-Policy", "Not Set")
    }
    
    # Calculate security score
    security_score = 0
    for header, value in security_headers.items():
        if value != "Not Set":
            security_score += 1
    
    security_headers["security_score"] = f"{security_score}/{len(security_headers)}"
    
    return security_headers

def analyze_performance_headers(headers):
    """
    Analyze performance-related headers
    """
    performance_headers = {
        "Cache-Control": headers.get("Cache-Control", "Not Set"),
        "Expires": headers.get("Expires", "Not Set"),
        "ETag": headers.get("ETag", "Not Set"),
        "Last-Modified": headers.get("Last-Modified", "Not Set"),
        "Vary": headers.get("Vary", "Not Set"),
        "Content-Encoding": headers.get("Content-Encoding", "Not Set"),
        "Keep-Alive": headers.get("Keep-Alive", "Not Set"),
        "Connection": headers.get("Connection", "Not Set")
    }
    
    # Check for caching
    has_caching = (
        performance_headers["Cache-Control"] != "Not Set" or
        performance_headers["Expires"] != "Not Set"
    )
    
    # Check for compression
    has_compression = (
        performance_headers["Content-Encoding"] != "Not Set" and
        "gzip" in performance_headers["Content-Encoding"]
    )
    
    performance_headers["has_caching"] = has_caching
    performance_headers["has_compression"] = has_compression
    
    return performance_headers

def analyze_content_headers(headers):
    """
    Analyze content-related headers
    """
    content_headers = {
        "Content-Type": headers.get("Content-Type", "Not Set"),
        "Content-Length": headers.get("Content-Length", "Not Set"),
        "Content-Language": headers.get("Content-Language", "Not Set"),
        "Content-Disposition": headers.get("Content-Disposition", "Not Set")
    }
    
    # Parse content type
    content_type = content_headers["Content-Type"]
    if content_type != "Not Set":
        media_type = content_type.split(";")[0].strip()
        charset = ""
        
        if ";" in content_type:
            for part in content_type.split(";"):
                if "charset" in part:
                    charset = part.split("=")[1].strip()
        
        content_headers["media_type"] = media_type
        content_headers["charset"] = charset
    else:
        content_headers["media_type"] = "Unknown"
        content_headers["charset"] = "Unknown"
    
    return content_headers

def analyze_server_info(headers):
    """
    Analyze server information from headers
    """
    server_info = {
        "Server": headers.get("Server", "Not Set"),
        "X-Powered-By": headers.get("X-Powered-By", "Not Set"),
        "X-Generator": headers.get("X-Generator", "Not Set"),
        "X-Drupal-Cache": headers.get("X-Drupal-Cache", "Not Set"),
        "X-Varnish": headers.get("X-Varnish", "Not Set"),
        "Via": headers.get("Via", "Not Set")
    }
    
    # Detect server type
    server = server_info["Server"]
    if server != "Not Set":
        if "nginx" in server.lower():
            server_type = "Nginx"
        elif "apache" in server.lower():
            server_type = "Apache"
        elif "iis" in server.lower():
            server_type = "IIS"
        elif "cloudflare" in server.lower():
            server_type = "Cloudflare"
        else:
            server_type = "Unknown"
    else:
        server_type = "Unknown"
    
    server_info["server_type"] = server_type
    
    return server_info

def check_http_headers(url):
    """
    Check HTTP headers for a website
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Format the URL
    url = format_url(url)
    
    print(f"Starting HTTP header check for: {url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Analyzing HTTP headers...",
        "session_id": session_id
    }
    
    try:
        # Basic URL validation
        if not url or not re.match(r'^https?://.+\..+', url):
            raise ValueError("Invalid URL format")
        
        print(f"Checking HTTP headers for {url}")
        
        # Analyze headers
        header_data = analyze_headers(url)
        
        if "error" in header_data:
            raise ValueError(header_data["error"])
        
        # Create final results
        results = {
            "status": "success",
            "url": url,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": header_data
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
        
    header_results = check_http_headers(target_url)
    
    # The results are already printed in the function
    sys.exit(0)
