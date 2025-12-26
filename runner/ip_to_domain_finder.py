import os
import json
import time
import sys
import re
import requests
import socket
from datetime import datetime
import uuid

def generate_session_id():
    return str(uuid.uuid4())

def validate_ip(ip):
    """
    Validate if input is a valid IPv4 address
    """
    ip_regex = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return re.match(ip_regex, ip) is not None

def get_ip_info(ip):
    """
    Get information about an IP address using ip-api.com
    """
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                # Create a flag emoji based on country code
                country_code = data.get('countryCode', '').upper()
                flag = ""
                if country_code:
                    try:
                        # Convert country code to flag emoji
                        flag = ''.join([chr(ord(c) + 127397) for c in country_code])
                    except:
                        flag = ""
                
                return {
                    "ip": data.get('query'),
                    "location": f"{data.get('city', '')}, {data.get('country', '')}",
                    "flag": flag,
                    "isp": data.get('isp', ''),
                    "region": data.get('regionName', ''),
                    "country": data.get('country', ''),
                    "countryCode": country_code,
                    "lat": data.get('lat'),
                    "lon": data.get('lon'),
                    "timezone": data.get('timezone', ''),
                    "org": data.get('org', ''),
                    "as": data.get('as', '')
                }
            else:
                return {"error": data.get('message', 'Unknown error')}
        else:
            return {"error": f"API request failed with status code {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def find_domains_for_ip(ip):
    """
    Find domains hosted on an IP address using HackerTarget API
    """
    domains = []
    
    # Method 1: Use HackerTarget API (most reliable and free)
    try:
        url = f"https://api.hackertarget.com/reverseiplookup/?q={ip}"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            if "error" not in response.text.lower() and "no records" not in response.text.lower():
                domain_list = response.text.strip().split('\n')
                
                for domain in domain_list:
                    domain = domain.strip()
                    if domain and not domain.startswith('Error') and domain not in [d.get("name", "") for d in domains]:
                        # Basic validation - skip if it looks like an error message
                        if len(domain) > 3 and '.' in domain and ' ' not in domain:
                            # Check if domain is active
                            try:
                                socket.gethostbyname(domain)
                                status = 'active'
                            except:
                                status = 'inactive'
                            
                            domains.append({
                                "name": domain,
                                "title": f"Website {len(domains) + 1}",
                                "status": status
                            })
    except Exception as e:
        print(f"Error with hackertarget.com: {str(e)}")
    
    return domains[:20]  # Limit to 20 domains

def check_ip_domains(ip):
    """
    Main function to check domains hosted on an IP address
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting reverse IP lookup for: {ip}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Finding domains hosted on IP...",
        "session_id": session_id
    }
    
    try:
        # Validate IP address
        if not validate_ip(ip):
            raise ValueError("Invalid IPv4 address format")
        
        # Get IP information
        print(f"Getting information for IP {ip}...")
        ip_info = get_ip_info(ip)
        
        if "error" in ip_info:
            raise ValueError(ip_info["error"])
        
        # Find domains hosted on this IP
        print(f"Finding domains for IP {ip}...")
        domains = find_domains_for_ip(ip)
        
        # Create final results
        results = {
            "status": "success",
            "ip": ip,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "ipInfo": ip_info,
                "domains": domains
            }
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
    
    # Always write results to results.json (like your original code)
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
    ip = os.environ.get("IP")
    if not ip:
        print("ERROR: IP environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "IP environment variable not set.",
            "session_id": os.environ.get("SESSION_ID", "unknown")
        }
        
        # Write error results to results.json (like your original)
        try:
            with open('results.json', 'w') as f:
                json.dump(error_result, f)
            print("Error results written to results.json")
        except Exception as file_error:
            print(f"ERROR writing error results file: {str(file_error)}")
        
        print(f"results={json.dumps(error_result)}")
        sys.exit(1)
        
    ip_results = check_ip_domains(ip)
    
    # The results are already printed in the function
    sys.exit(0)
