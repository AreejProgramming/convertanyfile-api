import os
import json
import time
import sys
import re
import requests
import socket
import dns.resolver
import whois
from datetime import datetime
from urllib.parse import urlparse
import uuid
import ipinfo

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

def get_ip_address(url):
    """
    Get the IP address of a domain
    """
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.netloc
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except Exception as e:
        print(f"Error getting IP address: {str(e)}")
        return None

def get_ip_info(ip_address):
    """
    Get information about an IP address using ipinfo.io
    """
    try:
        # You would need to get an API token from ipinfo.io
        # For this example, we'll use a mock approach
        # In a real implementation, you would use:
        # handler = ipinfo.getHandler(access_token='YOUR_API_TOKEN')
        # details = handler.getDetails(ip_address)
        
        # Mock data for demonstration
        return {
            "ip": ip_address,
            "hostname": None,
            "city": "New York",
            "region": "New York",
            "country": "US",
            "loc": "40.7128,-74.0060",
            "org": "AS12345 Example Hosting Provider",
            "postal": "10001",
            "timezone": "America/New_York"
        }
    except Exception as e:
        print(f"Error getting IP info: {str(e)}")
        return None

def get_nameservers(domain):
    """
    Get the nameservers for a domain
    """
    try:
        parsed_url = urlparse(domain)
        hostname = parsed_url.netloc
        
        # Remove www. if present
        if hostname.startswith('www.'):
            hostname = hostname[4:]
            
        nameservers = dns.resolver.resolve(hostname, 'NS')
        return [str(ns) for ns in nameservers]
    except Exception as e:
        print(f"Error getting nameservers: {str(e)}")
        return []

def get_whois_info(domain):
    """
    Get WHOIS information for a domain
    """
    try:
        parsed_url = urlparse(domain)
        hostname = parsed_url.netloc
        
        # Remove www. if present
        if hostname.startswith('www.'):
            hostname = hostname[4:]
            
        domain_info = whois.whois(hostname)
        return domain_info
    except Exception as e:
        print(f"Error getting WHOIS info: {str(e)}")
        return None

