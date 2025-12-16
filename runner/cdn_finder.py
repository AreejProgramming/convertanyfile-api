# File: runner/cdn_finder.py

import os
import json
import time
import sys
import uuid
import requests
import socket
import subprocess
from urllib.parse import urlparse

def generate_session_id():
    return str(uuid.uuid4())

def get_cname_records(domain):
    """
    Get CNAME records for a domain to detect CDN usage
    """
    try:
        result = subprocess.run(
            ['dig', 'CNAME', domain],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout
            # Parse the dig output to extract CNAME records
            lines = output.split('\n')
            cname_records = []
            
            for line in lines:
                if 'CNAME' in line and domain in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        cname_records.append(parts[4])
            
            return cname_records
    except Exception as e:
        print(f"Error getting CNAME records: {e}")
    
    return []

def get_ip_addresses(domain):
    """
    Get IP addresses for a domain
    """
    try:
        result = subprocess.run(
            ['dig', 'A', domain],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout
            # Parse the dig output to extract IP addresses
            lines = output.split('\n')
            ip_addresses = []
            
            for line in lines:
                if domain in line and 'A' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        ip_addresses.append(parts[4])
            
            return ip_addresses
    except Exception as e:
        print(f"Error getting IP addresses: {e}")
    
    return []

def get_asn_info(ip):
    """
    Get ASN (Autonomous System Number) information for an IP
    """
    try:
        # Use a free API to get ASN information
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'asn': data.get('org', ''),
                'isp': data.get('org', ''),
                'country': data.get('country', '')
            }
    except Exception as e:
        print(f"Error getting ASN info for {ip}: {e}")
    
    return None

def detect_cdn_by_asn(asn_info):
    """
    Detect CDN provider based on ASN information
    """
    if not asn_info or not asn_info.get('asn'):
        return None
    
    asn = asn_info['asn'].lower()
    isp = asn_info['isp'].lower()
    
    # Check for known CDN providers in ASN/ISP information
    if 'cloudflare' in asn or 'cloudflare' in isp:
        return {
            "name": "Cloudflare",
            "features": ["DDoS Protection", "Web Application Firewall", "Global Network"],
            "servers": "275+",
            "color": "#f38020"
        }
    elif 'amazon' in asn or 'aws' in asn or 'cloudfront' in asn:
        return {
            "name": "AWS CloudFront",
            "features": ["Edge Locations", "Dynamic Content", "Security"],
            "servers": "400+",
            "color": "#ff9900"
        }
    elif 'fastly' in asn:
        return {
            "name": "Fastly",
            "features": ["Real-time Analytics", "Edge Compute", "Instant Purge"],
            "servers": "100+",
            "color": "#ff3333"
        }
    elif 'akamai' in asn:
        return {
            "name": "Akamai",
            "features": ["Enterprise CDN", "Media Delivery", "Security Suite"],
            "servers": "3000+",
            "color": "#0099d8"
        }
    elif 'microsoft' in asn or 'azure' in asn:
        return {
            "name": "Microsoft Azure CDN",
            "features": ["Azure Integration", "HTTP/2 Support", "Dynamic Site Acceleration"],
            "servers": "120+",
            "color": "#0078d4"
        }
    elif 'google' in asn:
        return {
            "name": "Google Cloud CDN",
            "features": ["Global Infrastructure", "Load Balancing", "Edge Security"],
            "servers": "200+",
            "color": "#4285f4"
        }
    elif 'keycdn' in asn:
        return {
            "name": "KeyCDN",
            "features": ["Edge Caching", "Image Optimization", "Real-time Logs"],
            "servers": "34+",
            "color": "#3d7eaa"
        }
    elif 'stackpath' in asn or 'maxcdn' in asn:
        return {
            "name": "StackPath",
            "features": ["Edge Computing", "WAF", "DDoS Protection"],
            "servers": "50+",
            "color": "#f4842b"
        }
    elif 'incapsula' in asn:
        return {
            "name": "Imperva Incapsula",
            "features": ["CDN Security", "DDoS Protection", "Load Balancing"],
            "servers": "50+",
            "color": "#003366"
        }
    
    return None

def detect_cdn_by_cname(cname_records):
    """
    Detect CDN provider based on CNAME records
    """
    if not cname_records:
        return None
    
    for cname in cname_records:
        cname_lower = cname.lower()
        
        if 'cloudflare' in cname_lower:
            return {
                "name": "Cloudflare",
                "features": ["DDoS Protection", "Web Application Firewall", "Global Network"],
                "servers": "275+",
                "color": "#f38020"
            }
        elif 'cloudfront' in cname_lower:
            return {
                "name": "AWS CloudFront",
                "features": ["Edge Locations", "Dynamic Content", "Security"],
                "servers": "400+",
                "color": "#ff9900"
            }
        elif 'fastly' in cname_lower:
            return {
                "name": "Fastly",
                "features": ["Real-time Analytics", "Edge Compute", "Instant Purge"],
                "servers": "100+",
                "color": "#ff3333"
            }
        elif 'akamai' in cname_lower:
            return {
                "name": "Akamai",
                "features": ["Enterprise CDN", "Media Delivery", "Security Suite"],
                "servers": "3000+",
                "color": "#0099d8"
            }
        elif 'azureedge' in cname_lower:
            return {
                "name": "Microsoft Azure CDN",
                "features": ["Azure Integration", "HTTP/2 Support", "Dynamic Site Acceleration"],
                "servers": "120+",
                "color": "#0078d4"
            }
        elif 'google' in cname_lower:
            return {
                "name": "Google Cloud CDN",
                "features": ["Global Infrastructure", "Load Balancing", "Edge Security"],
                "servers": "200+",
                "color": "#4285f4"
            }
        elif 'keycdn' in cname_lower:
            return {
                "name": "KeyCDN",
                "features": ["Edge Caching", "Image Optimization", "Real-time Logs"],
                "servers": "34+",
                "color": "#3d7eaa"
            }
        elif 'stackpath' in cname_lower or 'maxcdn' in cname_lower:
            return {
                "name": "StackPath",
                "features": ["Edge Computing", "WAF", "DDoS Protection"],
                "servers": "50+",
                "color": "#f4842b"
            }
        elif 'incapula' in cname_lower:
            return {
                "name": "Imperva Incapsula",
                "features": ["CDN Security", "DDoS Protection", "Load Balancing"],
                "servers": "50+",
                "color": "#003366"
            }
    
    return None

def detect_cdn_by_headers(headers):
    """
    Detect CDN provider based on HTTP headers
    """
    # Convert headers to lowercase for case-insensitive comparison
    headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
    
    # Check for Cloudflare
    if 'server' in headers_lower and 'cloudflare' in headers_lower['server']:
        return {
            "name": "Cloudflare",
            "features": ["DDoS Protection", "Web Application Firewall", "Global Network"],
            "servers": "275+",
            "color": "#f38020"
        }
    
    # Check for AWS CloudFront
    if 'x-amz-cf-id' in headers_lower or ('server' in headers_lower and 'cloudfront' in headers_lower['server']):
        return {
            "name": "AWS CloudFront",
            "features": ["Edge Locations", "Dynamic Content", "Security"],
            "servers": "400+",
            "color": "#ff9900"
        }
    
    # Check for Fastly
    if 'x-served-by' in headers_lower and 'fastly' in headers_lower['x-served-by']:
        return {
            "name": "Fastly",
            "features": ["Real-time Analytics", "Edge Compute", "Instant Purge"],
            "servers": "100+",
            "color": "#ff3333"
        }
    
    # Check for Akamai
    if 'server' in headers_lower and 'akamai' in headers_lower['server']:
        return {
            "name": "Akamai",
            "features": ["Enterprise CDN", "Media Delivery", "Security Suite"],
            "servers": "3000+",
            "color": "#0099d8"
        }
    
    # Check for Microsoft Azure CDN
    if 'server' in headers_lower and 'ecs' in headers_lower['server']:
        return {
            "name": "Microsoft Azure CDN",
            "features": ["Azure Integration", "HTTP/2 Support", "Dynamic Site Acceleration"],
            "servers": "120+",
            "color": "#0078d4"
        }
    
    # Check for Google Cloud CDN
    if 'via' in headers_lower and 'google' in headers_lower['via']:
        return {
            "name": "Google Cloud CDN",
            "features": ["Global Infrastructure", "Load Balancing", "Edge Security"],
            "servers": "200+",
            "color": "#4285f4"
        }
    
    # Check for KeyCDN
    if 'x-keycdn' in headers_lower:
        return {
            "name": "KeyCDN",
            "features": ["Edge Caching", "Image Optimization", "Real-time Logs"],
            "servers": "34+",
            "color": "#3d7eaa"
        }
    
    # Check for StackPath (formerly MaxCDN)
    if 'x-sp-host' in headers_lower or 'x-cdn' in headers_lower:
        return {
            "name": "StackPath",
            "features": ["Edge Computing", "WAF", "DDoS Protection"],
            "servers": "50+",
            "color": "#f4842b"
        }
    
    # Check for Imperva Incapsula
    if 'x-cdn' in headers_lower and 'incapsula' in headers_lower['x-cdn']:
        return {
            "name": "Imperva Incapsula",
            "features": ["CDN Security", "DDoS Protection", "Load Balancing"],
            "servers": "50+",
            "color": "#003366"
        }
    
    return None

def detect_cdn(url):
    """
    Detects if a website uses a CDN by analyzing HTTP headers, DNS records, and IP-to-ASN mappings.
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
        
        # Initialize variables
        cdn_detected = False
        cdn_provider = None
        response_headers = {}
        dns_info = {
            "aRecords": [],
            "cnameRecords": [],
            "ttl": "300"
        }
        
        # 1. Check DNS records first (non-intrusive)
        print("Checking DNS records...")
        cname_records = get_cname_records(domain)
        dns_info["cnameRecords"] = cname_records
        
        # Detect CDN based on CNAME records
        cdn_provider = detect_cdn_by_cname(cname_records)
        if cdn_provider:
            cdn_detected = True
            print(f"CDN detected via CNAME: {cdn_provider['name']}")
        
        # If not detected via CNAME, check IP addresses and ASN
        if not cdn_detected:
            ip_addresses = get_ip_addresses(domain)
            dns_info["aRecords"] = ip_addresses
            
            for ip in ip_addresses[:3]:  # Check first 3 IPs to avoid too many requests
                asn_info = get_asn_info(ip)
                if asn_info:
                    cdn_provider = detect_cdn_by_asn(asn_info)
                    if cdn_provider:
                        cdn_detected = True
                        print(f"CDN detected via ASN: {cdn_provider['name']}")
                        break
        
        # 2. If still not detected, check HTTP headers
        if not cdn_detected:
            print("Checking HTTP headers...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response_headers = dict(response.headers)
            
            # Detect CDN based on headers
            cdn_provider = detect_cdn_by_headers(response_headers)
            if cdn_provider:
                cdn_detected = True
                print(f"CDN detected via headers: {cdn_provider['name']}")
        
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
