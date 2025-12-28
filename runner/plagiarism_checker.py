import os
import json
import time
import sys
import re
import requests
import uuid
import random
from datetime import datetime
from urllib.parse import urlparse

def generate_session_id():
    return str(uuid.uuid4())

def validate_text(text):
    """
    Validate if input text has content
    """
    return text and text.strip() and len(text.strip()) > 10

def check_plagiarism_smallseo(text, options=None):
    """
    Check plagiarism using SmallSEOTools API simulation
    """
    try:
        # Simulate API call delay
        time.sleep(1)
        
        # Extract text characteristics
        text_length = len(text)
        word_count = len(text.split())
        
        # Calculate a mock plagiarism score
        base_score = 0
        
        # Factors that might increase plagiarism score
        if word_count < 50:
            base_score += 5  # Short texts might be quotes
        if any(c in text.lower() for c in ['according to', 'as mentioned', 'in conclusion']):
            base_score += 3  # Common academic phrases
        if text.count('"') > 10:
            base_score += 2  # Many quotes might indicate citations
            
        # Add some randomness
        score = min(base_score + random.randint(0, 15), 35)
        
        # Generate mock sources
        sources = []
        num_sources = 0 if score < 15 else random.randint(1, 3)
        
        # Mock source database
        mock_sources = [
            {"url": "https://en.wikipedia.org/wiki/Artificial_intelligence", "title": "Wikipedia - Artificial Intelligence"},
            {"url": "https://www.techcrunch.com/2023/05/25/ai-and-the-future-of-work", "title": "TechCrunch - AI and Future of Work"},
            {"url": "https://www.example-blog.com/web-development-trends", "title": "Example Blog - Web Development Trends"},
            {"url": "https://www.researchgate.net/publication/Impact_of_social_media", "title": "ResearchGate - Impact of Social Media"},
            {"url": "https://scholar.google.com/scholar?q=academic+integrity", "title": "Google Scholar - Academic Integrity"},
            {"url": "https://www.jstor.org/stable/23453643", "title": "JSTOR - Academic Database"},
            {"url": "https://arxiv.org/abs/2312.10298", "title": "arXiv - Academic Papers"}
        ]
        
        for i in range(num_sources):
            source = random.choice(mock_sources)
            
            # Extract a random fragment from the text
            sentences = re.split(r'[.!?]+', text)
            if sentences and len(sentences) > 0:
                fragment = random.choice(sentences)[:30] + "..."
            else:
                fragment = "Our analysis shows a match with a similar sentence structure on this page..."
                
            similarity = random.randint(5, 20)
            sources.append({
                "url": source["url"],
                "title": source["title"],
                "similarity": similarity,
                "userTextFragment": fragment,
                "sourceTextFragment": "Our analysis shows a match with a similar sentence structure on this page..."
            })
        
        return {
            "score": score,
            "wordCount": word_count,
            "charCount": text_length,
            "sources": sources
        }
        
    except Exception as e:
        print(f"Error checking plagiarism: {str(e)}")
        return {"error": str(e)}

def check_plagiarism_service(text):
    """
    Main function to check plagiarism
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting plagiarism check for text of length {len(text)}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Analyzing text for plagiarism...",
        "session_id": session_id
    }
    
    try:
        # Validate text
        if not validate_text(text):
            raise ValueError("Text is too short or empty")
        
        # Check plagiarism
        print(f"Checking plagiarism for text of length {len(text)}")
        plagiarism_data = check_plagiarism_smallseo(text)
        
        if "error" in plagiarism_data:
            raise ValueError(plagiarism_data["error"])
        
        # Create final results
        results = {
            "status": "success",
            "timestamp": time.time(),
            "session_id": session_id,
            "data": plagiarism_data
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
    text = os.environ.get("TEXT")
    if not text:
        print("ERROR: TEXT environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "TEXT environment variable not set.",
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
        
    plagiarism_results = check_plagiarism_service(text)
    
    # The results are already printed in the function
    sys.exit(0)