def detect_hosting_provider(url):
    """
    Detect the hosting provider of a website
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Format the URL
    url = format_url(url)
    
    print(f"Starting hosting provider check for: {url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results with error state
    results = {
        "status": "error", 
        "message": "Hosting provider check failed to start.",
        "session_id": session_id
    }
    
    try:
        # Basic URL validation
        if not url or not re.match(r'^https?://.+\..+', url):
            raise ValueError("Invalid URL format")
        
        print(f"Checking hosting provider for {url}")
        
        # Get IP address
        ip_address = get_ip_address(url)
        if not ip_address:
            raise ValueError("Could not resolve IP address")
        
        # Get IP information
        ip_info = get_ip_info(ip_address)
        if not ip_info:
            raise ValueError("Could not get IP information")
        
        # Get nameservers
        nameservers = get_nameservers(url)
        
        # Get WHOIS information
        whois_info = get_whois_info(url)
        
        # Extract hosting provider from IP info
        org = ip_info.get("org", "")
        
        # Determine hosting provider based on patterns
        provider = {
            "name": "Unknown",
            "type": "Unknown",
            "features": [],
            "priceRange": "Unknown"
        }
        
        # Check for common hosting providers
        if "Amazon" in org or "AWS" in org:
            provider = {
                "name": "Amazon Web Services (AWS)",
                "type": "Cloud Hosting",
                "features": ["EC2 Instances", "S3 Storage", "Global Infrastructure"],
                "priceRange": "Pay-as-you-go"
            }
        elif "Google" in org:
            provider = {
                "name": "Google Cloud Platform",
                "type": "Cloud Hosting",
                "features": ["Compute Engine", "Cloud Storage", "Global Network"],
                "priceRange": "Pay-as-you-go"
            }
        elif "Microsoft" in org or "Azure" in org:
            provider = {
                "name": "Microsoft Azure",
                "type": "Cloud Hosting",
                "features": ["Virtual Machines", "Blob Storage", "Global Infrastructure"],
                "priceRange": "Pay-as-you-go"
            }
        elif "DigitalOcean" in org:
            provider = {
                "name": "DigitalOcean",
                "type": "Cloud VPS",
                "features": ["Droplets", "Kubernetes", "Load Balancers"],
                "priceRange": "$4 - $960/mo"
            }
        elif "Cloudflare" in org:
            provider = {
                "name": "Cloudflare",
                "type": "Edge Platform",
                "features": ["DDoS Protection", "Workers", "Pages"],
                "priceRange": "Free - $5,000+/mo"
            }
        elif "Bluehost" in org or any(ns.lower().find("bluehost") != -1 for ns in nameservers):
            provider = {
                "name": "Bluehost",
                "type": "Shared Hosting",
                "features": ["WordPress Optimized", "Free SSL", "24/7 Support"],
                "priceRange": "$2.95 - $13.95/mo"
            }
        elif "HostGator" in org or any(ns.lower().find("hostgator") != -1 for ns in nameservers):
            provider = {
                "name": "HostGator",
                "type": "Shared Hosting",
                "features": ["Unlimited Bandwidth", "Free Domain", "Website Builder"],
                "priceRange": "$2.75 - $5.95/mo"
            }
        elif "GoDaddy" in org or any(ns.lower().find("godaddy") != -1 for ns in nameservers):
            provider = {
                "name": "GoDaddy",
                "type": "Shared Hosting",
                "features": ["Easy Setup", "Microsoft 365", "Daily Backups"],
                "priceRange": "$1.99 - $24.99/mo"
            }
        elif "SiteGround" in org or any(ns.lower().find("siteground") != -1 for ns in nameservers):
            provider = {
                "name": "SiteGround",
                "type": "Managed Hosting",
                "features": ["SuperCacher", "Daily Backups", "Free CDN"],
                "priceRange": "$3.99 - $10.69/mo"
            }
        elif "Vultr" in org or any(ns.lower().find("vultr") != -1 for ns in nameservers):
            provider = {
                "name": "Vultr",
                "type": "Cloud VPS",
                "features": ["High Frequency", "Bare Metal", "Global Network"],
                "priceRange": "$2.50 - $500/mo"
            }
        
        # Get server headers
        try:
            response = requests.get(url, timeout=10)
            server = response.headers.get('Server', 'Unknown')
            powered_by = response.headers.get('X-Powered-By', 'Unknown')
            last_modified = response.headers.get('Last-Modified', 'Unknown')
        except Exception as e:
            print(f"Error getting server headers: {str(e)}")
            server = "Unknown"
            powered_by = "Unknown"
            last_modified = "Unknown"
        
        # Generate hosting details
        hosting_details = {
            "uptime": f"{(95 + (hash(url) % 5)).toFixed(2)}%",  # Mock uptime
            "responseTime": f"{100 + (hash(url) % 200)}ms",  # Mock response time
            "plan": provider["type"] == "Cloud Hosting" ? "Pay-as-you-go" : "Standard Plan",
            "since": whois_info and whois_info.creation_date and whois_info.creation_date.year or f"{2013 + (hash(url) % 10)}"
        }
        
        # Create server info
        server_info = {
            "ip": ip_address,
            "location": f"{ip_info.get('city', 'Unknown')}, {ip_info.get('country', 'Unknown')}",
            "nameservers": nameservers,
            "server": server,
            "x-powered-by": powered_by,
            "last-modified": last_modified
        }
        
        # Create final results
        results = {
            "status": "success",
            "url": url,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "provider": provider,
                "server_info": server_info,
                "hosting_details": hosting_details
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
        
    hosting_results = detect_hosting_provider(target_url)
    
    # The results are already printed in the function
    sys.exit(0)
