# File: runner/youtube_audio_downloader.py

import os
import json
import time
import sys
import uuid
import re
import yt_dlp
from datetime import datetime
import tempfile
import requests

def generate_session_id():
    return str(uuid.uuid4())

def extract_video_id(url):
    """
    Extract video ID from a YouTube URL
    """
    # Regular expression to extract video ID from YouTube URL
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
        r'youtube\.com/watch\?.*v=([^&\n?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_video_info(url):
    """
    Get video information from YouTube without downloading
    """
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Getting video info for: {url}")
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "Video info fetch failed to start.",
        "session_id": session_id
    }
    
    try:
        # Create a temporary cookies file
        cookies_file = None
        cookies_content = os.environ.get("YOUTUBE_COOKIES", "")
        
        if cookies_content:
            cookies_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            cookies_file.write(cookies_content)
            cookies_file.close()
        
        # Configure yt-dlp options for info extraction only
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        # Add cookies if available
        if cookies_file:
            ydl_opts['cookiefile'] = cookies_file.name
        
        # Try multiple methods to get video info
        info = None
        last_error = None
        
        # Method 1: Try with cookies if available
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            last_error = str(e)
            print(f"Method 1 failed: {e}")
            
            # Method 2: Try without cookies but with different user agent
            if not cookies_file:
                ydl_opts['http_headers'] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                except Exception as e2:
                    last_error = str(e2)
                    print(f"Method 2 failed: {e2}")
                    
                    # Method 3: Try with Invidious instance as fallback
                    try:
                        video_id = extract_video_id(url)
                        if video_id:
                            # Use an Invidious instance to get video info
                            invidious_url = f"https://yewtu.be/api/v1/videos/{video_id}"
                            response = requests.get(invidious_url, timeout=10)
                            
                            if response.status_code == 200:
                                data = response.json()
                                info = {
                                    'title': data.get('title', 'Unknown'),
                                    'uploader': data.get('author', 'Unknown'),
                                    'duration': data.get('lengthSeconds', 0),
                                    'thumbnail': data.get('videoThumbnails', [{}])[0].get('url', '') if data.get('videoThumbnails') else '',
                                    'view_count': data.get('viewCount', 0),
                                    'upload_date': data.get('published', '').replace('-', ''),
                                    'description': data.get('description', '')[:500] + '...' if data.get('description') else ''
                                }
                                print("Successfully used Invidious fallback")
                    except Exception as e3:
                        last_error = str(e3)
                        print(f"Method 3 failed: {e3}")
        
        if not info:
            raise Exception(f"All methods failed. Last error: {last_error}")
        
        # Format duration as MM:SS
        duration_seconds = info.get('duration', 0)
        minutes, seconds = divmod(duration_seconds, 60)
        duration = f"{minutes}:{seconds:02d}"
        
        # Get thumbnail URL
        thumbnail = info.get('thumbnail', '')
        
        results = {
            "status": "success",
            "session_id": session_id,
            "data": {
                "title": info.get('title', 'Unknown'),
                "uploader": info.get('uploader', 'Unknown'),
                "duration": duration,
                "thumbnail": thumbnail,
                "view_count": info.get('view_count', 0),
                "upload_date": info.get('upload_date', ''),
                "description": info.get('description', '')[:500] + '...' if info.get('description') else ''
            }
        }
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
    
    finally:
        # Clean up temporary cookies file
        if cookies_file and os.path.exists(cookies_file.name):
            os.unlink(cookies_file.name)
    
    # Always output the results, even if there was an error
    print(f"results={json.dumps(results)}")
    return results

