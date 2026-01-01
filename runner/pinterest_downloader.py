import requests
import json
import os
import re
import sys
import argparse
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

def extract_pin_id(url):
    """Extract the pin ID from a Pinterest URL."""
    # Handle different Pinterest URL formats
    patterns = [
        r'pinterest\.com/pin/(\d+)',
        r'pin\.it/([a-zA-Z0-9]+)',
        r'pinterest\.com/.*?/pin/(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_video_info(pin_id):
    """Get video information from Pinterest API."""
    # Pinterest's internal API endpoint
    api_url = f"https://www.pinterest.com/resource/PinResource/get/"
    
    # Prepare the data for the API request
    data = {
        "data": {
            "options": {
                "field_set_key": "unauth_react_pin_grid",
                "id": pin_id
            },
            "context": {}
        }
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": "https://www.pinterest.com/",
        "Origin": "https://www.pinterest.com"
    }
    
    try:
        response = requests.post(api_url, json=data, headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching video info: {e}")
    
    return None

def extract_video_from_page(url):
    """Extract video information by parsing the Pinterest page."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for embedded JSON data in script tags
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'Preact' in script.string and 'video' in script.string:
                    # Extract JSON data from the script
                    try:
                        # Find the JSON data in the script
                        json_data = re.search(r'window\.__PWS_DATA__\s*=\s*({.+});', script.string)
                        if json_data:
                            data = json.loads(json_data.group(1))
                            return extract_video_from_pws_data(data)
                    except (json.JSONDecodeError, AttributeError) as e:
                        print(f"Error parsing JSON: {e}")
                        continue
            
            # Alternative method: Look for video tags
            video_tags = soup.find_all('video')
            if video_tags:
                video_tag = video_tags[0]
                sources = video_tag.find_all('source')
                if sources:
                    return {
                        'status': 'success',
                        'data': {
                            'title': soup.title.string if soup.title else 'Pinterest Video',
                            'thumbnail': video_tag.get('poster', ''),
                            'downloadUrl': sources[0].get('src', ''),
                            'duration': '0:30',  # Default duration
                            'description': 'Video from Pinterest'
                        }
                    }
    except Exception as e:
        print(f"Error fetching page: {e}")
    
    return None

def extract_video_from_pws_data(data):
    """Extract video information from Pinterest's PWS data."""
    try:
        # Navigate through the nested data structure
        if 'resourceResponses' in data:
            for resource in data['resourceResponses']:
                if resource.get('name') == 'PinResource':
                    pin_data = resource.get('response', {}).get('data', {})
                    
                    if 'videos' in pin_data and 'video_list' in pin_data['videos']:
                        video_list = pin_data['videos']['video_list']
                        
                        # Find the highest quality video
                        highest_quality = None
                        highest_height = 0
                        
                        for video_key, video_info in video_list.items():
                            if 'url' in video_info and 'height' in video_info:
                                if video_info['height'] > highest_height:
                                    highest_height = video_info['height']
                                    highest_quality = video_info
                        
                        if highest_quality:
                            return {
                                'status': 'success',
                                'data': {
                                    'title': pin_data.get('title', 'Pinterest Video'),
                                    'description': pin_data.get('description', ''),
                                    'thumbnail': pin_data.get('images', {}).get('orig', {}).get('url', ''),
                                    'downloadUrl': highest_quality['url'],
                                    'duration': format_duration(pin_data.get('videos', {}).get('duration', 0)),
                                    'author': {
                                        'name': pin_data.get('pinner', {}).get('full_name', ''),
                                        'username': pin_data.get('pinner', {}).get('username', ''),
                                        'avatar': pin_data.get('pinner', {}).get('image_medium_url', '')
                                    },
                                    'board': pin_data.get('board', {}).get('name', ''),
                                    'hashtags': extract_hashtags(pin_data.get('description', ''))
                                }
                            }
    except Exception as e:
        print(f"Error extracting from PWS data: {e}")
    
    return None

def extract_hashtags(description):
    """Extract hashtags from description."""
    if not description:
        return []
    
    # Find hashtags in the description
    hashtags = re.findall(r'#(\w+)', description)
    return [f"#{tag}" for tag in hashtags[:5]]  # Limit to 5 hashtags

def format_duration(seconds):
    """Format duration in seconds to MM:SS format."""
    if not seconds:
        return "0:30"
    
    minutes = int(seconds) // 60
    seconds = int(seconds) % 60
    return f"{minutes}:{seconds:02d}"

def download_pinterest_video(url, session_id, output_dir):
    """Main function to download Pinterest video."""
    print(f"Processing Pinterest URL: {url}")
    
    # Extract pin ID from URL
    pin_id = extract_pin_id(url)
    if not pin_id:
        print("Could not extract pin ID from URL")
        return None
    
    print(f"Extracted pin ID: {pin_id}")
    
    # Try to get video info from API first
    video_info = get_video_info(pin_id)
    
    # If API fails, try parsing the page
    if not video_info:
        print("API method failed, trying page parsing...")
        video_info = extract_video_from_page(url)
    
    if not video_info:
        print("Could not extract video information")
        return None
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the results to a JSON file
    output_file = os.path.join(output_dir, f"pinterest_results_{session_id}.json")
    with open(output_file, 'w') as f:
        json.dump(video_info, f, indent=2)
    
    print(f"Results saved to {output_file}")
    return video_info

def main():
    parser = argparse.ArgumentParser(description='Download Pinterest videos')
    parser.add_argument('--url', required=True, help='Pinterest URL to download')
    parser.add_argument('--session_id', required=True, help='Session ID for tracking')
    parser.add_argument('--output_dir', default='artifacts', help='Output directory')
    
    args = parser.parse_args()
    
    result = download_pinterest_video(args.url, args.session_id, args.output_dir)
    
    if result:
        print("Successfully processed Pinterest video")
        sys.exit(0)
    else:
        print("Failed to process Pinterest video")
        sys.exit(1)

if __name__ == "__main__":
    main()
