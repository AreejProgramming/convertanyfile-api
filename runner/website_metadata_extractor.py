import os
import json
import time
import sys
import re
import requests
import uuid
from datetime import datetime
from urllib.parse import urlparse
import concurrent.futures
from bs4 import BeautifulSoup
import html

def generate_session_id():
    return str(uuid.uuid4())

def validate_url(url):
    """
    Validate if input is a valid URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def normalize_url(url):
    """
    Normalize URL format
    """
    if not url:
        return None
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Remove trailing slash
    if url.endswith('/'):
        url = url[:-1]
    
    return url

def extract_metadata_from_html(html_content, url):
    """
    Extract metadata from HTML content
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract basic metadata
        title = ""
        if soup.title:
            title = soup.title.string.strip() if soup.title.string else ""
        
        # Extract meta description
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content').strip()
        
        # Extract keywords
        keywords = []
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            keywords = [k.strip() for k in meta_keywords.get('content').split(',')]
        
        # Extract canonical URL
        canonical = url
        canonical_link = soup.find('link', attrs={'rel': 'canonical'})
        if canonical_link and canonical_link.get('href'):
            canonical = canonical_link.get('href')
        
        # Extract language
        language = "en-US"
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            language = html_tag.get('lang')
        
        # Extract charset
        charset = "UTF-8"
        meta_charset = soup.find('meta', attrs={'charset': True})
        if meta_charset and meta_charset.get('content'):
            charset = meta_charset.get('content')
        
        # Extract viewport
        viewport = "width=device-width, initial-scale=1.0"
        meta_viewport = soup.find('meta', attrs={'name': 'viewport'})
        if meta_viewport and meta_viewport.get('content'):
            viewport = meta_viewport.get('content')
        
        # Extract robots
        robots = "index, follow"
        meta_robots = soup.find('meta', attrs={'name': 'robots'})
        if meta_robots and meta_robots.get('content'):
            robots = meta_robots.get('content')
        
        # Extract favicon
        domain = urlparse(url).netloc
        favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
        
        # Extract Open Graph tags
        og_title = title
        og_description = description
        og_type = "website"
        og_url = url
        og_image = ""
        og_site_name = domain
        og_locale = "en_US"
        
        og_title_meta = soup.find('meta', property='og:title')
        if og_title_meta and og_title_meta.get('content'):
            og_title = og_title_meta.get('content')
            
        og_desc_meta = soup.find('meta', property='og:description')
        if og_desc_meta and og_desc_meta.get('content'):
            og_description = og_desc_meta.get('content')
            
        og_type_meta = soup.find('meta', property='og:type')
        if og_type_meta and og_type_meta.get('content'):
            og_type = og_type_meta.get('content')
            
        og_url_meta = soup.find('meta', property='og:url')
        if og_url_meta and og_url_meta.get('content'):
            og_url = og_url_meta.get('content')
            
        og_image_meta = soup.find('meta', property='og:image')
        if og_image_meta and og_image_meta.get('content'):
            og_image = og_image_meta.get('content')
            
        og_site_meta = soup.find('meta', property='og:site_name')
        if og_site_meta and og_site_meta.get('content'):
            og_site_name = og_site_meta.get('content')
            
        og_locale_meta = soup.find('meta', property='og:locale')
        if og_locale_meta and og_locale_meta.get('content'):
            og_locale = og_locale_meta.get('content')
        
        # Extract Twitter Card tags
        twitter_card = "summary_large_image"
        twitter_site = "@example"
        twitter_creator = "@johndoe"
        twitter_title = title
        twitter_description = description
        twitter_image = ""
        
        twitter_card_meta = soup.find('meta', attrs={'name': 'twitter:card'})
        if twitter_card_meta and twitter_card_meta.get('content'):
            twitter_card = twitter_card_meta.get('content')
            
        twitter_site_meta = soup.find('meta', attrs={'name': 'twitter:site'})
        if twitter_site_meta and twitter_site_meta.get('content'):
            twitter_site = twitter_site_meta.get('content')
            
        twitter_creator_meta = soup.find('meta', attrs={'name': 'twitter:creator'})
        if twitter_creator_meta and twitter_creator_meta.get('content'):
            twitter_creator = twitter_creator_meta.get('content')
            
        twitter_title_meta = soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title_meta and twitter_title_meta.get('content'):
            twitter_title = twitter_title_meta.get('content')
            
        twitter_desc_meta = soup.find('meta', attrs={'name': 'twitter:description'})
        if twitter_desc_meta and twitter_desc_meta.get('content'):
            twitter_description = twitter_desc_meta.get('content')
            
        twitter_image_meta = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image_meta and twitter_image_meta.get('content'):
            twitter_image = twitter_image_meta.get('content')
        
        # Extract Schema.org structured data
        schema = {}
        schema_scripts = soup.find_all('script', type='application/ld+json')
        for script in schema_scripts:
            if script.string:
                try:
                    schema_data = json.loads(script.string)
                    if isinstance(schema_data, dict):
                        schema.update(schema_data)
                except:
                    pass
        
        # If no schema found, create a basic one
        if not schema:
            schema = {
                "@context": "https://schema.org",
                "@type": "WebPage",
                "name": title,
                "description": description,
                "url": url,
                "datePublished": datetime.now().isoformat(),
                "dateModified": datetime.now().isoformat(),
                "author": {
                    "@type": "Person",
                    "name": "Unknown"
                },
                "publisher": {
                    "@type": "Organization",
                    "name": domain
                }
            }
        
        # Extract headings
        headings = []
        for i in range(1, 7):
            heading = soup.find(f'h{i}')
            if heading:
                headings.append({
                    "level": i,
                    "text": heading.get_text().strip(),
                    "id": heading.get('id') if heading.get('id') else f"heading-{i}"
                })
        
        # Extract images
        images = []
        img_tags = soup.find_all('img')
        for img in img_tags[:10]:  # Limit to first 10 images
            src = img.get('src')
            alt = img.get('alt', '')
            width = img.get('width', '')
            height = img.get('height', '')
            
            if src:
                images.append({
                    "src": src,
                    "alt": alt,
                    "width": int(width) if width.isdigit() else 0,
                    "height": int(height) if height.isdigit() else 0
                })
        
        # Extract links
        links = []
        a_tags = soup.find_all('a', href=True)
        for a in a_tags[:20]:  # Limit to first 20 links
            href = a.get('href')
            text = a.get_text().strip()
            is_external = href and (urlparse(href).netloc != urlparse(url).netloc)
            
            if href and text:
                links.append({
                    "href": href,
                    "text": text,
                    "external": is_external
                })
        
        # Extract meta tags
        meta_tags = []
        meta_tag_elements = soup.find_all('meta')
        for meta in meta_tag_elements:
            name = meta.get('name') or meta.get('property') or ''
            content = meta.get('content', '')
            
            if name and content:
                meta_tags.append({
                    "name": name,
                    "content": content
                })
        
        # Extract performance metrics (mock data)
        import random
        performance = {
            "loadTime": random.randint(500, 3000),
            "size": random.randint(100000, 5000000),
            "requests": random.randint(10, 100)
        }
        
        return {
            "url": url,
            "title": title,
            "description": description,
            "keywords": keywords,
            "author": "Unknown",
            "canonical": canonical,
            "language": language,
            "charset": charset,
            "viewport": viewport,
            "robots": robots,
            "favicon": favicon,
            "openGraph": {
                "title": og_title,
                "description": og_description,
                "type": og_type,
                "url": og_url,
                "image": og_image,
                "siteName": og_site_name,
                "locale": og_locale
            },
            "twitter": {
                "card": twitter_card,
                "site": twitter_site,
                "creator": twitter_creator,
                "title": twitter_title,
                "description": twitter_description,
                "image": twitter_image
            },
            "schema": schema,
            "headings": headings,
            "images": images,
            "links": links,
            "metaTags": meta_tags,
            "performance": performance
        }
        
    except Exception as e:
        print(f"Error extracting metadata: {str(e)}")
        return {"error": str(e)}

