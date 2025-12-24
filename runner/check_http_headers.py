# runner/check_http_headers.py
import os
import json
import time
import sys
import uuid
import re
import requests
from datetime import datetime
from urllib.parse import urlparse, urlunparse
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

def check_http_headers(url):
    """
    Fetches and analyzes HTTP headers for the specified URL.
    Returns detailed information about the headers, status, and security analysis.
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Format the URL
    url = format_url(url)
    
    print(f"Starting HTTP header check for: {url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results with error state
    results = {
        "status": "error", 
        "message": "HTTP header check failed to start.",
        "session_id": session_id
    }
    
    try:
        # Basic URL validation
        if not url or not re.match(r'^https?://.+\..+', url):
            raise ValueError("Invalid URL format")
        
        print(f"Checking HTTP headers for {url}")
        
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
        
        # Extract all headers
        headers_dict = dict(response.headers)
        
        # Convert header keys to a consistent format (Title-Case)
        formatted_headers = {}
        for key, value in headers_dict.items():
            # Convert to title case with hyphens
            formatted_key = '-'.join(word.capitalize() for word in key.split('-'))
            formatted_headers[formatted_key] = value
        
        # Security analysis
        security_analysis = analyze_security_headers(formatted_headers)
        
        # Performance analysis
        performance_analysis = analyze_performance_headers(formatted_headers)
        
        # Server information
        server_info = extract_server_info(formatted_headers, domain)
        
        # Create comprehensive result
        header_info = {
            "url": url,
            "final_url": response.url,
            "status_code": response.status_code,
            "status_text": get_status_text(response.status_code),
            "protocol": f"HTTP/{response.raw.version}",
            "response_time": response_time,
            "date": response.headers.get('Date', datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')),
            "headers": formatted_headers,
            "security_analysis": security_analysis,
            "performance_analysis": performance_analysis,
            "server_info": server_info,
            "redirects": get_redirect_chain(response),
            "content_info": analyze_content_headers(formatted_headers),
            "checked_at": time.time()
        }
        
        results = {
            "status": "success",
            "url": url,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": header_info
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

def analyze_security_headers(headers):
    """
    Analyze security-related headers and provide recommendations
    """
    security_headers = {
        'Content-Security-Policy': headers.get('Content-Security-Policy'),
        'X-Frame-Options': headers.get('X-Frame-Options'),
        'Strict-Transport-Security': headers.get('Strict-Transport-Security'),
        'X-Content-Type-Options': headers.get('X-Content-Type-Options'),
        'X-XSS-Protection': headers.get('X-Xss-Protection'),
        'Referrer-Policy': headers.get('Referrer-Policy'),
        'Permissions-Policy': headers.get('Permissions-Policy'),
        'Cross-Origin-Embedder-Policy': headers.get('Cross-Origin-Embedder-Policy'),
        'Cross-Origin-Opener-Policy': headers.get('Cross-Origin-Opener-Policy'),
        'Cross-Origin-Resource-Policy': headers.get('Cross-Origin-Resource-Policy')
    }
    
    security_score = 0
    max_score = 10
    recommendations = []
    
    # Check each security header
    if security_headers['Content-Security-Policy']:
        security_score += 2
    else:
        recommendations.append("Consider implementing Content-Security-Policy to prevent XSS attacks")
    
    if security_headers['X-Frame-Options']:
        security_score += 1
    else:
        recommendations.append("Add X-Frame-Options header to prevent clickjacking")
    
    if security_headers['Strict-Transport-Security']:
        security_score += 2
    else:
        recommendations.append("Implement HSTS (Strict-Transport-Security) for HTTPS sites")
    
    if security_headers['X-Content-Type-Options']:
        security_score += 1
    else:
        recommendations.append("Add X-Content-Type-Options: nosniff to prevent MIME-sniffing")
    
    if security_headers['Referrer-Policy']:
        security_score += 1
    else:
        recommendations.append("Consider adding Referrer-Policy for privacy")
    
    if security_headers['Permissions-Policy']:
        security_score += 1
    else:
        recommendations.append("Consider implementing Permissions-Policy to control browser features")
    
    # Check for server information disclosure
    server_header = headers.get('Server')
    if server_header and any(version in server_header.lower() for version in ['apache/', 'nginx/', 'iis/', 'php/']):
        recommendations.append("Consider hiding server version information for security")
    
    # Check for powered-by header
    if headers.get('X-Powered-By'):
        recommendations.append("Consider removing X-Powered-By header to avoid technology disclosure")
    
    # Additional checks
    if security_headers['X-Xss-Protection']:
        security_score += 1
    
    if security_headers['Cross-Origin-Embedder-Policy']:
        security_score += 0.5
    
    if security_headers['Cross-Origin-Opener-Policy']:
        security_score += 0.5
    
    return {
        "score": round(security_score, 1),
        "max_score": max_score,
        "grade": get_security_grade(security_score, max_score),
        "headers_present": {k: v for k, v in security_headers.items() if v},
        "headers_missing": [k for k, v in security_headers.items() if not v],
        "recommendations": recommendations
    }

def analyze_performance_headers(headers):
    """
    Analyze performance-related headers
    """
    performance_info = {
        "compression": None,
        "caching": None,
        "etag": None,
        "last_modified": None,
        "content_length": None
    }
    
    # Check compression
    encoding = headers.get('Content-Encoding')
    if encoding:
        performance_info["compression"] = {
            "enabled": True,
            "method": encoding
        }
    else:
        performance_info["compression"] = {
            "enabled": False,
            "recommendation": "Consider enabling gzip or Brotli compression"
        }
    
    # Check caching
    cache_control = headers.get('Cache-Control')
    expires = headers.get('Expires')
    
    if cache_control:
        performance_info["caching"] = {
            "enabled": True,
            "cache_control": cache_control,
            "expires": expires
        }
    elif expires:
        performance_info["caching"] = {
            "enabled": True,
            "cache_control": None,
            "expires": expires
        }
    else:
        performance_info["caching"] = {
            "enabled": False,
            "recommendation": "Consider implementing Cache-Control headers"
        }
    
    # Check ETag
    etag = headers.get('Etag')
    if etag:
        performance_info["etag"] = etag
    
    # Check Last-Modified
    last_modified = headers.get('Last-Modified')
    if last_modified:
        performance_info["last_modified"] = last_modified
    
    # Content length
    content_length = headers.get('Content-Length')
    if content_length:
        performance_info["content_length"] = f"{int(content_length) / 1024:.2f} KB"
    
    return performance_info

def extract_server_info(headers, domain):
    """
    Extract server information from headers
    """
    server_info = {
        "server": headers.get('Server'),
        "x_powered_by": headers.get('X-Powered-By'),
        "technology": [],
        "ip_address": None
    }
    
    # Detect technologies
    server_header = headers.get('Server', '').lower()
    powered_by = headers.get('X-Powered-By', '').lower()
    
    if 'apache' in server_header:
        server_info["technology"].append("Apache")
    if 'nginx' in server_header:
        server_info["technology"].append("Nginx")
    if 'iis' in server_header:
        server_info["technology"].append("IIS")
    if 'cloudflare' in server_header:
        server_info["technology"].append("Cloudflare")
    if 'php' in powered_by:
        server_info["technology"].append("PHP")
    if 'asp.net' in powered_by:
        server_info["technology"].append("ASP.NET")
    if 'express' in powered_by:
        server_info["technology"].append("Express.js")
    
    # Try to get IP address
    try:
        ip = socket.gethostbyname(domain)
        server_info["ip_address"] = ip
    except:
        pass
    
    return server_info

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

def analyze_content_headers(headers):
    """
    Analyze content-related headers
    """
    content_info = {
        "type": headers.get('Content-Type'),
        "length": headers.get('Content-Length'),
        "encoding": headers.get('Content-Encoding'),
        "language": headers.get('Content-Language'),
        "disposition": headers.get('Content-Disposition')
    }
    
    # Parse content type
    content_type = headers.get('Content-Type', '')
    if ';' in content_type:
        content_info["mime_type"] = content_type.split(';')[0].strip()
        content_info["charset"] = content_type.split(';')[1].strip() if len(content_type.split(';')) > 1 else None
    else:
        content_info["mime_type"] = content_type
        content_info["charset"] = None
    
    return content_info

def get_status_text(status_code):
    """
    Get human-readable status text
    """
    status_texts = {
        200: "OK",
        201: "Created",
        202: "Accepted",
        204: "No Content",
        301: "Moved Permanently",
        302: "Found",
        303: "See Other",
        304: "Not Modified",
        307: "Temporary Redirect",
        308: "Permanent Redirect",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        408: "Request Timeout",
        429: "Too Many Requests",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout"
    }
    return status_texts.get(status_code, "Unknown")

def get_security_grade(score, max_score):
    """
    Get security grade based on score
    """
    percentage = (score / max_score) * 100
    if percentage >= 80:
        return "A"
    elif percentage >= 60:
        return "B"
    elif percentage >= 40:
        return "C"
    elif percentage >= 20:
        return "D"
    else:
        return "F"

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
        
    header_results = check_http_headers(target_url)
    
    # The results are already printed in the function
    sys.exit(0)  # Exit with 0 to prevent workflow failure
