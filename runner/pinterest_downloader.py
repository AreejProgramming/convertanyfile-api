#!/usr/bin/env python3
import argparse
import json
import re
import requests
import sys
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote  # Added quote import here

class PinterestVideoDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
    
    def get_video_info(self, url):
        # Validate Pinterest URL
        if not self.is_valid_pinterest_url(url):
            return {'status': 'error', 'message': 'Invalid Pinterest URL'}
        
        # Extract pin ID
        pin_id = self.extract_pin_id(url)
        if not pin_id:
            return {'status': 'error', 'message': 'Could not extract pin ID from URL'}
        
        # Get the pin data
        pin_data = self.fetch_pin_data(pin_id)
        if not pin_data:
            return {'status': 'error', 'message': 'Failed to fetch pin data'}
        
        # Extract video information
        video_info = self.extract_video_info(pin_data)
        if not video_info:
            return {'status': 'error', 'message': 'No video found in this pin'}
        
        return {'status': 'success', 'data': video_info}
    
    def is_valid_pinterest_url(self, url):
        return re.match(r'^(https?:\/\/)?(www\.)?(pinterest\.com|pin\.it)\/.+', url, re.IGNORECASE)
    
    def extract_pin_id(self, url):
        # Handle different URL formats
        if re.search(r'pin\/(\d+)', url):
            return re.search(r'pin\/(\d+)', url).group(1)
        
        # Handle short URLs (pin.it)
        if 'pin.it' in url:
            try:
                response = self.session.head(url, allow_redirects=True, timeout=10)
                if response.status_code == 200:
                    redirect_url = response.url
                    if re.search(r'pin\/(\d+)', redirect_url):
                        return re.search(r'pin\/(\d+)', redirect_url).group(1)
            except Exception as e:
                print(f"Error following redirect: {e}")
        
        return None
    
    def fetch_pin_data(self, pin_id):
        # Method 1: Try Pinterest's GraphQL API
        graphql_data = self.fetch_with_graphql(pin_id)
        if graphql_data:
            return graphql_data
        
        # Method 2: Try scraping the pin page
        scraped_data = self.scrape_pin_page(pin_id)
        if scraped_data:
            return scraped_data
        
        return None
    
    def fetch_with_graphql(self, pin_id):
        try:
            # Pinterest's GraphQL query for pin data
            query_data = {
                "options": {
                    "field_set_key": "unauth_react_pin_grid",
                    "id": pin_id,
                    "is_promotable": False
                },
                "context": {}
            }
            
            api_url = f"https://www.pinterest.com/resource/PinResource/get/?data={quote(json.dumps(query_data))}"
            
            response = self.session.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'resource_response' in data and 'data' in data['resource_response']:
                    return data['resource_response']['data']
        except Exception as e:
            print(f"GraphQL error: {e}")
        
        return None
    
    def scrape_pin_page(self, pin_id):
        try:
            url = f"https://www.pinterest.com/pin/{pin_id}/"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                # Extract initial data from the page
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for the script tag containing the data
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'window.__PWS_DATA__' in script.string:
                        # Extract the JSON data
                        json_text = script.string.split('window.__PWS_DATA__ = ')[1].split(';</script>')[0]
                        data = json.loads(json_text)
                        
                        # Navigate through the data structure to find the pin
                        if 'resourceResponses' in data:
                            for resource in data['resourceResponses']:
                                if resource.get('resource', {}).get('name') == 'PinResource' and 'response' in resource and 'data' in resource['response']:
                                    return resource['response']['data']
        except Exception as e:
            print(f"Scraping error: {e}")
        
        return None
    
    def extract_video_info(self, pin_data):
        # Check if this pin has a video
        if 'videos' not in pin_data:
            return None
        
        # Get video data
        video_list = pin_data['videos'].get('video_list', {})
        video_data = video_list.get('V_720P') or video_list.get('V_480P') or video_list.get('V_360P')
        
        if not video_data:
            return None
        
        # Extract author information
        author_data = pin_data.get('closeup_attribution', {})
        author = {
            'name': author_data.get('full_name', 'Unknown'),
            'username': '@' + author_data.get('username', 'unknown'),
            'avatar': author_data.get('image_medium_url', 'https://picsum.photos/seed/avatar/100/100.jpg')
        }
        
        # Extract hashtags
        hashtags = []
        if 'hashtags' in pin_data:
            for tag in pin_data['hashtags']:
                hashtags.append('#' + tag['hashtag'])
        
        # Build video information
        video_info = {
            'title': pin_data.get('title') or pin_data.get('description') or 'Pinterest Video',
            'description': pin_data.get('description', 'No description available'),
            'thumbnail': pin_data.get('images', {}).get('236x', {}).get('url', 'https://picsum.photos/seed/pinterest/400/300.jpg'),
            'duration': self.format_duration(video_data.get('duration', 0)),
            'views': self.format_number(pin_data.get('aggregated_pin_data', {}).get('saves', 0)),
            'likes': self.format_number(pin_data.get('aggregated_pin_data', {}).get('repins', 0)),
            'saves': self.format_number(pin_data.get('aggregated_pin_data', {}).get('saves', 0)),
            'author': author,
            'hashtags': hashtags,
            'board': pin_data.get('board', {}).get('name', 'Unknown Board'),
            'downloadUrl': video_data.get('url'),
            'formats': self.get_available_formats(video_list)
        }
        
        return video_info
    
    def get_available_formats(self, video_list):
        formats = []
        
        # Define quality mapping
        quality_map = {
            'V_720P': {'quality': 'high', 'resolution': '720p'},
            'V_480P': {'quality': 'medium', 'resolution': '480p'},
            'V_360P': {'quality': 'low', 'resolution': '360p'}
        }
        
        for key, video in video_list.items():
            if key in quality_map:
                quality = quality_map[key]['quality']
                resolution = quality_map[key]['resolution']
                size = self.format_file_size(video.get('size', 0))
                
                formats.append({
                    'quality': quality,
                    'resolution': resolution,
                    'size': size,
                    'format': 'mp4',
                    'url': video.get('url')
                })
        
        # Sort by quality (high to low)
        quality_order = {'high': 3, 'medium': 2, 'low': 1}
        formats.sort(key=lambda f: quality_order.get(f['quality'], 0), reverse=True)
        
        return formats
    
    def format_duration(self, seconds):
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def format_number(self, num):
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        return str(num)
    
    def format_file_size(self, bytes):
        if bytes >= 1048576:
            return f"{bytes/1048576:.1f} MB"
        elif bytes >= 1024:
            return f"{bytes/1024:.1f} KB"
        return f"{bytes} bytes"

def main():
    parser = argparse.ArgumentParser(description='Download Pinterest videos')
    parser.add_argument('--url', required=True, help='Pinterest URL to analyze')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    
    args = parser.parse_args()
    
    downloader = PinterestVideoDownloader()
    result = downloader.get_video_info(args.url)
    
    with open(args.output, 'w') as f:
        json.dump(result, f)
    
    return 0 if result['status'] == 'success' else 1

if __name__ == '__main__':
    sys.exit(main())
