import os
import json
import time
import sys
import re
import ssl
import socket
from datetime import datetime
from urllib.parse import urlparse
import uuid

def generate_session_id():
    return str(uuid.uuid4())

def validate_domain(domain):
    """
    Validate if input is a valid domain name or URL
    """
    # Remove protocol if present
    if domain.startswith(('http://', 'https://')):
        domain = domain.split('://', 1)[1]
    
    # Remove path if present
    if '/' in domain:
        domain = domain.split('/', 1)[0]
    
    # Domain name regex
    domain_regex = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$'
    # IPv4 regex
    ip_regex = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    
    return re.match(domain_regex, domain) or re.match(ip_regex, domain)

def get_ssl_certificate_info(domain, port=443, timeout=10):
    """
    Get SSL certificate information for a domain
    """
    try:
        # Create socket connection
        context = ssl.create_default_context()
        
        # Measure connection time
        start_time = time.time()
        
        # Connect to the server
        with socket.create_connection((domain, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                connection_time = (time.time() - start_time) * 1000  # milliseconds
                
                # Extract certificate information
                cert_info = {
                    'subject': dict(x[0] for x in cert['subject']),
                    'issuer': dict(x[0] for x in cert['issuer']),
                    'version': cert['version'],
                    'serialNumber': cert['serialNumber'],
                    'notBefore': cert['notBefore'],
                    'notAfter': cert['notAfter'],
                    'subjectAltName': cert.get('subjectAltName', []),
                    'connectionTime': connection_time
                }
                
                # Parse dates
                not_before = datetime.strptime(cert_info['notBefore'], '%b %d %H:%M:%S %Y %Z')
                not_after = datetime.strptime(cert_info['notAfter'], '%b %d %H:%M:%S %Y %Z')
                
                # Calculate days until expiration
                days_until_expiry = (not_after - datetime.now()).days
                
                # Get certificate chain
                cert_chain = ssock.get_verified_chain()
                
                return {
                    'domain': domain,
                    'port': port,
                    'valid': True,
                    'subject': cert_info['subject'].get('commonName', 'N/A'),
                    'issuer': cert_info['issuer'].get('organizationName', 'N/A'),
                    'version': cert_info['version'],
                    'serialNumber': cert_info['serialNumber'],
                    'issuedDate': cert_info['notBefore'],
                    'expiryDate': cert_info['notAfter'],
                    'daysUntilExpiry': days_until_expiry,
                    'subjectAltName': cert_info['subjectAltName'],
                    'connectionTime': connection_time,
                    'chainLength': len(cert_chain) if cert_chain else 0,
                    'isSelfSigned': cert_info['issuer'] == cert_info['subject'],
                    'signatureAlgorithm': cert.get('signatureAlgorithm', 'Unknown'),
                    'publicKeySize': cert.get('subjectPublicKeyInfo', {}).get('publicKey', {}).get('size', 0)
                }
                
    except socket.gaierror as e:
        return {
            'domain': domain,
            'port': port,
            'valid': False,
            'error': f"DNS resolution failed: {str(e)}",
            'errorType': 'DNS_ERROR'
        }
    except socket.timeout:
        return {
            'domain': domain,
            'port': port,
            'valid': False,
            'error': "Connection timeout",
            'errorType': 'TIMEOUT_ERROR'
        }
    except ssl.SSLCertVerificationError as e:
        return {
            'domain': domain,
            'port': port,
            'valid': False,
            'error': f"Certificate verification failed: {str(e)}",
            'errorType': 'CERT_ERROR'
        }
    except ConnectionRefusedError:
        return {
            'domain': domain,
            'port': port,
            'valid': False,
            'error': "Connection refused",
            'errorType': 'CONNECTION_ERROR'
        }
    except Exception as e:
        return {
            'domain': domain,
            'port': port,
            'valid': False,
            'error': f"Unexpected error: {str(e)}",
            'errorType': 'UNKNOWN_ERROR'
        }

def check_ssl_certificate(domain):
    """
    Main function to check SSL certificate
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting SSL certificate check for: {domain}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Checking SSL certificate...",
        "session_id": session_id
    }
    
    try:
        # Validate and clean domain
        if not domain or not validate_domain(domain):
            raise ValueError("Invalid domain name or URL format")
        
        # Clean domain (remove protocol and path)
        clean_domain = domain.strip()
        if clean_domain.startswith(('http://', 'https://')):
            clean_domain = clean_domain.split('://', 1)[1]
        if '/' in clean_domain:
            clean_domain = clean_domain.split('/', 1)[0]
        
        print(f"Cleaned domain: {clean_domain}")
        
        # Check SSL certificate
        print(f"Checking SSL certificate for {clean_domain}...")
        cert_data = get_ssl_certificate_info(clean_domain)
        
        # Add additional analysis
        if cert_data.get('valid'):
            # Check if certificate is expiring soon
            if cert_data['daysUntilExpiry'] < 30:
                cert_data['expiryWarning'] = 'Certificate expires soon'
            elif cert_data['daysUntilExpiry'] < 7:
                cert_data['expiryWarning'] = 'Certificate expires very soon'
            
            # Check if it's a self-signed certificate
            if cert_data['isSelfSigned']:
                cert_data['warning'] = 'Self-signed certificate'
            
            # Check key size
            if cert_data['publicKeySize'] < 2048:
                cert_data['warning'] = 'Weak key size detected'
        
        # Create final results
        results = {
            "status": "success",
            "domain": clean_domain,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": cert_data
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
    domain = os.environ.get("DOMAIN")
    if not domain:
        print("ERROR: DOMAIN environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "DOMAIN environment variable not set.",
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
        
    ssl_results = check_ssl_certificate(domain)
    
    # The results are already printed in the function
    sys.exit(0)
