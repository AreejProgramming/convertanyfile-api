# File: runner/whois_lookup.py
import os
import json
import time
import sys
import uuid
import re
import whois
from datetime import datetime

def generate_session_id():
    return str(uuid.uuid4())

def extract_domain_from_url(url):
    """
    Extract domain from a URL or return the input if it's already a domain
    """
    # Remove protocol if present
    url = re.sub(r'^https?://', '', url)
    
    # Remove www prefix
    url = re.sub(r'^www\.', '', url)
    
    # Remove path after domain
    url = url.split('/')[0]
    
    return url

def get_first_date(date_field):
    """
    Helper function to extract the first date from a field that might be a list or a single value
    """
    if not date_field:
        return None
    
    # If it's a list, return the first element
    if isinstance(date_field, list):
        return date_field[0]
    
    # If it's already a datetime or string, return it as is
    return date_field

def format_date(date_obj):
    """
    Format a date object to ISO format string (YYYY-MM-DD)
    """
    if not date_obj:
        return ""
    
    if isinstance(date_obj, str):
        # Try to parse the string
        try:
            date_obj = datetime.strptime(date_obj.split(' ')[0], '%Y-%m-%d')
        except ValueError:
            try:
                date_obj = datetime.strptime(date_obj, '%d-%b-%Y')
            except ValueError:
                try:
                    date_obj = datetime.strptime(date_obj, '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    return ""
    
    # Format the date
    return date_obj.strftime('%Y-%m-%d')

def calculate_days_until_expiry(expiry_date):
    """
    Calculate the number of days until a domain expires
    """
    if not expiry_date:
        return None
    
    try:
        # Parse the expiry date
        if isinstance(expiry_date, str):
            expiry_date = datetime.strptime(expiry_date.split(' ')[0], '%Y-%m-%d')
        
        # Calculate the difference
        now = datetime.now()
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        if expiry_date.tzinfo is not None:
            expiry_date = expiry_date.replace(tzinfo=None)
            
        delta = expiry_date - now
        return delta.days
    except:
        return None

def lookup_whois(domain):
    """
    Performs a WHOIS lookup for the given domain
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Clean up the domain input
    domain = extract_domain_from_url(domain)
    
    print(f"Starting WHOIS lookup for: {domain}")
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "WHOIS lookup failed to start.",
        "session_id": session_id
    }
    
    try:
        # Basic domain validation
        domain_regex = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?\.[a-zA-Z]{2,}$'
        if not re.match(domain_regex, domain):
            raise ValueError("Invalid domain format")
        
        print(f"Querying WHOIS for {domain}")
        
        # Query WHOIS data
        w = whois.whois(domain)
        
        # Extract registrar information
        registrar_info = {
            "name": getattr(w, 'registrar', 'Unknown'),
            "url": getattr(w, 'registrar_url', ''),
            "ianaId": getattr(w, 'registrar_id', None),
            "abuseContact": getattr(w, 'abuse_contact_email', ''),
            "phone": getattr(w, 'abuse_contact_phone', '')
        }
        
        # Extract date information
        creation_date = get_first_date(getattr(w, 'creation_date', None))
        updated_date = get_first_date(getattr(w, 'last_updated', None))
        expiry_date = get_first_date(getattr(w, 'expiration_date', None))
        
        dates_info = {
            "created": format_date(creation_date),
            "updated": format_date(updated_date),
            "expires": format_date(expiry_date),
            "daysUntilExpiry": calculate_days_until_expiry(expiry_date)
        }
        
        # Extract status information
        status_info = getattr(w, 'status', [])
        if isinstance(status_info, list) and status_info:
            status_info = status_info[0]
        
        # Extract name servers
        name_servers = getattr(w, 'name_servers', [])
        if name_servers:
            # Ensure it's a list
            if not isinstance(name_servers, list):
                name_servers = [name_servers]
            # Filter out None values
            name_servers = [ns for ns in name_servers if ns]
        
        # Extract registrant information
        registrant_info = {
            "name": getattr(w, 'registrant_name', ''),
            "organization": getattr(w, 'registrant_org', ''),
            "country": getattr(w, 'registrant_country', ''),
            "state": getattr(w, 'registrant_state', ''),
            "email": getattr(w, 'registrant_email', ''),
            "phone": getattr(w, 'registrant_phone', '')
        }
        
        # Extract DNSSEC information
        dnssec_info = getattr(w, 'dnssec', 'unsigned')
        
        # Get raw WHOIS data
        raw_whois = str(w)
        
        results = {
            "status": "success",
            "domain": domain,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "registrar": registrar_info,
                "dates": dates_info,
                "status": status_info,
                "nameServers": name_servers,
                "registrant": registrant_info,
                "dnssec": dnssec_info,
                "rawWhois": raw_whois
            }
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
    
    # Always output the results, even if there was an error
    print(f"results={json.dumps(results)}")
    return results

if __name__ == "__main__":
    target_domain = os.environ.get("TARGET_DOMAIN")
    if not target_domain:
        print("ERROR: TARGET_DOMAIN environment variable not set.")
        print(f"results={json.dumps({'status': 'error', 'message': 'TARGET_DOMAIN environment variable not set.'})}")
        sys.exit(1)
        
    whois_results = lookup_whois(target_domain)
    
    # The results are already printed in the function
