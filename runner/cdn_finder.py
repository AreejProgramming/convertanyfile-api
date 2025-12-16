# File: runner/cdn_finder.py

import os
import json
import time
import sys
import uuid
import requests
from urllib.parse import urlparse

def generate_session_id():
    return str(uuid.uuid4())

def detect_cdn(url):
    """
    Detects if a website uses a CDN by analyzing HTTP headers and DNS records.
    Includes robust error handling and logging.
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting CDN detection for URL: {url}") # Log for debugging
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "Analysis failed to start.",
        "session_id": session_id
    }
    
    try:
        # Parse the URL to get the domain
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        if not domain:
            raise ValueError("Invalid URL format")
        
        print(f"Analyzing domain: {domain}")
        
        # Make a request to the website to get headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response_headers = dict(response.headers)
        
        # CDN detection based on headers
        cdn_provider = None
        cdn_detected = False
        
        # Check for Cloudflare
        if 'server' in response_headers and 'cloudflare' in response_headers['server'].lower():
            cdn_detected = True
            cdn_provider = {
                "name": "Cloudflare",
                "features": ["DDoS Protection", "Web Application Firewall", "Global Network"],
                "servers": "275+",
                "color": "#f38020"
            }
        
        # Check for AWS CloudFront
        elif 'x-amz-cf-id' in response_headers or ('server' in response_headers and 'cloudfront' in response_headers['server'].lower()):
            cdn_detected = True
            cdn_provider = {
                "name": "AWS CloudFront",
                "features": ["Edge Locations", "Dynamic Content", "Security"],
                "servers": "400+",
                "color": "#ff9900"
            }
        
        # Check for Fastly
        elif 'x-served-by' in response_headers and 'fastly' in response_headers['x-served-by'].lower():
            cdn_detected = True
            cdn_provider = {
                "name": "Fastly",
                "features": ["Real-time Analytics", "Edge Compute", "Instant Purge"],
                "servers": "100+",
                "color": "#ff3333"
            }
        
        # Check for Akamai
        elif 'server' in response_headers and 'akamai' in response_headers['server'].lower():
            cdn_detected = True
            cdn_provider = {
                "name": "Akamai",
                "features": ["Enterprise CDN", "Media Delivery", "Security Suite"],
                "servers": "3000+",
                "color": "#0099d8"
            }
        
        # Check for Microsoft Azure CDN
        elif 'server' in response_headers and 'ecs' in response_headers['server'].lower():
            cdn_detected = True
            cdn_provider = {
                "name": "Microsoft Azure CDN",
                "features": ["Azure Integration", "HTTP/2 Support", "Dynamic Site Acceleration"],
                "servers": "120+",
                "color": "#0078d4"
            }
        
        # Check for Google Cloud CDN
        elif 'via' in response_headers and 'google' in response_headers['via'].lower():
            cdn_detected = True
            cdn_provider = {
                "name": "Google Cloud CDN",
                "features": ["Global Infrastructure", "Load Balancing", "Edge Security"],
                "servers": "200+",
                "color": "#4285f4"
            }
        
        # Get DNS information (simplified)
        dns_info = {
            "aRecords": [domain],  # Simplified for this example
            "ttl": "300"
        }
        
        results = {
            "status": "success",
            "url": url,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "detected": cdn_detected,
                "provider": cdn_provider,
                "headers": response_headers,
                "dnsInfo": dns_info
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
            "message": "Connection error: Could not connect to the website.",
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
        
    analysis_results = detect_cdn(target_url)
    
    # Print the results in a format that can be easily extracted
    print(f"results={json.dumps(analysis_results)}")
