# File: runner/domain_expiry_checker.py

import os
import json
import time
import sys
import uuid
import whois
import re
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

def get_expiry_date(expiry_date_field):
    """
    Helper function to extract and parse the expiry date
    """
    if not expiry_date_field:
        return None
    
    expiry_date = get_first_date(expiry_date_field)
    
    if not expiry_date:
        return None
        
    # Parse the date
    if isinstance(expiry_date, str):
        # Try to parse different date formats
        try:
            expiry_date = datetime.strptime(expiry_date.split(' ')[0], '%Y-%m-%d')
        except ValueError:
            try:
                expiry_date = datetime.strptime(expiry_date, '%d-%b-%Y')
            except ValueError:
                try:
                    expiry_date = datetime.strptime(expiry_date, '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    raise ValueError(f"Could not parse expiry date: {expiry_date}")
    
    # Make it timezone-naive to avoid issues
    if expiry_date.tzinfo is not None:
        expiry_date = expiry_date.replace(tzinfo=None)
        
    return expiry_date

def check_domain_expiry(domain):
    """
    Checks the expiry date of a domain by querying WHOIS data.
    Returns detailed information about the domain registration.
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Clean up the domain input
    domain = extract_domain_from_url(domain)
    
    print(f"Starting domain expiry check for: {domain}")
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "Domain expiry check failed to start.",
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
        
        # Extract creation date
        creation_date = None
        
        # Try different possible fields for creation date
        if hasattr(w, 'creation_date') and w.creation_date:
            creation_date = get_first_date(w.creation_date)
        elif hasattr(w, 'created') and w.created:
            creation_date = get_first_date(w.created)
        elif hasattr(w, 'registration_date') and w.registration_date:
            creation_date = get_first_date(w.registration_date)
        
        if not creation_date:
            raise ValueError("Could not determine domain creation date")
            
        # Parse the date
        if isinstance(creation_date, str):
            # Try to parse different date formats
            try:
                creation_date = datetime.strptime(creation_date.split(' ')[0], '%Y-%m-%d')
            except ValueError:
                try:
                    creation_date = datetime.strptime(creation_date, '%d-%b-%Y')
                except ValueError:
                    try:
                        creation_date = datetime.strptime(creation_date, '%Y-%m-%dT%H:%M:%SZ')
                    except ValueError:
                        raise ValueError(f"Could not parse creation date: {creation_date}")
        
        # Make both datetimes timezone-naive to avoid subtraction issues
        if creation_date.tzinfo is not None:
            creation_date = creation_date.replace(tzinfo=None)
        
        # Get expiry date
        expiry_date = None
        if hasattr(w, 'expiration_date') and w.expiration_date:
            expiry_date = get_expiry_date(w.expiration_date)
        
        # Calculate days until expiry
        now = datetime.now()
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)
            
        days_until_expiry = None
        if expiry_date:
            days_until_expiry = (expiry_date - now).days
        
        # Get registrar
        registrar = getattr(w, 'registrar', 'Unknown')
        
        # Get status
        status = 'ok'
        if hasattr(w, 'status'):
            status = get_first_date(w.status)
        
        # Get nameservers
        nameservers = []
        if hasattr(w, 'name_servers'):
            nameservers = w.name_servers
        
        results = {
            "status": "success",
            "domain": domain,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "creation_date": creation_date.strftime('%Y-%m-%d'),
                "expiry_date": expiry_date.strftime('%Y-%m-%d') if expiry_date else None,
                "days_until_expiry": days_until_expiry,
                "registrar": registrar,
                "status": status,
                "nameservers": nameservers
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
        
    domain_results = check_domain_expiry(target_domain)
    
    # The results are already printed in the function