def download_audio(url, quality):
    """
    Download audio from YouTube video and convert to MP3
    """
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Downloading audio for: {url}")
    print(f"Quality: {quality}")
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "Audio download failed to start.",
        "session_id": session_id
    }
    
    try:
        # Create a temporary cookies file
        cookies_file = None
        cookies_content = os.environ.get("YOUTUBE_COOKIES", "")
        
        if cookies_content:
            cookies_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            cookies_file.write(cookies_content)
            cookies_file.close()
        
        # Extract video ID for filename
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError("Could not extract video ID from URL")
        
        # Get video info first
        ydl_opts_info = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        # Add cookies if available
        if cookies_file:
            ydl_opts_info['cookiefile'] = cookies_file.name
        
        info = None
        last_error = None
        
        # Try to get video info
        try:
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            last_error = str(e)
            print(f"Video info extraction failed: {e}")
            
            # Try with Invidious fallback
            try:
                invidious_url = f"https://yewtu.be/api/v1/videos/{video_id}"
                response = requests.get(invidious_url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    info = {
                        'title': data.get('title', 'Unknown'),
                        'uploader': data.get('author', 'Unknown'),
                        'duration': data.get('lengthSeconds', 0),
                        'thumbnail': data.get('videoThumbnails', [{}])[0].get('url', '') if data.get('videoThumbnails') else '',
                        'view_count': data.get('viewCount', 0),
                        'upload_date': data.get('published', '').replace('-', ''),
                        'description': data.get('description', '')[:500] + '...' if data.get('description') else ''
                    }
                    print("Successfully used Invidious fallback for video info")
            except Exception as e2:
                print(f"Invidious fallback failed: {e2}")
        
        if not info:
            raise Exception(f"Could not get video info. Last error: {last_error}")
        
        title = info.get('title', video_id)
        # Clean title for filename
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        
        # Map quality to bitrate
        quality_map = {
            '64kbps': '64',
            '128kbps': '128',
            '192kbps': '192',
            '256kbps': '256',
            '320kbps': '320'
        }
        
        bitrate = quality_map.get(quality, '128')
        
        # Configure yt-dlp options for audio download
        output_filename = f"{safe_title}_{video_id}.mp3"
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': bitrate,
            }],
            'outtmpl': output_filename,
            'quiet': True,
            'no_warnings': True,
        }
        
        # Add cookies if available
        if cookies_file:
            ydl_opts['cookiefile'] = cookies_file.name
        
        # Try multiple methods to download
        download_success = False
        
        # Method 1: Try with cookies if available
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                download_success = True
        except Exception as e:
            last_error = str(e)
            print(f"Download method 1 failed: {e}")
            
            # Method 2: Try without cookies but with different user agent
            if not cookies_file:
                ydl_opts['http_headers'] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                        download_success = True
                except Exception as e2:
                    last_error = str(e2)
                    print(f"Download method 2 failed: {e2}")
                    
                    # Method 3: Try with Invidious direct download
                    try:
                        # Get direct download URL from Invidious
                        invidious_api_url = f"https://yewtu.be/api/v1/videos/{video_id}?format=json"
                        response = requests.get(invidious_api_url, timeout=10)
                        
                        if response.status_code == 200:
                            data = response.json()
                            audio_streams = data.get('adaptiveFormats', [])
                            
                            # Find the best audio stream
                            best_audio = None
                            for stream in audio_streams:
                                if stream.get('type', '').startswith('audio/'):
                                    if not best_audio or int(stream.get('bitrate', 0)) > int(best_audio.get('bitrate', 0)):
                                        best_audio = stream
                            
                            if best_audio:
                                download_url = best_audio.get('url')
                                if download_url:
                                    # Download the audio file
                                    audio_response = requests.get(download_url, stream=True, timeout=30)
                                    audio_response.raise_for_status()
                                    
                                    with open(output_filename, 'wb') as f:
                                        for chunk in audio_response.iter_content(chunk_size=8192):
                                            f.write(chunk)
                                    
                                    download_success = True
                                    print("Successfully used Invidious direct download")
                    except Exception as e3:
                        last_error = str(e3)
                        print(f"Download method 3 failed: {e3}")
        
        if not download_success:
            raise Exception(f"All download methods failed. Last error: {last_error}")
        
        # Check if file exists
        if os.path.exists(output_filename):
            file_size = os.path.getsize(output_filename)
            
            results = {
                "status": "success",
                "session_id": session_id,
                "data": {
                    "filename": output_filename,
                    "title": title,
                    "video_id": video_id,
                    "quality": quality,
                    "file_size": file_size,
                    "download_url": f"/downloads/{output_filename}"
                }
            }
        else:
            raise ValueError("Downloaded file not found")
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
    
    finally:
        # Clean up temporary cookies file
        if cookies_file and os.path.exists(cookies_file.name):
            os.unlink(cookies_file.name)
    
    # Always output the results, even if there was an error
    print(f"results={json.dumps(results)}")
    return results

if __name__ == "__main__":
    action = os.environ.get("ACTION", "info")
    target_url = os.environ.get("TARGET_URL")
    target_quality = os.environ.get("TARGET_QUALITY", "128kbps")
    
    if not target_url:
        print("ERROR: TARGET_URL environment variable not set.")
        print(f"results={json.dumps({'status': 'error', 'message': 'TARGET_URL environment variable not set.'})}")
        sys.exit(1)
    
    if action == "info":
        video_results = get_video_info(target_url)
    elif action == "download":
        download_results = download_audio(target_url, target_quality)
    else:
        print("ERROR: Invalid action specified.")
        print(f"results={json.dumps({'status': 'error', 'message': 'Invalid action specified.'})}")
        sys.exit(1)
    
    # The results are already printed in the function
