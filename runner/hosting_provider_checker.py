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
        # Remove www. if present
        if hostname.startswith('www.'):
            hostname = hostname[4:]
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except Exception as e:
        print(f"Error getting IP address: {str(e)}")
        return None

def get_ip_info(ip_address):
    """
    Get information about an IP address using ip-api.com (free service)
    """
    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}?fields=status,message,country,regionName,city,zip,isp,org,as,reverse,mobile,proxy,hosting", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                return {
                    "ip": ip_address,
                    "hostname": data.get("reverse", ""),
                    "city": data.get("city", "Unknown"),
                    "region": data.get("regionName", "Unknown"),
                    "country": data.get("country", "Unknown"),
                    "loc": f"{data.get('lat', '')},{data.get('lon', '')}",
                    "org": data.get("org", ""),
                    "postal": data.get("zip", ""),
                    "timezone": data.get("timezone", ""),
                    "as": data.get("as", ""),
                    "mobile": data.get("mobile", False),
                    "proxy": data.get("proxy", False),
                    "hosting": data.get("hosting", False)
                }
        return None
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

def get_server_headers(url):
    """
    Get server headers from HTTP request
    """
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        return {
            "server": response.headers.get('Server', ''),
            "powered_by": response.headers.get('X-Powered-By', ''),
            "via": response.headers.get('Via', ''),
            "cdn": response.headers.get('CDN', '') or response.headers.get('X-Cache', ''),
            "status_code": response.status_code
        }
    except Exception as e:
        print(f"Error getting server headers: {str(e)}")
        return {}

