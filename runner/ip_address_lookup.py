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

def validate_input(input_str):
    """
    Validate if input is a valid IP address or domain name
    """
    # IPv4 regex
    ipv4_regex = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    # IPv6 regex (simplified)
    ipv6_regex = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    # Domain name regex
    domain_regex = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$'
    
    return (re.match(ipv4_regex, input_str) or 
            re.match(ipv6_regex, input_str) or 
            re.match(domain_regex, input_str))

def resolve_domain_to_ip(domain):
    """
    Resolve a domain name to its IP address
    """
    try:
        import socket
        ip = socket.gethostbyname(domain)
        return ip
    except:
        return None

def lookup_ip_info(ip):
    """
    Lookup information for an IP address using ip-api.com
    """
    try:
        # Using ip-api.com which is free and doesn't require API key
        url = f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,proxy,hosting,query"
        
        # Measure response time
        start_time = time.time()
        response = requests.get(url, timeout=10)
        response_time = (time.time() - start_time) * 1000  # milliseconds
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                # Determine IP type (IPv4 or IPv6)
                ip_type = 'IPv6' if ':' in ip else 'IPv4'
                
                return {
                    "ip": data.get('query'),
                    "type": ip_type,
                    "country": data.get('country'),
                    "countryCode": data.get('countryCode'),
                    "region": data.get('regionName'),
                    "city": data.get('city'),
                    "latitude": data.get('lat'),
                    "longitude": data.get('lon'),
                    "timezone": data.get('timezone'),
                    "isp": data.get('isp'),
                    "org": data.get('org'),
                    "as": data.get('as'),
                    "proxy": data.get('proxy'),
                    "hosting": data.get('hosting'),
                    "responseTime": response_time,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"error": data.get('message', 'Unknown error')}
        else:
            return {"error": f"API request failed with status code {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def check_ip_address(query):
    """
    Main function to check IP address or domain
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting IP address lookup for: {query}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Looking up IP address information...",
        "session_id": session_id
    }
    
    try:
        # Validate input
        if not query or not validate_input(query):
            raise ValueError("Invalid IP address or domain format")
        
        # Check if input is a domain name
        is_domain = re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$', query)
        
        ip = query
        if is_domain:
            # Resolve domain to IP
            print(f"Resolving domain {query} to IP address...")
            ip = resolve_domain_to_ip(query)
            if not ip:
                raise ValueError(f"Failed to resolve domain {query} to an IP address")
            print(f"Resolved {query} to {ip}")
        
        # Lookup IP information
        print(f"Looking up information for IP {ip}...")
        ip_data = lookup_ip_info(ip)
        
        if "error" in ip_data:
            raise ValueError(ip_data["error"])
        
        # Create final results
        results = {
            "status": "success",
            "query": query,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": ip_data
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
    query = os.environ.get("QUERY")
    if not query:
        print("ERROR: QUERY environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "QUERY environment variable not set.",
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
        
    ip_results = check_ip_address(query)
    
    # The results are already printed in the function
    sys.exit(0)
