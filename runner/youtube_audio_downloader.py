# File: runner/youtube_audio_downloader.py

import os
import json
import time
import sys
import uuid
import re
import yt_dlp
from datetime import datetime

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
        # Configure yt-dlp options for info extraction only
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info
            info = ydl.extract_info(url, download=False)
            
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
        
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
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
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Download and convert audio
            ydl.download([url])
            
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