def detect_hosting_provider_real(org, hostname, as_info, nameservers, server_headers):
    """
    Real hosting provider detection using comprehensive databases and patterns
    """
    
    # Comprehensive hosting provider database with ASN and IP ranges
    hosting_providers = {
        # Major Cloud Providers
        "aws": {
            "patterns": ["amazon", "aws", "amazon.com", "amazon web services"],
            "asns": ["AS16509", "AS14618", "AS8987", "AS16591"],
            "nameservers": ["awsdns", "amazonaws.com"],
            "type": "Cloud Hosting",
            "features": ["EC2", "S3", "Global Infrastructure"],
            "price_range": "Pay-as-you-go"
        },
        "google_cloud": {
            "patterns": ["google", "gcp", "google cloud", "google llc"],
            "asns": ["AS15169", "AS396982", "AS45566"],
            "nameservers": ["googledomains.com", "google.com"],
            "type": "Cloud Hosting", 
            "features": ["Compute Engine", "Cloud Storage", "Global Network"],
            "price_range": "Pay-as-you-go"
        },
        "azure": {
            "patterns": ["microsoft", "azure", "msft", "microsoft corporation"],
            "asns": ["AS8075", "AS8069", "AS53581"],
            "nameservers": ["azure-dns.com", "azure-dns.net"],
            "type": "Cloud Hosting",
            "features": ["Virtual Machines", "Azure Storage", "Global Infrastructure"],
            "price_range": "Pay-as-you-go"
        },
        # CDN/Edge Providers
        "cloudflare": {
            "patterns": ["cloudflare", "cloudflare inc"],
            "asns": ["AS13335", "AS209242"],
            "nameservers": ["cloudflare.com"],
            "type": "CDN/Edge Platform",
            "features": ["DDoS Protection", "CDN", "DNS"],
            "price_range": "Free - Enterprise"
        },
        "fastly": {
            "patterns": ["fastly", "fastly inc"],
            "asns": ["AS54113"],
            "nameservers": ["fastly.net"],
            "type": "CDN/Edge Platform",
            "features": ["CDN", "Edge Computing", "Security"],
            "price_range": "Pay-as-you-go"
        },
        "akamai": {
            "patterns": ["akamai", "akamai technologies"],
            "asns": ["AS20940", "AS20941"],
            "nameservers": ["akamai.com", "akadns.net"],
            "type": "CDN/Edge Platform",
            "features": ["CDN", "Security", "Performance"],
            "price_range": "Enterprise"
        },
        # Hosting Companies
        "digitalocean": {
            "patterns": ["digitalocean", "digital ocean"],
            "asns": ["AS14061"],
            "nameservers": ["digitalocean.com"],
            "type": "Cloud VPS",
            "features": ["Droplets", "Kubernetes", "Spaces"],
            "price_range": "$4 - $960/month"
        },
        "linode": {
            "patterns": ["linode", "akamai technologies"],
            "asns": ["AS63949"],
            "nameservers": ["linode.com", "linode.net"],
            "type": "Cloud VPS",
            "features": ["Linodes", "Kubernetes", "Object Storage"],
            "price_range": "$5 - $160/month"
        },
        "vultr": {
            "patterns": ["vultr", "choopa"],
            "asns": ["AS20473"],
            "nameservers": ["vultr.com"],
            "type": "Cloud VPS",
            "features": ["Cloud Compute", "Bare Metal", "Kubernetes"],
            "price_range": "$2.50 - $500/month"
        },
        "hetzner": {
            "patterns": ["hetzner", "hetzner online"],
            "asns": ["AS24940", "AS24961"],
            "nameservers": ["hetzner.com"],
            "type": "Dedicated/VPS",
            "features": ["Dedicated Servers", "Cloud VPS", "Storage Boxes"],
            "price_range": "€2.49 - €160+/month"
        },
        # Shared Hosting
        "bluehost": {
            "patterns": ["bluehost", "new dream network"],
            "asns": ["AS26496"],
            "nameservers": ["bluehost.com"],
            "type": "Shared Hosting",
            "features": ["WordPress Hosting", "Free SSL", "Site Builder"],
            "price_range": "$2.95 - $13.95/month"
        },
        "hostgator": {
            "patterns": ["hostgator", "endurance international group"],
            "asns": ["AS26496"],
            "nameservers": ["hostgator.com"],
            "type": "Shared Hosting",
            "features": ["Unlimited Bandwidth", "Free Domain", "Website Builder"],
            "price_range": "$2.75 - $5.95/month"
        },
        "godaddy": {
            "patterns": ["godaddy", "go daddy"],
            "asns": ["AS26496"],
            "nameservers": ["godaddy.com"],
            "type": "Shared Hosting",
            "features": ["Easy Setup", "Microsoft 365", "Daily Backups"],
            "price_range": "$1.99 - $24.99/month"
        },
        "siteground": {
            "patterns": ["siteground", "sg hosting"],
            "asns": ["AS39556"],
            "nameservers": ["siteground.com"],
            "type": "Managed Hosting",
            "features": ["SuperCacher", "Daily Backups", "Free CDN"],
            "price_range": "$3.99 - $10.69/month"
        },
        # Static Site Hosting
        "github": {
            "patterns": ["github", "github pages"],
            "asns": ["AS36459"],
            "nameservers": ["github.com"],
            "type": "Static Site Hosting",
            "features": ["Free Hosting", "Custom Domains", "SSL"],
            "price_range": "Free - $21+/month"
        },
        "netlify": {
            "patterns": ["netlify", "netlify inc"],
            "asns": ["AS13335"],  # Often uses Cloudflare
            "nameservers": ["netlify.com"],
            "type": "Static Site Hosting",
            "features": ["CI/CD", "Serverless Functions", "Global CDN"],
            "price_range": "Free - $19+/month"
        },
        "vercel": {
            "patterns": ["vercel", "zeit"],
            "asns": ["AS13335"],  # Often uses Cloudflare
            "nameservers": ["vercel.com"],
            "type": "Static Site Hosting",
            "features": ["Serverless Functions", "Global CDN", "Preview Deployments"],
            "price_range": "Free - $20+/month"
        }
    }
    
    # Search in all available data sources
    search_terms = []
    if org:
        search_terms.append(org.lower())
    if hostname:
        search_terms.append(hostname.lower())
    if as_info:
        search_terms.append(as_info.lower())
    search_terms.extend([ns.lower() for ns in nameservers])
    if server_headers:
        search_terms.extend([
            server_headers.get('server', '').lower(),
            server_headers.get('powered_by', '').lower(),
            server_headers.get('via', '').lower(),
            server_headers.get('cdn', '').lower()
        ])
    
    # Check each provider
    for provider_key, provider_data in hosting_providers.items():
        # Check patterns
        for term in search_terms:
            if any(pattern in term for pattern in provider_data["patterns"]):
                return {
                    "name": provider_key.replace("_", " ").title(),
                    "type": provider_data["type"],
                    "features": provider_data["features"],
                    "priceRange": provider_data["price_range"]
                }
        
        # Check ASNs
        for term in search_terms:
            if any(asn in term for asn in provider_data["asns"]):
                return {
                    "name": provider_key.replace("_", " ").title(),
                    "type": provider_data["type"],
                    "features": provider_data["features"],
                    "priceRange": provider_data["price_range"]
                }
        
        # Check nameservers
        for ns in nameservers:
            if any(ns_pattern in ns.lower() for ns_pattern in provider_data["nameservers"]):
                return {
                    "name": provider_key.replace("_", " ").title(),
                    "type": provider_data["type"],
                    "features": provider_data["features"],
                    "priceRange": provider_data["price_range"]
                }
    
    # If no match found, return the actual organization name
    if org and org.strip():
        return {
            "name": org,
            "type": "Hosting Provider",
            "features": ["Web Hosting Services"],
            "priceRange": "Varies"
        }
    
    # Final fallback
    return {
        "name": "Unknown",
        "type": "Unknown",
        "features": [],
        "priceRange": "Unknown"
    }

