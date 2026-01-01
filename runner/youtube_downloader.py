import yt_dlp
import sys
import os
import re
import time

def sanitize_filename(filename):
    """Remove or replace characters that are invalid in filenames"""
    # Replace invalid characters with underscores
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename or "untitled"

def download_video(url, quality='720p', format='mp4', output_path='.', max_retries=3):
    """
    Downloads a video from a given YouTube URL with specified quality and format.
    Includes retry logic with different configurations.
    """
    
    # Different configurations to try
    configs = [
        # Configuration 1: Android client
        {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'format': f'best[height<={quality.replace("p", "")}]/best' if format != 'mp3' else 'bestaudio/best',
            'no_warnings': False,
            'quiet': False,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; US) gzip'
            }
        },
        # Configuration 2: iOS client
        {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'format': f'best[height<={quality.replace("p", "")}]/best' if format != 'mp3' else 'bestaudio/best',
            'no_warnings': False,
            'quiet': False,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios'],
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.ios.youtube/19.09.3 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X; en_US)'
            }
        },
        # Configuration 3: Web client with no JS
        {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'format': f'best[height<={quality.replace("p", "")}]/best' if format != 'mp3' else 'bestaudio/best',
            'no_warnings': False,
            'quiet': False,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],
                    'player_skip': ['js', 'configs'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        }
    ]
    
    # Add postprocessors for mp3 format
    if format == 'mp3':
        for config in configs:
            config['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
    
    for attempt in range(max_retries):
        for i, config in enumerate(configs):
            print(f"Attempt {attempt + 1}/{max_retries}, Configuration {i + 1}/{len(configs)}")
            print(f"Trying with client: {config['extractor_args']['youtube']['player_client']}")
            
            try:
                with yt_dlp.YoutubeDL(config) as ydl:
                    # First extract info without downloading to validate
                    info_dict = ydl.extract_info(url, download=False)
                    
                    # Check if info_dict is valid
                    if not info_dict:
                        raise Exception("Failed to extract video information")
                        
                    # Get video title with fallback
                    video_title = info_dict.get('title', None)
                    if not video_title:
                        # Try to use video ID as fallback
                        video_id = info_dict.get('id', None)
                        video_title = video_id if video_id else "video"
                    
                    # Sanitize the title for filename
                    safe_title = sanitize_filename(video_title)
                        
                    # Get video extension with fallback
                    video_ext = info_dict.get('ext', format if format != 'mp3' else 'mp3')
                    
                    # Now download with the validated info
                    info_dict = ydl.extract_info(url, download=True)
                    
                    # Create filename safely
                    filename = f"{safe_title}.{video_ext}"
                    print(f"Successfully downloaded: {filename}")
                    return filename
                    
            except Exception as e:
                print(f"Configuration {i + 1} failed: {e}")
                if i == len(configs) - 1 and attempt == max_retries - 1:
                    # All configurations and attempts failed
                    print(f"All attempts failed. Last error: {e}")
                    return None
                else:
                    # Wait before next attempt
                    time.sleep(2)
    
    return None

if __name__ == "__main__":
    # Expecting 3 arguments: url, quality, format
    if len(sys.argv) < 4:
        print("Error: Please provide a URL, quality, and format as arguments.")
        sys.exit(1)
    
    video_url = sys.argv[1]
    selected_quality = sys.argv[2]
    selected_format = sys.argv[3]
    
    # Create a directory to store the video
    output_dir = "video_output"
    os.makedirs(output_dir, exist_ok=True)
    
    downloaded_file = download_video(video_url, selected_quality, selected_format, output_dir)
    
    if downloaded_file:
        print(f"Download complete. File saved to: {os.path.join(output_dir, downloaded_file)}")
    else:
        print("Download failed.")
        sys.exit(1)
