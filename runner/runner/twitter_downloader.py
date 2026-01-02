import json
import os
import sys
import argparse
import subprocess

def get_video_info(url):
    """
    Uses yt-dlp to extract video information from a Twitter/X URL.
    """
    command = [
        'yt-dlp',
        '--no-warnings',
        '--simulate', # Don't download the video
        '--print-json', # Print JSON info to stdout
        url
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        video_data = json.loads(result.stdout)
        return video_data

    except subprocess.CalledProcessError as e:
        print(f"yt-dlp failed with error: {e.stderr}")
        return None
    except json.JSONDecodeError:
        print("Failed to parse JSON output from yt-dlp.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
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
            'status': 'success',
            'data': {
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
        }

    # SUCCESS: We found formats, return the full data
    description = data.get('description', '')
    hashtags = [f"#{tag}" for tag in description.split() if tag.startswith('#')][:5]

    return {
        'status': 'success',
        'data': {
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
    }

def main():
    parser = argparse.ArgumentParser(description='Analyze Twitter/X video using yt-dlp')
    parser.add_argument('--url', required=True, help='Twitter/X URL to analyze')
    parser.add_argument('--session_id', required=True, help='Session ID for tracking')
    
    args = parser.parse_args()
    
    print(f"Analyzing URL: {args.url}")
    
    raw_data = get_video_info(args.url)
    
    if not raw_data:
        final_result = {
            'status': 'error',
            'message': 'Could not extract video information. The URL may be invalid, private, or the content may not be a video.'
        }
    else:
        final_result = process_ytdlp_data(raw_data, args.url)

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
