import json
import os
import sys
import argparse
import subprocess
import re
import requests
from datetime import datetime

def get_video_info_with_ytdlp(url):
    """
    Uses yt-dlp with updated authentication methods to extract video information from a Twitter/X URL.
    """
    # Try multiple approaches to get the video
    commands = [
        # First attempt: with cookies if available
        [
            'yt-dlp',
            '--no-warnings',
            '--simulate',
            '--print-json',
            '--add-header', 'Authorization:Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            url
        ],
        # Second attempt: with user agent
        [
            'yt-dlp',
            '--no-warnings',
            '--simulate',
            '--print-json',
            '--add-header', 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            url
        ],
        # Third attempt: basic approach
        [
            'yt-dlp',
            '--no-warnings',
            '--simulate',
            '--print-json',
            url
        ]
    ]
    
    for i, command in enumerate(commands):
        try:
            print(f"Attempt {i+1} with yt-dlp")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            video_data = json.loads(result.stdout)
            return video_data
        except subprocess.CalledProcessError as e:
            print(f"Attempt {i+1} failed with error: {e.stderr}")
            if i < len(commands) - 1:
                continue
            else:
                return None
        except json.JSONDecodeError:
            print(f"Attempt {i+1} failed to parse JSON output")
            if i < len(commands) - 1:
                continue
            else:
                return None

