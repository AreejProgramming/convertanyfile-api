import argparse
import json
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import os
import gzip
from io import BytesIO

def parse_sitemap(url, max_hops=3):
    """Parse sitemap and return structured data"""
    results = {
        'status': 'success',
        'url': url,
        'stats': {
            'totalUrls': 0,
            'changeFrequencies': {
                'daily': 0,
                'weekly': 0,
                'monthly': 0,
                'yearly': 0,
                'never': 0
            }
        },
        'urls': []
    }
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Handle gzipped sitemaps
        if url.endswith('.gz'):
            content = gzip.decompress(response.content)
        else:
            content = response.content
            
        # Parse XML
        root = ET.fromstring(content)
        
        # Handle sitemap index
        if root.tag.endswith('sitemapindex'):
            sitemaps = []
            for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc is not None:
                    sitemaps.append(loc.text)
            
            # Process each sitemap (with hop limit)
            for sitemap_url in sitemaps[:max_hops]:
                try:
                    sitemap_data = parse_single_sitemap(sitemap_url)
                    if sitemap_data:
                        results['urls'].extend(sitemap_data['urls'])
                        results['stats']['totalUrls'] += sitemap_data['stats']['totalUrls']
                        for freq in results['stats']['changeFrequencies']:
                            results['stats']['changeFrequencies'][freq] += sitemap_data['stats']['changeFrequencies'][freq]
                except Exception as e:
                    print(f"Error processing sitemap {sitemap_url}: {e}")
                    continue
        else:
            # Handle single sitemap
            sitemap_data = parse_single_sitemap(url)
            if sitemap_data:
                results = sitemap_data
        
        return results
        
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

def parse_single_sitemap(url):
    """Parse a single sitemap file"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Handle gzipped sitemaps
        if url.endswith('.gz'):
            content = gzip.decompress(response.content)
        else:
            content = response.content
            
        # Parse XML
        root = ET.fromstring(content)
        
        results = {
            'status': 'success',
            'url': url,
            'stats': {
                'totalUrls': 0,
                'changeFrequencies': {
                    'daily': 0,
                    'weekly': 0,
                    'monthly': 0,
                    'yearly': 0,
                    'never': 0
                }
            },
            'urls': []
        }
        
        # Extract URLs
        for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
            loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            changefreq = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}changefreq')
            priority = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}priority')
            lastmod = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
            
            url_data = {
                'loc': loc.text if loc is not None else '',
                'changefreq': changefreq.text if changefreq is not None else 'unknown',
                'priority': float(priority.text) if priority is not None else 0.5,
                'lastmod': lastmod.text if lastmod is not None else None
            }
            
            results['urls'].append(url_data)
            results['stats']['totalUrls'] += 1
            
            # Count change frequencies
            freq = changefreq.text if changefreq is not None else 'unknown'
            if freq in results['stats']['changeFrequencies']:
                results['stats']['changeFrequencies'][freq] += 1
        
        return results
        
    except Exception as e:
        print(f"Error parsing sitemap {url}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Analyze sitemap')
    parser.add_argument('--url', required=True, help='Sitemap URL to analyze')
    parser.add_argument('--session-id', required=True, help='Session ID')
    parser.add_argument('--max-hops', type=int, default=3, help='Maximum number of sitemap hops')
    
    args = parser.parse_args()
    
    # Create results directory
    os.makedirs('results', exist_ok=True)
    
    # Analyze sitemap
    results = parse_sitemap(args.url, args.max_hops)
    
    # Save results
    with open('results/results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Analysis complete. Results saved for session {args.session_id}")

if __name__ == '__main__':
    main()