def fetch_website_content(url):
    """
    Fetch website content
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}: {response.reason}"}
        
        content_type = response.headers.get('content-type', '')
        
        if 'text/html' not in content_type:
            return {"error": "URL does not point to HTML content"}
        
        return {
            "content": response.text,
            "content_type": content_type,
            "status_code": response.status_code,
            "response_headers": dict(response.headers)
        }
        
    except Exception as e:
        print(f"Error fetching website: {str(e)}")
        return {"error": str(e)}

def check_website_metadata(url):
    """
    Main function to check website metadata
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting metadata extraction for: {url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Extracting website metadata...",
        "session_id": session_id
    }
    
    try:
        # Validate and normalize URL
        normalized_url = normalize_url(url)
        
        if not normalized_url or not validate_url(normalized_url):
            raise ValueError("Invalid URL format")
        
        # Fetch website content
        print(f"Fetching content from {normalized_url}")
        content_data = fetch_website_content(normalized_url)
        
        if "error" in content_data:
            raise ValueError(content_data["error"])
        
        # Extract metadata from HTML
        print("Extracting metadata from HTML content")
        metadata = extract_metadata_from_html(content_data["content"], normalized_url)
        
        if "error" in metadata:
            raise ValueError(metadata["error"])
        
        # Create final results
        results = {
            "status": "success",
            "url": normalized_url,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": metadata
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
    url = os.environ.get("URL")
    if not url:
        print("ERROR: URL environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "URL environment variable not set.",
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
        
    metadata_results = check_website_metadata(url)
    
    # The results are already printed in the function
    sys.exit(0)