def get_real_performance_metrics(url):
    """
    Get real performance metrics by actually measuring
    """
    try:
        # Measure response time
        start_time = time.time()
        response = requests.get(url, timeout=10)
        response_time = (time.time() - start_time) * 1000  # milliseconds
        
        return {
            "response_time": f"{response_time:.2f}ms",
            "status_code": response.status_code,
            "content_length": len(response.content)
        }
    except Exception as e:
        return {
            "response_time": "Unknown",
            "status_code": "Error",
            "content_length": 0
        }

def detect_hosting_provider(url):
    """
    Detect the hosting provider of a website with REAL data
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Format the URL
    url = format_url(url)
    
    print(f"Starting hosting provider check for: {url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Analyzing hosting provider...",
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
        
        # Get server headers
        server_headers = get_server_headers(url)
        
        # Extract hosting provider information
        org = ip_info.get("org", "")
        hostname = ip_info.get("hostname", "")
        as_info = ip_info.get("as", "")
        
        # REAL hosting provider detection
        provider = detect_hosting_provider_real(org, hostname, as_info, nameservers, server_headers)
        
        # Get REAL performance metrics
        performance_metrics = get_real_performance_metrics(url)
        
        # Generate hosting details with real data where possible
        hosting_details = {
            "uptime": "Unknown",  # Would need historical data
            "responseTime": performance_metrics["response_time"],
            "plan": provider["type"],
            "since": "Unknown"  # Would need WHOIS registration date
        }
        
        # Handle WHOIS creation date for "since"
        try:
            if whois_info and hasattr(whois_info, 'creation_date') and whois_info.creation_date:
                if isinstance(whois_info.creation_date, list):
                    creation_date = whois_info.creation_date[0]
                else:
                    creation_date = whois_info.creation_date
                
                if creation_date:
                    hosting_details["since"] = creation_date.strftime("%Y-%m-%d")
        except:
            hosting_details["since"] = "Unknown"
        
        # Create server info
        server_info = {
            "ip": ip_address,
            "location": f"{ip_info.get('city', 'Unknown')}, {ip_info.get('country', 'Unknown')}",
            "nameservers": nameservers,
            "server": server_headers.get("server", "Unknown"),
            "x-powered-by": server_headers.get("powered_by", "Unknown"),
            "status_code": server_headers.get("status_code", "Unknown"),
            "isp": ip_info.get("org", "Unknown"),
            "asn": ip_info.get("as", "Unknown")
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
