import json
import os
import sys
import argparse
import subprocess

def get_video_info(url):
    """
    Uses yt-dlp to extract video information from a URL.
    This is the most robust method as yt-dlp is actively maintained
    to handle site changes.
    """
    command = [
        'yt-dlp',
        '--no-warnings',
        '--simulate', # Don't download the video
        '--print-json', # Print JSON info to stdout
        url
    ]

    try:
        # Run the yt-dlp command
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the JSON output from yt-dlp
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

    # yt-dlp provides a list of formats. We'll group them by quality.
    formats = []
    seen_qualities = set()
    
    # Sort formats by height (quality) descending
    sorted_formats = sorted(data.get('formats', []), key=lambda f: f.get('height', 0), reverse=True)

    for f in sorted_formats:
        # We only want video-only or video+audio streams
        if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
            quality_label = f"{f.get('height', 'unknown')}p"
            
            # Avoid duplicate quality entries
            if quality_label not in seen_qualities:
                seen_qualities.add(quality_label)
                
                # Map to our quality names
                quality = 'high'
                if f.get('height', 1080) <= 480:
                    quality = 'low'
                elif f.get('height', 1080) <= 720:
                    quality = 'medium'

                formats.append({
                    'quality': quality,
                    'resolution': quality_label,
                    'size': f"{f.get('filesize_approx', 0) / (1024*1024):.1f} MB" if f.get('filesize_approx') else 'Unknown MB',
                    'format': f.get('ext', 'mp4'),
                    'url': f.get('url') # This is the direct download URL
                })

    # If no formats were found, create a default one
    if not formats and data.get('url'):
        formats.append({
            'quality': 'high',
            'resolution': 'Unknown',
            'size': 'Unknown MB',
            'format': 'mp4',
            'url': data.get('url')
        })

    # Extract hashtags from description
    description = data.get('description', '')
    hashtags = [f"#{tag}" for tag in description.split() if tag.startswith('#')][:5]

    # Create the final result object
    return {
        'status': 'success',
        'data': {
            'title': data.get('title', 'Pinterest Video'),
            'description': data.get('description', 'Check out this video from Pinterest!'),
            'thumbnail': data.get('thumbnail'),
            'duration': format_duration(data.get('duration')),
            'author': {
                'name': data.get('uploader', 'Creative User'),
                'username': data.get('uploader_id', '@creativeuser'),
                'avatar': data.get('uploader_avatar', 'https://picsum.photos/seed/avatar/100/100.jpg')
            },
            'formats': formats,
            'hashtags': hashtags,
            'board': data.get('playlist', 'Creative Videos'), # 'playlist' often corresponds to the board
            'url': original_url
        }
    }

def main():
    parser = argparse.ArgumentParser(description='Analyze Pinterest video using yt-dlp')
    parser.add_argument('--url', required=True, help='Pinterest URL to analyze')
    parser.add_argument('--session_id', required=True, help='Session ID for tracking')
    
    args = parser.parse_args()
    
    print(f"Analyzing URL: {args.url}")
    
    # 1. Get raw video data using yt-dlp
    raw_data = get_video_info(args.url)
    
    if not raw_data:
        print("Failed to get video information.")
        # Create a failure object
        final_result = {
            'status': 'error',
            'message': 'Could not extract video information. The URL may be invalid, private, or the video may not be available.'
        }
    else:
        # 2. Process the data into the desired format
        final_result = process_ytdlp_data(raw_data, args.url)

    # 3. Save the final result to a JSON file for the artifact
    output_dir = 'artifacts'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"pinterest_results_{args.session_id}.json")
    
    with open(output_file, 'w') as f:
        json.dump(final_result, f, indent=2)
    
    print(f"Results saved to {output_file}")
    if final_result.get('status') == 'success':
        print("Successfully processed video.")
    else:
        print("Processing failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
