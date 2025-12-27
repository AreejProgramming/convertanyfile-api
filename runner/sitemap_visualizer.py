import os
import json
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlparse
import xmltodict

def generate_session_id():
    return f"{int(time.time())}-{os.urandom(4).hex()}"

def validate_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def analyze_sitemap(sitemap_url):
    """
    Fetches and analyzes a sitemap from a given URL.
    Handles both sitemap files and sitemap indexes.
    """
    try:
        response = requests.get(sitemap_url, timeout=15)
        response.raise_for_status()
        
        # Parse the XML content
        try:
            # Use xmltodict for easier parsing
            sitemap_dict = xmltodict.parse(response.content)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to parse XML: {str(e)}",
                "url": sitemap_url
            }
        
        # Check if it's a sitemap index or a sitemap file
        if 'sitemapindex' in sitemap_dict:
            return {
                "status": "error",
                "message": "Sitemap indexes are not directly supported yet. Please provide a direct sitemap URL.",
                "url": sitemap_url
            }
        elif 'urlset' in sitemap_dict:
            # It's a standard sitemap
            urlset = sitemap_dict['urlset']['url']
            if not isinstance(urlset, list):
                urlset = [urlset] # Ensure it's a list even with one entry
                
            urls = []
            change_freq_counts = {"daily": 0, "weekly": 0, "monthly": 0, "yearly": 0, "always": 0, "never": 0}
            
            for entry in urlset:
                loc = entry.get('loc', '')
                lastmod = entry.get('lastmod', '')
                changefreq = entry.get('changefreq', 'not specified').lower()
                priority = entry.get('priority', '0.5')
                
                urls.append({
                    "loc": loc,
                    "lastmod": lastmod,
                    "changefreq": changefreq,
                    "priority": priority
                })
                
                if changefreq in change_freq_counts:
                    change_freq_counts[changefreq] += 1

            stats = {
                "totalUrls": len(urls),
                "lastUpdated": max([u['lastmod'] for u in urls if u['lastmod']] or ['N/A']),
                "changeFrequencies": change_freq_counts
            }
            
            return {
                "status": "success",
                "message": f"Successfully analyzed {len(urls)} URLs.",
                "url": sitemap_url,
                "stats": stats,
                "urls": urls
            }
        else:
            return {
                "status": "error",
                "message": "Invalid sitemap format. Could not find 'urlset' or 'sitemapindex'.",
                "url": sitemap_url
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Request failed: {str(e)}",
            "url": sitemap_url
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "url": sitemap_url
        }

def main():
    target_url = os.environ.get("URL")
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    if not target_url:
        print("ERROR: URL environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "URL environment variable not set.",
            "session_id": session_id
        }
        
        with open('results.json', 'w') as f:
            json.dump(error_result, f)
        
        print(f"results={json.dumps(error_result)}")
        sys.exit(1)
        
    if not validate_url(target_url):
        print(f"ERROR: Invalid URL format: {target_url}")
        error_result = {
            "status": "error", 
            "message": "Invalid URL format.",
            "session_id": session_id
        }
        
        with open('results.json', 'w') as f:
            json.dump(error_result, f)
        
        print(f"results={json.dumps(error_result)}")
        sys.exit(1)
    
    print(f"Starting sitemap analysis for: {target_url}")
    print(f"Session ID: {session_id}")
    
    results = analyze_sitemap(target_url)
    results["session_id"] = results.get("session_id", session_id)
    results["timestamp"] = datetime.now().isoformat()
    
    try:
        with open('results.json', 'w') as f:
            json.dump(results, f)
        print("Results successfully written to results.json")
    except Exception as file_error:
        print(f"ERROR writing results file: {str(file_error)}")
        sys.exit(1)
    
    print(f"results={json.dumps(results)}")
    sys.exit(0)

if __name__ == "__main__":
    main()
