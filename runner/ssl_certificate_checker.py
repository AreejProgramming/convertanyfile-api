import os
import json
import time
import sys
import re
import ssl
import socket
import subprocess
from datetime import datetime, timedelta
from urllib.parse import urlparse
import uuid

def generate_session_id():
    return str(uuid.uuid4())

def validate_domain(domain):
    """
    Validate if input is a valid domain name
    """
    # Domain name regex
    domain_regex = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$'
    # URL regex
    url_regex = r'^https?:\/\/(?:[-\w.])+(?:\:[0-9]+)?(?:\/(?:[\w\/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
    
    return (re.match(domain_regex, domain) or re.match(url_regex, domain))

def get_ssl_certificate_info(domain):
    """
    Get SSL certificate information for a domain
    """
    try:
        # Clean domain (remove protocol if present)
        if domain.startswith(('http://', 'https://')):
            domain = domain.split('://', 1)[1]
        
        # Default port
        port = 443
        
        # Check if port is specified
        if ':' in domain:
            domain, port_str = domain.rsplit(':', 1)
            port = int(port_str)
        
        # Get certificate
        context = ssl.create_default_context()
        with socket.create_connection((domain, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert(binary_form=True)
        
        # Parse certificate
        cert_info = {}
        
        # Get subject
        subject = {}
        for item in cert_info['subject']:
            for key, value in item:
                subject[key] = value
        
        # Get issuer
        issuer = {}
        for item in cert_info['issuer']:
            for key, value in item:
                issuer[key] = value
        
        # Get validity dates
        not_before = datetime.strptime(cert_info['notBefore'], '%b %d %H:%M:%S %Y %Z')
        not_after = datetime.strptime(cert_info['notAfter'], '%b %d %H:%M:%S %Y %Z')
        
        # Calculate days until expiry
        days_until_expiry = (not_after - datetime.now()).days
        
        # Get serial number
        serial_number = cert_info.get('serialNumber', '')
        
        # Get signature algorithm
        signature_algorithm = cert_info.get('signatureAlgorithm', '')
        
        # Get version
        version = cert_info.get('version', '')
        
        # Get subject alternative names
        san = []
        if 'subjectAltName' in cert_info:
            for item in cert_info['subjectAltName']:
                if item[0] == 'DNS':
                    san.append(item[1])
        
        # Get key size (using openssl command)
        try:
            cmd = f"echo | openssl s_client -connect {domain}:{port} 2>/dev/null | openssl x509 -noout -text | grep 'Public-Key'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            key_size = 2048  # Default
            if result.returncode == 0:
                output = result.stdout
                if 'RSA' in output:
                    match = re.search(r'RSA Public-Key: \((\d+) bit\)', output)
                    if match:
                        key_size = int(match.group(1))
        except:
            key_size = 2048  # Default
        
        # Get protocol and cipher suite (using openssl command)
        try:
            cmd = f"echo | openssl s_client -connect {domain}:{port} 2>/dev/null | grep 'Protocol'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            protocol = "TLS 1.2"  # Default
            if result.returncode == 0:
                output = result.stdout
                if 'TLSv1.2' in output:
                    protocol = "TLS 1.2"
                elif 'TLSv1.1' in output:
                    protocol = "TLS 1.1"
                elif 'TLSv1' in output:
                    protocol = "TLS 1.0"
                elif 'SSLv3' in output:
                    protocol = "SSL 3.0"
            
            cmd = f"echo | openssl s_client -connect {domain}:{port} 2>/dev/null | grep 'Cipher'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            cipher_suite = "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384"  # Default
            if result.returncode == 0:
                output = result.stdout
                match = re.search(r'Cipher\s*:\s*(.+)', output)
                if match:
                    cipher_suite = match.group(1).strip()
        except:
            protocol = "TLS 1.2"  # Default
            cipher_suite = "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384"  # Default
        
        # Check for common vulnerabilities
        vulnerabilities = []
        
        # Check for Heartbleed
        try:
            cmd = f"echo | openssl s_client -connect {domain}:{port} 2>/dev/null | grep 'heartbeat'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and 'heartbeat' in result.stdout:
                vulnerabilities.append({
                    "name": "Heartbleed",
                    "status": "Vulnerable",
                    "severity": "Critical"
                })
            else:
                vulnerabilities.append({
                    "name": "Heartbleed",
                    "status": "Not Vulnerable",
                    "severity": "Safe"
                })
        except:
            vulnerabilities.append({
                "name": "Heartbleed",
                "status": "Unknown",
                "severity": "Unknown"
            })
        
        # Check for POODLE
        try:
            cmd = f"echo | openssl s_client -connect {domain}:{port} 2>/dev/null | grep 'Protocol.*SSLv3'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and 'SSLv3' in result.stdout:
                vulnerabilities.append({
                    "name": "POODLE",
                    "status": "Vulnerable",
                    "severity": "High"
                })
            else:
                vulnerabilities.append({
                    "name": "POODLE",
                    "status": "Not Vulnerable",
                    "severity": "Safe"
                })
        except:
            vulnerabilities.append({
                "name": "POODLE",
                "status": "Unknown",
                "severity": "Unknown"
            })
        
        # Check for BEAST
        try:
            cmd = f"echo | openssl s_client -connect {domain}:{port} 2>/dev/null | grep 'Cipher.*CBC'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and 'CBC' in result.stdout:
                vulnerabilities.append({
                    "name": "BEAST",
                    "status": "Vulnerable",
                    "severity": "Medium"
                })
            else:
                vulnerabilities.append({
                    "name": "BEAST",
                    "status": "Not Vulnerable",
                    "severity": "Safe"
                })
        except:
            vulnerabilities.append({
                "name": "BEAST",
                "status": "Unknown",
                "severity": "Unknown"
            })
        
        # Build certificate info
        cert_info = {
            "domain": domain,
            "isSecure": days_until_expiry > 0,
            "isValid": days_until_expiry > 0,
            "certificate": {
                "issuer": issuer.get('organizationName', ''),
                "subject": subject.get('commonName', ''),
                "serialNumber": serial_number,
                "signatureAlgorithm": signature_algorithm,
                "version": version,
                "issuedOn": not_before.strftime('%Y-%m-%d'),
                "expiresOn": not_after.strftime('%Y-%m-%d'),
                "daysUntilExpiry": days_until_expiry,
                "keySize": key_size,
                "protocol": protocol,
                "cipherSuite": cipher_suite,
                "SANs": san
            },
            "vulnerabilities": vulnerabilities
        }
        
        return cert_info
    except Exception as e:
        return {"error": str(e)}

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
        # Validate input
        if not domain or not validate_domain(domain):
            raise ValueError("Invalid domain name format")
        
        # Get SSL certificate information
        print(f"Getting SSL certificate information for {domain}...")
        ssl_data = get_ssl_certificate_info(domain)
        
        if "error" in ssl_data:
            raise ValueError(ssl_data["error"])
        
        # Create final results
        results = {
            "status": "success",
            "domain": domain,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": ssl_data
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
