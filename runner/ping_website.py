import os
import json
import time
import sys
import re
import socket
import requests
from datetime import datetime
from urllib.parse import urlparse
import uuid

def generate_session_id():
    return str(uuid.uuid4())

def validate_url(url):
    """
    Validate if URL is properly formatted
    """
    try:
        parsed_url = urlparse(url)
        return parsed_url.scheme in ['http', 'https']
    except:
        return False

def resolve_ip_address(url):
    """
    Resolve IP address from hostname
    """
    try:
        hostname = urlparse(url).hostname
        if hostname:
            ip_address = socket.gethostbyname(hostname)
            return ip_address
        return None
    except socket.gaierror:
        return None

def get_server_info(url):
    """
    Get server information from HTTP headers
    """
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        
        server_info = {
            'server': response.headers.get('Server', 'Unknown'),
            'powered_by': response.headers.get('X-Powered-By', 'Unknown'),
            'content_type': response.headers.get('Content-Type', 'Unknown'),
            'content_length': response.headers.get('Content-Length', 'Unknown'),
            'cache_control': response.headers.get('Cache-Control', 'Unknown'),
            'last_modified': response.headers.get('Last-Modified', 'Unknown')
        }
        
        return server_info
    except Exception as e:
        print(f"Error getting server info: {str(e)}")
        return {
            'server': 'Unknown',
            'error': str(e)
        }

def get_location_info(ip_address):
    """
    Get location information for IP address (basic implementation)
    """
    try:
        # Using ip-api.com for geolocation (free tier)
        response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'country': data.get('country', 'Unknown'),
                'region': data.get('regionName', 'Unknown'),
                'city': data.get('city', 'Unknown'),
                'isp': data.get('isp', 'Unknown'),
                'org': data.get('org', 'Unknown'),
                'timezone': data.get('timezone', 'Unknown')
            }
        else:
            return {
                'country': 'Unknown',
                'region': 'Unknown',
                'city': 'Unknown',
                'error': 'Location service unavailable'
            }
    except Exception as e:
        print(f"Error getting location info: {str(e)}")
        return {
            'country': 'Unknown',
            'region': 'Unknown',
            'city': 'Unknown',
            'error': str(e)
        }

def ping_website(url):
    """
    Main function to ping a website and get response information
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting ping for: {url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Pinging website...",
        "session_id": session_id
    }
    
    try:
        # Validate URL
        if not validate_url(url):
            raise ValueError("Invalid URL format. Please include http:// or https://")
        
        # Measure response time
        start_time = time.time()
        
        # Perform HEAD request (lighter than GET)
        response = requests.head(url, timeout=10, allow_redirects=True)
        end_time = time.time()
        
        # Calculate latency in milliseconds
        latency = (end_time - start_time) * 1000
        
        # Get IP address
        ip_address = resolve_ip_address(url)
        
        # Get server information
        server_info = get_server_info(url)
        
        # Get location information
        location_info = None
        if ip_address:
            location_info = get_location_info(ip_address)
        
        # Determine status
        if response.status_code < 400:
            status_text = "Reachable"
            status = "success"
        elif response.status_code == 404:
            status_text = "Not Found (404)"
            status = "error"
        elif response.status_code >= 500:
            status_text = "Server Error"
            status = "error"
        else:
            status_text = f"HTTP {response.status_code}"
            status = "warning"
        
        # Create final results
        results = {
            "status": status,
            "message": f"Website is {status_text.lower()}.",
            "url": url,
            "latency": latency,
            "statusCode": response.status_code,
            "statusText": status_text,
            "ipAddress": ip_address or "Unknown",
            "server": server_info.get('server', 'Unknown'),
            "location": f"{location_info.get('city', 'Unknown')}, {location_info.get('region', 'Unknown')}, {location_info.get('country', 'Unknown')}" if location_info else "Unknown",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "additional_info": {
                "server_headers": server_info,
                "location_details": location_info
            }
        }
        
    except requests.exceptions.Timeout:
        results = {
            "status": "error",
            "message": "Request timed out. The server did not respond within 10 seconds.",
            "url": url,
            "session_id": session_id,
            "error": "timeout"
        }
    except requests.exceptions.ConnectionError:
        results = {
            "status": "error",
            "message": "Could not connect to the server. The website may be down or the URL is incorrect.",
            "url": url,
            "session_id": session_id,
            "error": "connection_error"
        }
    except requests.exceptions.RequestException as e:
        results = {
            "status": "error",
            "message": f"Request failed: {str(e)}",
            "url": url,
            "session_id": session_id,
            "error": str(e)
        }
    except Exception as e:
        results = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "url": url,
            "session_id": session_id,
            "error": str(e)
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
    target_url = os.environ.get("URL")
    if not target_url:
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
        
    ping_results = ping_website(target_url)
    
    # The results are already printed in the function
    sys.exit(0)
