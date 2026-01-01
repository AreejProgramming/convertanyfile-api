import json
import os
import sys
import argparse
import subprocess
import re

def get_image_info(url):
    """
    Uses yt-dlp to extract image information from a Pinterest URL.
    """
    command = [
        'yt-dlp',
        '--no-warnings',
        '--simulate', # Don't download the image
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
        image_data = json.loads(result.stdout)
        return image_data

    except subprocess.CalledProcessError as e:
        print(f"yt-dlp failed with error: {e.stderr}")
        return None
    except json.JSONDecodeError:
        print("Failed to parse JSON output from yt-dlp.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def get_image_url_by_quality(data, quality):
    """
    Extracts the appropriate image URL based on the requested quality.
    """
    if not data:
        return None
    
    # Check for thumbnails in the data
    thumbnails = data.get('thumbnails', [])
    if not thumbnails:
        # If no thumbnails, try to use the main URL
        return data.get('url')
    
    # Sort thumbnails by size (largest first)
    sorted_thumbnails = sorted(thumbnails, key=lambda t: t.get('width', 0) * t.get('height', 0), reverse=True)
    
    if quality == 'original':
        # Return the largest thumbnail
        return sorted_thumbnails[0].get('url') if sorted_thumbnails else data.get('url')
    elif quality == 'large':
        # Find a thumbnail around 736px width
        for thumb in sorted_thumbnails:
            if thumb.get('width', 0) >= 736:
                return thumb.get('url')
        # If not found, return the largest
        return sorted_thumbnails[0].get('url') if sorted_thumbnails else data.get('url')
    elif quality == 'medium':
        # Find a thumbnail around 474px width
        for thumb in sorted_thumbnails:
            if thumb.get('width', 0) >= 474:
                return thumb.get('url')
        # If not found, return the largest
        return sorted_thumbnails[0].get('url') if sorted_thumbnails else data.get('url')
    else:  # thumbnail
        # Find a thumbnail around 236px width
        for thumb in sorted_thumbnails:
            if thumb.get('width', 0) >= 236:
                return thumb.get('url')
        # If not found, return the largest
        return sorted_thumbnails[0].get('url') if sorted_thumbnails else data.get('url')

def process_ytdlp_data(data, original_url, quality):
    """
    Transforms the raw data from yt-dlp into the format expected by the React component.
    """
    if not data:
        return None

    # Extract hashtags from description
    description = data.get('description', '')
    hashtags = [f"#{tag}" for tag in description.split() if tag.startswith('#')][:5]

    # Get the appropriate image URL based on quality
    image_url = get_image_url_by_quality(data, quality)
    
    # Extract pin ID from URL
    pin_id_match = re.search(r'/pin/(\d+)', original_url)
    pin_id = pin_id_match.group(1) if pin_id_match else 'unknown'

    return {
        'status': 'success',
        'data': {
            'id': pin_id,
            'title': data.get('title', 'Pinterest Image'),
            'description': data.get('description', 'Check out this image from Pinterest!'),
            'thumbnail': data.get('thumbnail'),
            'downloadUrl': image_url,
            'author': {
                'name': data.get('uploader', 'Creative User'),
                'username': data.get('uploader_id', '@creativeuser'),
                'avatar': data.get('uploader_avatar', 'https://picsum.photos/seed/avatar/100/100.jpg')
            },
            'board': data.get('playlist', 'Creative Board'),
            'hashtags': hashtags,
            'url': original_url,
            'quality': quality
        }
    }

def main():
    parser = argparse.ArgumentParser(description='Analyze Pinterest image using yt-dlp')
    parser.add_argument('--url', required=True, help='Pinterest URL to analyze')
    parser.add_argument('--session_id', required=True, help='Session ID for tracking')
    parser.add_argument('--quality', default='original', help='Image quality (thumbnail, medium, large, original)')
    
    args = parser.parse_args()
    
    print(f"Analyzing URL: {args.url} with quality: {args.quality}")
    
    # Get raw image data using yt-dlp
    raw_data = get_image_info(args.url)
    
    if not raw_data:
        print("Failed to get image information.")
        # Create a failure object
        final_result = {
            'status': 'error',
            'message': 'Could not extract image information. The URL may be invalid, private, or the image may not be available.'
        }
    else:
        # Process the data into the desired format
        final_result = process_ytdlp_data(raw_data, args.url, args.quality)

    # Save the final result to a JSON file for the artifact
    output_dir = 'artifacts'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"pinterest_results_{args.session_id}.json")
    
    with open(output_file, 'w') as f:
        json.dump(final_result, f, indent=2)
    
    print(f"Results saved to {output_file}")
    if final_result.get('status') == 'success':
        print("Successfully processed image.")
    else:
        print("Processing failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
