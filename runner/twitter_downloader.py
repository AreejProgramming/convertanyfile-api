import json
import os
import sys
import asyncio
import aiohttp
import aiofiles
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import redis
import subprocess
import time
from datetime import datetime, timedelta

# Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
REDIS_TTL = 3600  # 1 hour
MAX_CONCURRENT_REQUESTS = 50
REQUEST_TIMEOUT = 60  # seconds

# Initialize FastAPI app
app = FastAPI(title="Twitter Video Downloader API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis client
try:
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()
    redis_available = True
except:
    redis_available = False
    print("Redis not available, using in-memory cache")

# In-memory cache fallback
memory_cache = {}

# Request model
class TwitterRequest(BaseModel):
    url: str
    session_id: str

# Response model
class TwitterResponse(BaseModel):
    status: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

# Helper functions
def generate_cache_key(url: str) -> str:
    """Generate a cache key for the given URL"""
    import hashlib
    return f"twitter_video:{hashlib.md5(url.encode()).hexdigest()}"

def get_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get data from cache (Redis or in-memory)"""
    if redis_available:
        try:
            data = redis_client.get(cache_key)
            if data:
                return json.loads(data)
        except:
            pass
    
    # Fallback to memory cache
    if cache_key in memory_cache:
        cache_entry = memory_cache[cache_key]
        if time.time() - cache_entry["timestamp"] < REDIS_TTL:
            return cache_entry["data"]
        else:
            del memory_cache[cache_key]
    
    return None

def set_in_cache(cache_key: str, data: Dict[str, Any]) -> None:
    """Set data in cache (Redis or in-memory)"""
    if redis_available:
        try:
            redis_client.setex(cache_key, REDIS_TTL, json.dumps(data))
            return
        except:
            pass
    
    # Fallback to memory cache
    memory_cache[cache_key] = {
        "data": data,
        "timestamp": time.time()
    }

def extract_tweet_id(url: str) -> Optional[str]:
    """Extract tweet ID from Twitter/X URL"""
    import re
    tweet_id_match = re.search(r'(?:twitter\.com|x\.com)/\w+/status/(\d+)', url)
    return tweet_id_match.group(1) if tweet_id_match else None

async def get_video_info_with_ytdlp(url: str) -> Optional[Dict[str, Any]]:
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
        # Third attempt: with additional headers
        [
            'yt-dlp',
            '--no-warnings',
            '--simulate',
            '--print-json',
            '--add-header', 'Authorization:Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            '--add-header', 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            '--add-header', 'Accept-Language:en-US,en;q=0.9',
            '--add-header', 'Referer:https://twitter.com/',
            url
        ],
        # Fourth attempt: basic approach
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
            # Run the command asynchronously
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=REQUEST_TIMEOUT
            )
            
            if process.returncode == 0:
                video_data = json.loads(stdout.decode())
                return video_data
            else:
                error_msg = stderr.decode()
                print(f"Attempt {i+1} failed with error: {error_msg}")
                if "No video could be found" in error_msg:
                    # This means the tweet doesn't contain a video
                    return {"no_video": True}
                if i < len(commands) - 1:
                    continue
                else:
                    return None
        except asyncio.TimeoutError:
            print(f"Attempt {i+1} timed out")
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
        except Exception as e:
            print(f"Attempt {i+1} failed with error: {str(e)}")
            if i < len(commands) - 1:
                continue
            else:
                return None
    
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

# API endpoints
@app.get("/")
async def root():
    return {"message": "Twitter Video Downloader API"}

@app.post("/api/twitter-video", response_model=TwitterResponse)
async def get_twitter_video(request: TwitterRequest, background_tasks: BackgroundTasks):
    """
    Process a Twitter/X video URL and return download information.
    """
    # Validate URL
    import re
    twitter_regex = re.compile(r'^(https?:\/\/)?(www\.)?(twitter\.com|x\.com)\/.+\/status\/(\d+)')
    if not twitter_regex.match(request.url):
        raise HTTPException(status_code=400, detail="Invalid Twitter/X URL")
    
    # Check cache first
    cache_key = generate_cache_key(request.url)
    cached_data = get_from_cache(cache_key)
    if cached_data:
        return TwitterResponse(status="success", data=cached_data)
    
    # Check if we're at the concurrent request limit
    if redis_available:
        try:
            current_requests = redis_client.incr("current_requests")
            redis_client.expire("current_requests", 60)  # Expire after 1 minute
            
            if current_requests > MAX_CONCURRENT_REQUESTS:
                redis_client.decr("current_requests")
                raise HTTPException(
                    status_code=429, 
                    detail="Too many concurrent requests. Please try again later."
                )
        except:
            pass
    
    try:
        # Process the video
        raw_data = await get_video_info_with_ytdlp(request.url)
        
        # Check if yt-dlp reported no video
        if raw_data and raw_data.get("no_video"):
            result_data = {
                'status': 'no_video',
                'message': 'This tweet does not contain a video or GIF.',
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
                    'url': request.url,
                    'noVideo': True
                }
            }
        # If yt-dlp fails, return an error
        elif not raw_data:
            result_data = {
                'status': 'error',
                'message': 'Could not extract video information. The URL may be invalid, private, or the content may not be a video.'
            }
        else:
            # Process the data
            processed_data = process_ytdlp_data(raw_data, request.url)
            result_data = {
                'status': 'success',
                'data': processed_data
            }
            
            # Cache the successful result
            if result_data['status'] == 'success':
                set_in_cache(cache_key, processed_data)
        
        return TwitterResponse(**result_data)
    
    except Exception as e:
        print(f"Error processing Twitter video: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to process video. Please try again later."
        )
    finally:
        # Decrement the request counter
        if redis_available:
            try:
                redis_client.decr("current_requests")
            except:
                pass

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "redis_available": redis_available,
        "cache_size": len(memory_cache)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
