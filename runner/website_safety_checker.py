import os
import json
import time
import sys
import re
from datetime import datetime
from urllib.parse import urlparse

def generate_session_id():
    return str(int(time.time() * 1000))

def extract_domain(url):
    """Extract domain from URL"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        parsed = urlparse(url)
        return parsed.hostname.lower()
    except:
        return url.lower()

# Suspicious TLDs and patterns
SUSPICIOUS_TLDS = [
    '.tk', '.ml', '.ga', '.cf', '.pw', '.top', '.click', '.download', '.win',
    '.stream', '.loan', '.review', '.trade', '.accountant', '.cricket', '.science'
]

MALICIOUS_PATTERNS = [
    r'paypal-secure',
    r'microsoft-security',
    r'google-verify',
    r'amazon-prime',
    r'facebook-login',
    r'apple-id',
    r'bank-america',
    r'chase-secure',
    r'wellsfargo-online',
    r'irs-gov'
]

TYPOSQUAT_PATTERNS = [
    {'original': 'google', 'typos': ['g00gle', 'googel', 'gogle', 'googl', 'googgle']},
    {'original': 'facebook', 'typos': ['faceb00k', 'faceboook', 'facbook', 'fb.com']},
    {'original': 'amazon', 'typos': ['amaz0n', 'amzon', 'amazin', 'arnazon']},
    {'original': 'microsoft', 'typos': ['microsofts', 'micr0soft', 'microsft']},
    {'original': 'apple', 'typos': ['appl3', 'aple', 'apples']}
]

def check_https(url):
    """Check if URL uses HTTPS"""
    return url.startswith('https://')

def check_domain_length(domain):
    """Check domain length"""
    length = len(domain)
    if length > 50:
        return {'risk': 'high', 'message': 'Unusually long domain name'}
    elif length > 30:
        return {'risk': 'medium', 'message': 'Long domain name'}
    else:
        return {'risk': 'low', 'message': 'Normal domain length'}

def check_tld(domain):
    """Check for suspicious TLD"""
    tld = domain[domain.lastIndexOf('.'):] if '.' in domain else ''
    if tld in SUSPICIOUS_TLDS:
        return {'risk': 'high', 'message': f'Suspicious TLD: {tld}'}
    else:
        return {'risk': 'low', 'message': 'Common TLD'}

def check_malicious_patterns(url, domain):
    """Check for malicious patterns"""
    for pattern in MALICIOUS_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE) or re.search(pattern, domain, re.IGNORECASE):
            return {
                'detected': True,
                'pattern': pattern,
                'message': f'Detected suspicious pattern: {pattern}'
            }
    return {'detected': False}

def check_typosquatting(domain):
    """Check for typosquatting"""
    for item in TYPOSQUAT_PATTERNS:
        for typo in item['typos']:
            if typo in domain and item['original'] not in domain:
                return {
                    'detected': True,
                    'original': item['original'],
                    'typo': typo,
                    'message': f'Possible typosquatting: {typo} instead of {item["original"]}'
                }
    return {'detected': False}

def check_special_chars(domain):
    """Check for special characters"""
    special_chars = re.findall(r'[!@#$%^&*(),.?":{}|<>]', domain)
    if special_chars:
        return {
            'detected': True,
            'chars': special_chars,
            'message': f'Contains unusual characters: {", ".join(special_chars)}'
        }
    return {'detected': False}

def check_subdomain_abuse(domain):
    """Check for subdomain abuse"""
    parts = domain.split('.')
    if len(parts) > 4:
        return {'risk': 'high', 'message': 'Excessive subdomains'}
    elif len(parts) > 3:
        return {'risk': 'medium', 'message': 'Multiple subdomains'}
    else:
        return {'risk': 'low', 'message': 'Normal subdomain structure'}

def check_ip_address(domain):
    """Check if domain is an IP address"""
    ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    if re.match(ip_pattern, domain):
        return {'detected': True, 'message': 'Using IP address instead of domain name'}
    return {'detected': False}

def calculate_safety_score(checks):
    """Calculate overall safety score"""
    score = 100
    
    # HTTPS check
    if not checks['https']['secure']:
        score -= 20
    
    # Domain length
    if checks['domainLength']['risk'] == 'high':
        score -= 15
    elif checks['domainLength']['risk'] == 'medium':
        score -= 5
    
    # TLD check
    if checks['tld']['risk'] == 'high':
        score -= 25
    elif checks['tld']['risk'] == 'medium':
        score -= 10
    
    # Malicious patterns
    if checks['maliciousPatterns']['detected']:
        score -= 40
    
    # Typosquatting
    if checks['typosquatting']['detected']:
        score -= 30
    
    # Special characters
    if checks['specialChars']['detected']:
        score -= 20
    
    # Subdomain abuse
    if checks['subdomainAbuse']['risk'] == 'high':
        score -= 15
    elif checks['subdomainAbuse']['risk'] == 'medium':
        score -= 5
    
    # IP address
    if checks['ipAddress']['detected']:
        score -= 25
    
    return max(0, min(100, score))

def check_website_safety(url):
    """Main function to check website safety"""
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    domain = extract_domain(url)
    
    print(f"Starting safety check for: {url}")
    print(f"Domain: {domain}")
    print(f"Session ID: {session_id}")
    
    # Perform all checks
    checks = {
        'https': {
            'secure': check_https(url),
            'message': 'Uses secure HTTPS' if check_https(url) else 'Not using HTTPS'
        },
        'domainLength': check_domain_length(domain),
        'tld': check_tld(domain),
        'maliciousPatterns': check_malicious_patterns(url, domain),
        'typosquatting': check_typosquatting(domain),
        'specialChars': check_special_chars(domain),
        'subdomainAbuse': check_subdomain_abuse(domain),
        'ipAddress': check_ip_address(domain)
    }
    
    # Calculate safety score
    score = calculate_safety_score(checks)
    is_safe = score >= 70
    
    # Determine reputation
    if score >= 90:
        reputation = 'Excellent'
    elif score >= 70:
        reputation = 'Good'
    elif score >= 40:
        reputation = 'Poor'
    else:
        reputation = 'Very Poor'
    
    # Determine risk level
    if score < 30:
        risk_level = 'Very High'
        risk_color = '#991b1b'
    elif score < 50:
        risk_level = 'High'
        risk_color = '#ef4444'
    elif score < 70:
        risk_level = 'Medium'
        risk_color = '#f59e0b'
    else:
        risk_level = 'Low'
        risk_color = '#10b981'
    
    # Create detailed results
    results = {
        'url': url,
        'domain': domain,
        'isSafe': is_safe,
        'score': score,
        'reputation': reputation,
        'riskLevel': risk_level,
        'riskColor': risk_color,
        'lastScanned': datetime.now().isoformat(),
        'checks': checks,
        'details': {
            'httpsStatus': checks['https']['message'],
            'domainAnalysis': f'{len(domain)} characters - {checks["domainLength"]["message"]}',
            'tldInfo': checks['tld']['message'],
            'maliciousPatterns': checks['maliciousPatterns']['message'] if checks['maliciousPatterns']['detected'] else 'No malicious patterns detected',
            'typosquatting': checks['typosquatting']['message'] if checks['typosquatting']['detected'] else 'No typosquatting detected',
            'specialCharacters': checks['specialChars']['message'] if checks['specialChars']['detected'] else 'No unusual characters',
            'subdomainInfo': checks['subdomainAbuse']['message'],
            'ipAddressInfo': checks['ipAddress']['message'] if checks['ipAddress']['detected'] else 'Using proper domain name'
        },
        'warnings': [
            not checks['https']['secure'] and 'Not using HTTPS',
            checks['maliciousPatterns']['detected'] and 'Suspicious pattern detected',
            checks['typosquatting']['detected'] and 'Possible typosquatting',
            checks['specialChars']['detected'] and 'Contains unusual characters',
            checks['ipAddress']['detected'] and 'Using IP address',
            checks['tld']['risk'] == 'high' and 'Suspicious TLD detected',
            checks['domainLength']['risk'] == 'high' and 'Unusually long domain'
        ]
    }
    
    # Filter out None values from warnings
    results['warnings'] = [w for w in results['warnings'] if w]
    
    return results

def main():
    url = os.environ.get("URL")
    if not url:
        print("ERROR: URL environment variable not set.")
        error_result = {
            "status": "error",
            "message": "URL environment variable not set.",
            "session_id": os.environ.get("SESSION_ID", "unknown")
        }
        
        with open('results.json', 'w') as f:
            json.dump(error_result, f)
        print(json.dumps(error_result))
        sys.exit(1)
    
    try:
        # Check website safety
        safety_results = check_website_safety(url)
        
        # Create final results
        results = {
            "status": "success",
            "timestamp": time.time(),
            "session_id": os.environ.get("SESSION_ID", generate_session_id()),
            "data": safety_results
        }
        
        # Write results to file
        with open('results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print("Safety check completed successfully")
        print(f"Results written to results.json")
        print(json.dumps(results))
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        error_result = {
            "status": "error",
            "message": str(e),
            "session_id": os.environ.get("SESSION_ID", "unknown")
        }
        
        with open('results.json', 'w') as f:
            json.dump(error_result, f)
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()
