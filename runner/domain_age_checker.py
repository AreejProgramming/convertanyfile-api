# File: runner/domain_age_checker.py

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

def check_domain_age(domain):
    """
    Checks the age of a domain by querying WHOIS data.
    Returns detailed information about the domain registration.
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Clean up the domain input
    domain = extract_domain_from_url(domain)
    
    print(f"Starting domain age check for: {domain}")
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "Domain age check failed to start.",
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
        
        # Extract creation date using the helper function
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
        now = datetime.now()
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        if creation_date.tzinfo is not None:
            creation_date = creation_date.replace(tzinfo=None)
        
        # Calculate domain age
        age_delta = now - creation_date
        
        days = age_delta.days
        years, remaining_days = divmod(days, 365)
        months, days = divmod(remaining_days, 30)
        
        # Get expiry date if available
        expiry_date = None
        if hasattr(w, 'expiration_date') and w.expiration_date:
            expiry_date = get_first_date(w.expiration_date)
            if isinstance(expiry_date, str):
                try:
                    expiry_date = datetime.strptime(expiry_date.split(' ')[0], '%Y-%m-%d')
                    if expiry_date.tzinfo is not None:
                        expiry_date = expiry_date.replace(tzinfo=None)
                except ValueError:
                    expiry_date = None
        
        results = {
            "status": "success",
            "domain": domain,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "creation_date": creation_date.strftime('%Y-%m-%d'),
                "age_years": years,
                "age_months": months,
                "age_days": days,
                "registrar": getattr(w, 'registrar', 'Unknown'),
                "expiry_date": expiry_date.strftime('%Y-%m-%d') if expiry_date else None
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
        
    domain_results = check_domain_age(target_domain)
    
    # The results are already printed in the function
