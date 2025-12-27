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

def fetch_and_parse_sitemap(sitemap_url):
    """
    Fetches and parses a single sitemap file (not an index).
    Returns a list of URLs.
    """
    print(f"  Fetching sitemap: {sitemap_url}")
    try:
        response = requests.get(sitemap_url, timeout=15)
        response.raise_for_status()
        
        sitemap_dict = xmltodict.parse(response.content)
        
        if 'urlset' not in sitemap_dict:
            print(f"  Warning: Sitemap at {sitemap_url} does not contain a 'urlset'. Skipping.")
            return []

        urlset = sitemap_dict['urlset'].get('url', [])
        if not isinstance(urlset, list):
            urlset = [urlset]

        urls = []
        for entry in urlset:
            loc = entry.get('loc', '')
            lastmod = entry.get('lastmod', '')
            changefreq = entry.get('changefreq', 'not specified').lower()
            priority = entry.get('priority', '0.5')
            
            if loc: # Ensure loc is not empty
                urls.append({
                    "loc": loc,
                    "lastmod": lastmod,
                    "changefreq": changefreq,
                    "priority": priority
                })
        
        return urls

    except requests.exceptions.RequestException as e:
        print(f"  Error fetching sitemap {sitemap_url}: {str(e)}")
        return [] # Return empty list on error to not break the whole process
    except Exception as e:
        print(f"  Error parsing sitemap {sitemap_url}: {str(e)}")
        return []


def analyze_sitemap(sitemap_url):
    """
    Fetches and analyzes a sitemap or sitemap index.
    Handles both by recursively fetching child sitemaps.
    """
    try:
        print(f"Analyzing initial URL: {sitemap_url}")
        response = requests.get(sitemap_url, timeout=15)
        response.raise_for_status()
        
        sitemap_dict = xmltodict.parse(response.content)
        
        all_urls = []
        
        # Check if it's a sitemap index
        if 'sitemapindex' in sitemap_dict:
            print("Detected a sitemap index. Processing child sitemaps...")
            sitemap_entries = sitemap_dict['sitemapindex'].get('sitemap', [])
            if not isinstance(sitemap_entries, list):
                sitemap_entries = [sitemap_entries]

            for sitemap_entry in sitemap_entries:
                child_sitemap_url = sitemap_entry.get('loc')
                if child_sitemap_url:
                    child_urls = fetch_and_parse_sitemap(child_sitemap_url)
                    all_urls.extend(child_urls)
        
        # Check if it's a standard sitemap file
        elif 'urlset' in sitemap_dict:
            print("Detected a standard sitemap file.")
            all_urls = fetch_and_parse_sitemap(sitemap_url)
        
        else:
            return {
                "status": "error",
                "message": "Invalid sitemap format. Could not find 'urlset' or 'sitemapindex'. The URL might be a regular HTML page.",
                "url": sitemap_url
            }

        if not all_urls:
            return {
                "status": "error",
                "message": "Could not extract any valid URLs from the sitemap(s).",
                "url": sitemap_url
            }

        # Process all collected URLs
        change_freq_counts = {"daily": 0, "weekly": 0, "monthly": 0, "yearly": 0, "always": 0, "never": 0, "not specified": 0}
        
        for url_entry in all_urls:
            changefreq = url_entry.get('changefreq', 'not specified')
            if changefreq in change_freq_counts:
                change_freq_counts[changefreq] += 1

        stats = {
            "totalUrls": len(all_urls),
            "lastUpdated": max([u['lastmod'] for u in all_urls if u['lastmod']] or ['N/A']),
            "changeFrequencies": change_freq_counts
        }
        
        return {
            "status": "success",
            "message": f"Successfully analyzed {len(all_urls)} URLs from {len(sitemap_entries) if 'sitemap_entries' in locals() else 1} sitemap file(s).",
            "url": sitemap_url,
            "stats": stats,
            "urls": all_urls
        }
            
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Request failed: {str(e)}. The URL may be incorrect or the server may be down.",
            "url": sitemap_url
        }
    except Exception as e:
        # This will now catch the initial XML parsing error more gracefully
        return {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}. This might be because the URL does not point to a valid XML sitemap file.",
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
