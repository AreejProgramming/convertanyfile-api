import os
import json
import time
import sys
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
import uuid

def generate_session_id():
    return str(uuid.uuid4())

def validate_url(url):
    """
    Validate if input is a valid URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def fetch_content_from_url(url):
    """
    Fetch text content from a URL
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            # Extract text content from HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
                
            # Get text content
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        else:
            return None
    except Exception as e:
        print(f"Error fetching content from URL: {str(e)}")
        return None

def analyze_keyword_density(content):
    """
    Analyze keyword density in the provided content
    """
    # Stop words list
    stop_words = set([
        'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'him', 'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'just', 'me', 'more', 'most', 'my', 'myself', 'no', 'nor', 'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same', 'she', 'should', 'so', 'some', 'such', 'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'we', 'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'with', 'you', 'your', 'yours', 'yourself', 'yourselves'
    ])
    
    # Extract words
    words = re.findall(r'\b\w+\b', content.lower())
    total_words = len(words)
    
    # Count word frequency (excluding stop words and short words)
    word_frequency = {}
    for word in words:
        if not stop_words.has(word) and len(word) > 2:
            word_frequency[word] = word_frequency.get(word, 0) + 1
    
    # Calculate density and sort by density
    keywords = []
    for word, count in word_frequency.items():
        density = (count / total_words) * 100
        keywords.append({
            "word": word,
            "count": count,
            "density": round(density, 2)
        })
    
    # Sort by density (descending)
    keywords.sort(key=lambda x: x["density"], reverse=True)
    
    return {
        "totalWords": total_words,
        "uniqueKeywords": len(keywords),
        "textLength": len(content),
        "keywords": keywords[:50]  # Return top 50 keywords
    }

def check_keyword_density(content):
    """
    Main function to check keyword density
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting keyword density analysis")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Analyzing keyword density...",
        "session_id": session_id
    }
    
    try:
        text_to_analyze = content
        
        # Check if content is a URL
        if validate_url(content):
            print(f"Fetching content from URL: {content}")
            text_to_analyze = fetch_content_from_url(content)
            
            if not text_to_analyze:
                raise ValueError("Failed to fetch content from the provided URL")
        
        # Validate that we have content to analyze
        if not text_to_analyze or not text_to_analyze.strip():
            raise ValueError("No content to analyze")
        
        # Analyze keyword density
        print(f"Analyzing keyword density for content of length {len(text_to_analyze)}")
        keyword_data = analyze_keyword_density(text_to_analyze)
        
        # Create final results
        results = {
            "status": "success",
            "timestamp": time.time(),
            "session_id": session_id,
            "data": keyword_data
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
    
    # Always write results to file, even if there was an error
    try:
        with open('results.json', 'w') as f:
            json.dump(results, f)
        print("Results successfully written to results.json")
    except Exception as file_error:
        print(f"ERROR writing results file: {str(file_error)}")
        # Try to write to a different location as fallback
        try:
            with open(f'/tmp/results_{session_id}.json', 'w') as f:
                json.dump(results, f)
            print(f"Results written to fallback location: /tmp/results_{session_id}.json")
        except Exception as fallback_error:
            print(f"ERROR writing to fallback location: {str(fallback_error)}")
    
    # Always output the results, even if there was an error
    print(f"results={json.dumps(results)}")
    return results

if __name__ == "__main__":
    content = os.environ.get("CONTENT")
    if not content:
        print("ERROR: CONTENT environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "CONTENT environment variable not set.",
            "session_id": os.environ.get("SESSION_ID", "unknown")
        }
        
        # Write error results to file
        try:
            with open('results.json', 'w') as f:
                json.dump(error_result, f)
            print("Error results written to results.json")
        except Exception as file_error:
            print(f"ERROR writing error results file: {str(file_error)}")
        
        print(f"results={json.dumps(error_result)}")
        sys.exit(1)
        
    keyword_results = check_keyword_density(content)
    
    # The results are already printed in the function
    sys.exit(0)
