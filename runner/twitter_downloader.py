import json
import os
import sys
import argparse
import subprocess
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import concurrent.futures
import threading

# Thread-safe storage for session data
session_data = {}
session_lock = threading.Lock()

def extract_tweet_id(url):
    """Extract tweet ID from Twitter/X URL"""
    tweet_id_match = re.search(r'(?:twitter\.com|x\.com)/\w+/status/(\d+)', url)
    return tweet_id_match.group(1) if tweet_id_match else None

def get_video_info_with_ytdlp(url, session_id):
    """
    Uses yt-dlp with optimized settings to extract video information from a Twitter/X URL.
    """
    # Create a unique output directory for this session
    output_dir = f'temp_{session_id}'
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Optimized command with timeout and specific format selection
        command = [
            'yt-dlp',
            '--no-warnings',
            '--simulate',
            '--print-json',
            '--format', 'best[height<=720]',  # Limit to 720p for faster processing
            '--add-header', 'Authorization:Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            '--add-header', 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            '--socket-timeout', '30',  # Set timeout to 30 seconds
            url
        ]
        
        print(f"Processing {url} with session {session_id}")
        
        # Run with timeout to prevent hanging
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=60  # 60 second timeout
        )
        
        video_data = json.loads(result.stdout)
        
        # Store session data
        with session_lock:
            session_data[session_id] = {
                'status': 'success',
                'data': video_data,
                'timestamp': datetime.now().isoformat()
            }
        
        return video_data
        
    except subprocess.TimeoutExpired:
        print(f"Timeout processing {url} with session {session_id}")
        with session_lock:
            session_data[session_id] = {
                'status': 'error',
                'message': 'Processing timed out. The video might be too large or the server is slow.',
                'timestamp': datetime.now().isoformat()
            }
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error processing {url} with session {session_id}: {e.stderr}")
        if "No video could be found" in e.stderr:
            # This means the tweet doesn't contain a video
            with session_lock:
                session_data[session_id] = {
                    'status': 'no_video',
                    'message': 'This tweet does not contain a video or GIF.',
                    'timestamp': datetime.now().isoformat()
                }
            return {"no_video": True}
        else:
            with session_lock:
                session_data[session_id] = {
                    'status': 'error',
                    'message': f'Failed to process: {e.stderr}',
                    'timestamp': datetime.now().isoformat()
                }
            return None
    except json.JSONDecodeError:
        print(f"JSON decode error for {url} with session {session_id}")
        with session_lock:
            session_data[session_id] = {
                'status': 'error',
                'message': 'Failed to parse video data.',
                'timestamp': datetime.now().isoformat()
            }
        return None
    except Exception as e:
        print(f"Unexpected error for {url} with session {session_id}: {str(e)}")
        with session_lock:
            session_data[session_id] = {
                'status': 'error',
                'message': f'Unexpected error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
        return None
    finally:
        # Clean up temp directory
        try:
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
        except:
            pass

def process_ytdlp_data(data, original_url):
    """
    Transforms the raw data from yt-dlp into the format expected by the React component.
    """
    if not data:
        return None

    # Check if yt-dlp reported no video
    if data.get("no_video"):
        return {
            'status': 'no_video',
            'message': 'This tweet does not contain a video or GIF.'
        }

    formats = []
    is_gif = False
    
    # Check if this is a GIF
    if data.get('description') and 'GIF' in data.get('description', '').upper():
        is_gif = True
    
    # Check for the main 'url' field
    if data.get('url'):
        formats.append({
            'quality': 'high',
            'resolution': f"{data.get('height', 'Unknown')}p",
            'size': f"{data.get('filesize_approx', 0) / (1024*1024):.1f} MB" if data.get('filesize_approx') else 'Unknown MB',
            'format': data.get('ext', 'mp4'),
            'url': data.get('url')
        })

    # If no direct URL, search the 'formats' list
    if not formats:
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

    # If still no formats, try to extract from requested_formats
    if not formats and 'requested_formats' in data:
        for f in data.get('requested_formats', []):
            if f.get('vcodec') != 'none' and f.get('url'):
                quality_label = f"{f.get('height', 'unknown')}p"
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
                break

    # If still no formats, it's likely not a downloadable video
    if not formats:
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

def format_duration(seconds):
    """Formats duration in seconds to a human-readable string."""
    if not seconds:
        return "0:00"
    minutes = int(seconds) // 60
    seconds = int(seconds) % 60
    return f"{minutes}:{seconds:02d}"

def main():
    parser = argparse.ArgumentParser(description='Analyze Twitter/X video using yt-dlp')
    parser.add_argument('--url', required=True, help='Twitter/X URL to analyze')
    parser.add_argument('--session_id', required=True, help='Session ID for tracking')
    
    args = parser.parse_args()
    
    print(f"Analyzing URL: {args.url} with session: {args.session_id}")
    
    # Process the video
    raw_data = get_video_info_with_ytdlp(args.url, args.session_id)
    
    # Get the session data
    with session_lock:
        session_result = session_data.get(args.session_id, {
            'status': 'error',
            'message': 'Unknown error occurred'
        })
    
    if session_result['status'] == 'success':
        final_result = {
            'status': 'success',
            'data': process_ytdlp_data(raw_data, args.url)
        }
    elif session_result['status'] == 'no_video':
        final_result = {
            'status': 'no_video',
            'message': session_result['message'],
            'data': {
                'title': 'Tweet Content',
                'description': 'This tweet does not contain a video or GIF.',
                'thumbnail': None,
                'duration': '0:00',
                'author': {
                    'name': 'Twitter User',
                    'username': '@user',
                    'avatar': 'https://picsum.photos/seed/avatar/100/100.jpg'
                },
                'formats': [],
                'hashtags': [],
                'isGif': False,
                'views': '0',
                'uploadDate': '',
                'url': args.url
            }
        }
    else:
        final_result = {
            'status': 'error',
            'message': session_result['message']
        }

    output_dir = 'artifacts'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"twitter_results_{args.session_id}.json")
    
    with open(output_file, 'w') as f:
        json.dump(final_result, f, indent=2)
    
    print(f"Results saved to {output_file}")
    print(f"Status: {final_result.get('status')}")
    
    # Clean up session data
    with session_lock:
        if args.session_id in session_data:
            del session_data[args.session_id]
    
    if final_result.get('status') != 'success':
        sys.exit(1)

if __name__ == "__main__":
    main()
