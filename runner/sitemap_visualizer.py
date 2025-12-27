import os
import json
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlparse, urljoin
import xmltodict
import re

def generate_session_id():
    return f"{int(time.time())}-{os.urandom(4).hex()}"

def validate_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def find_sitemap_url(base_url):
    """
    Tries to find the sitemap URL for a given base domain.
    1. Checks for /sitemap.xml
    2. Checks robots.txt for a 'Sitemap:' directive.
    Returns the found sitemap URL or None.
    """
    parsed_url = urlparse(base_url)
    domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Strategy 1: Try the common /sitemap.xml location
    sitemap_candidate = f"{domain}/sitemap.xml"
    print(f"  Probing common location: {sitemap_candidate}")
    try:
        response = requests.head(sitemap_candidate, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            # Do a quick GET to verify it's actually XML
            verify_response = requests.get(sitemap_candidate, timeout=10)
            if 'xml' in verify_response.headers.get('Content-Type', '') or verify_response.text.strip().startswith('<?xml'):
                print(f"  Found sitemap at common location: {sitemap_candidate}")
                return sitemap_candidate
    except requests.RequestException:
        print(f"  Sitemap not found at {sitemap_candidate}")

    # Strategy 2: Parse robots.txt to find the sitemap URL
    robots_url = f"{domain}/robots.txt"
    print(f"  Probing robots.txt: {robots_url}")
    try:
        response = requests.get(robots_url, timeout=10)
        if response.status_code == 200:
            # Use regex to find the Sitemap directive
            match = re.search(r'^Sitemap:\s*(.*)$', response.text, re.IGNORECASE | re.MULTILINE)
            if match:
                found_sitemap = match.group(1).strip()
                # Ensure the URL is absolute
                absolute_sitemap = urljoin(domain, found_sitemap)
                print(f"  Found sitemap in robots.txt: {absolute_sitemap}")
                return absolute_sitemap
    except requests.RequestException:
        print(f"  Could not fetch or parse robots.txt.")

    print("  Could not automatically find a sitemap URL.")
    return None


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


def analyze_sitemap(initial_url):
    """
    Fetches and analyzes a sitemap or sitemap index.
    Handles user-friendly input by trying to find the sitemap if a direct URL is not provided.
    """
    sitemap_url_to_analyze = initial_url
    parsed_url = urlparse(initial_url)
    
    # If the path is empty or just '/', it's likely a root domain, not a sitemap.
    if not parsed_url.path or parsed_url.path == '/':
        print("User provided a root domain. Attempting to find sitemap automatically...")
        discovered_sitemap = find_sitemap_url(initial_url)
        if discovered_sitemap:
            sitemap_url_to_analyze = discovered_sitemap
        else:
            return {
                "status": "error",
                "message": f"Could not find a sitemap for '{initial_url}'. Please provide the full sitemap URL (e.g., {initial_url}/sitemap.xml).",
                "url": initial_url
            }

    try:
        print(f"Analyzing sitemap URL: {sitemap_url_to_analyze}")
        response = requests.get(sitemap_url_to_analyze, timeout=15)
        response.raise_for_status()
        
        sitemap_dict = xmltodict.parse(response.content)
        
        all_urls = []
        sitemap_files_processed = 0
        
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
                    sitemap_files_processed += 1
        
        # Check if it's a standard sitemap file
        elif 'urlset' in sitemap_dict:
            print("Detected a standard sitemap file.")
            all_urls = fetch_and_parse_sitemap(sitemap_url_to_analyze)
            sitemap_files_processed = 1
        
        else:
            return {
                "status": "error",
                "message": "Invalid sitemap format. Could not find 'urlset' or 'sitemapindex'. The URL might be a regular HTML page.",
                "url": sitemap_url_to_analyze
            }

        if not all_urls:
            return {
                "status": "error",
                "message": "Could not extract any valid URLs from the sitemap(s).",
                "url": sitemap_url_to_analyze
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
            "message": f"Successfully analyzed {len(all_urls)} URLs from {sitemap_files_processed} sitemap file(s).",
            "url": sitemap_url_to_analyze,
            "stats": stats,
            "urls": all_urls
        }
            
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Request failed: {str(e)}. The URL may be incorrect or the server may be down.",
            "url": sitemap_url_to_analyze
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}. This might be because the URL does not point to a valid XML sitemap file.",
            "url": sitemap_url_to_analyze
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
    
    # --- DEBUGGING PRINT ---
    print(f"Final Python results object to be saved: {json.dumps(results)}")
    # --- END DEBUGGING PRINT ---

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