def get_video_info_with_twitter_api(url):
    """
    Fallback method using Twitter's public API endpoints.
    """
    try:
        # Extract tweet ID from URL
        tweet_id_match = re.search(r'(?:twitter\.com|x\.com)/\w+/status/(\d+)', url)
        if not tweet_id_match:
            return None
            
        tweet_id = tweet_id_match.group(1)
        
        # Use Twitter's GraphQL API (simplified approach)
        headers = {
            'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Try to get tweet details
        api_url = f"https://api.twitter.com/2/tweets/{tweet_id}?expansions=attachments.media_keys,author_id&media.fields=url,preview_image_url,width,height&user.fields=name,username,profile_image_url"
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return process_twitter_api_data(data, url)
        else:
            print(f"Twitter API request failed with status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Twitter API method failed with error: {e}")
        return None

def process_twitter_api_data(data, original_url):
    """
    Process Twitter API response into the format expected by the React component.
    """
    try:
        tweet = data.get('data', {})
        includes = data.get('includes', {})
        users = includes.get('users', [])
        media = includes.get('media', [])
        
        # Find the author
        author_id = tweet.get('author_id')
        author = next((u for u in users if u.get('id') == author_id), {})
        
        # Find media
        attachments = tweet.get('attachments', {})
        media_keys = attachments.get('media_keys', [])
        tweet_media = [m for m in media if m.get('media_key') in media_keys]
        
        # Process video media
        formats = []
        is_gif = False
        
        for m in tweet_media:
            if m.get('type') == 'video':
                # Get video info
                variants = m.get('variants', [])
                for v in variants:
                    if v.get('content_type') == 'video/mp4':
                        bitrate = v.get('bitrate', 0)
                        quality = 'medium'
                        if bitrate > 1000000: quality = 'high'
                        elif bitrate < 500000: quality = 'low'
                        
                        formats.append({
                            'quality': quality,
                            'resolution': f"{m.get('height', 0)}p",
                            'size': f"{v.get('bitrate', 0) / 1000:.0f} kbps",
                            'format': 'mp4',
                            'url': v.get('url')
                        })
            elif m.get('type') == 'animated_gif':
                is_gif = True
                variants = m.get('variants', [])
                for v in variants:
                    if v.get('content_type') == 'video/mp4':
                        formats.append({
                            'quality': 'high',
                            'resolution': f"{m.get('height', 0)}p",
                            'size': 'Unknown',
                            'format': 'mp4',
                            'url': v.get('url')
                        })
        
        # Get preview image
        thumbnail = None
        if tweet_media:
            thumbnail = tweet_media[0].get('preview_image_url')
        
        return {
            'title': tweet.get('text', '').split('\n')[0][:100],  # First line of tweet, truncated
            'description': tweet.get('text', ''),
            'thumbnail': thumbnail,
            'duration': '0:00',  # Not available from API
            'author': {
                'name': author.get('name', 'Twitter User'),
                'username': f"@{author.get('username', 'user')}",
                'avatar': author.get('profile_image_url', 'https://picsum.photos/seed/avatar/100/100.jpg')
            },
            'formats': formats,
            'hashtags': [],
            'isGif': is_gif,
            'views': '0',  # Not available from API
            'uploadDate': tweet.get('created_at', ''),
            'url': original_url
        }
    except Exception as e:
        print(f"Error processing Twitter API data: {e}")
        return None

def format_duration(seconds):
    """Formats duration in seconds to a human-readable string."""
    if not seconds:
        return "0:00"
    minutes = int(seconds) // 60
    seconds = int(seconds) % 60
    return f"{minutes}:{seconds:02d}"

def process_ytdlp_data(data, original_url):
    """
    Transforms the raw data from yt-dlp into the format expected by the React component.
    """
    if not data:
        return None

    print("--- DEBUG: yt-dlp raw data keys ---")
    print(list(data.keys()))
    print("--- DEBUG: Checking for direct 'url' key ---")
    print(f"Direct URL found: {'url' in data}")

    formats = []
    is_gif = False
    
    # Check if this is a GIF
    if data.get('description') and 'GIF' in data.get('description', '').upper():
        is_gif = True
    
    # Check for the main 'url' field
    if data.get('url'):
        print("--- DEBUG: Using direct URL from yt-dlp ---")
        formats.append({
            'quality': 'high',
            'resolution': f"{data.get('height', 'Unknown')}p",
            'size': f"{data.get('filesize_approx', 0) / (1024*1024):.1f} MB" if data.get('filesize_approx') else 'Unknown MB',
            'format': data.get('ext', 'mp4'),
            'url': data.get('url')
        })

    # If no direct URL, search the 'formats' list
    if not formats:
        print("--- DEBUG: Direct URL not found, searching formats list ---")
        sorted_formats = sorted(data.get('formats', []), key=lambda f: f.get('height', 0), reverse=True)
        seen_qualities = set()
        
        for f in sorted_formats:
            # We want a format that has both video and audio for a simple download
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                quality_label = f"{f.get('height', 'unknown')}p"
                if quality_label not in seen_qualities:
                    seen_qualities.add(quality_label)
                    quality = 'high'
                    if f.get('height', 1080) <= 480: quality = 'low'
                    elif f.get('height', 1080) <= 720: quality = 'medium'

                    formats.append({
                        'quality': quality,
                        'resolution': quality_label,
                        'size': f"{f.get('filesize_approx', 0) / (1024*1024):.1f} MB" if f.get('filesize_approx') else 'Unknown MB',
                        'format': f.get('ext', 'mp4'),
                        'url': f.get('url')
                    })
                    # We only need one format from this method to provide a download button
                    break 

    # If still no formats, it's likely not a downloadable video
    if not formats:
        print("--- DEBUG: No suitable video formats found. This might be an image or an unsupported video type. ---")
        # We still return the metadata so the user sees what was analyzed
        return {
            'title': data.get('title', 'Twitter/X Content'),
            'description': data.get('description', 'Could not find a downloadable video for this URL.'),
            'thumbnail': data.get('thumbnail'),
            'duration': format_duration(data.get('duration')),
            'author': {
                'name': data.get('uploader', 'Twitter/X User'),
                'username': data.get('uploader_id', '@user'),
                'avatar': data.get('uploader_avatar', 'https://picsum.photos/seed/avatar/100/100.jpg')
            },
            'formats': [], # The key part: an empty array
            'hashtags': [],
            'isGif': is_gif,
            'views': data.get('view_count', '0'),
            'uploadDate': data.get('upload_date', ''),
            'url': original_url
        }

    # SUCCESS: We found formats, return the full data
    description = data.get('description', '')
    hashtags = [f"#{tag}" for tag in description.split() if tag.startswith('#')][:5]

    return {
        'title': data.get('title', 'Twitter/X Video'),
        'description': data.get('description', 'Check out this video from Twitter/X!'),
        'thumbnail': data.get('thumbnail'),
        'duration': format_duration(data.get('duration')),
        'author': {
            'name': data.get('uploader', 'Twitter/X User'),
            'username': data.get('uploader_id', '@user'),
            'avatar': data.get('uploader_avatar', 'https://picsum.photos/seed/avatar/100/100.jpg')
        },
        'formats': formats, # This will now be populated
        'hashtags': hashtags,
        'isGif': is_gif,
        'views': data.get('view_count', '0'),
        'uploadDate': data.get('upload_date', ''),
        'url': original_url
    }

def main():
    parser = argparse.ArgumentParser(description='Analyze Twitter/X video using yt-dlp')
    parser.add_argument('--url', required=True, help='Twitter/X URL to analyze')
    parser.add_argument('--session_id', required=True, help='Session ID for tracking')
    
    args = parser.parse_args()
    
    print(f"Analyzing URL: {args.url}")
    
    # Try yt-dlp first with multiple approaches
    raw_data = get_video_info_with_ytdlp(args.url)
    
    # If yt-dlp fails, try Twitter API
    if not raw_data:
        print("yt-dlp failed, trying Twitter API fallback")
        raw_data = get_video_info_with_twitter_api(args.url)
    
    if not raw_data:
        final_result = {
            'status': 'error',
            'message': 'Could not extract video information. The URL may be invalid, private, or the content may not be a video. Twitter/X has recently changed their API, which may be causing this issue.'
        }
    else:
        final_result = {
            'status': 'success',
            'data': raw_data
        }

    output_dir = 'artifacts'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"twitter_results_{args.session_id}.json")
    
    with open(output_file, 'w') as f:
        json.dump(final_result, f, indent=2)
    
    print(f"Results saved to {output_file}")
    if final_result.get('status') == 'success':
        print("Successfully processed content.")
    else:
        print("Processing failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
