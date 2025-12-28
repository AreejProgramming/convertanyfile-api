import os
import json
import time
import sys
import re
import requests
import uuid
import random
import math
from datetime import datetime
from urllib.parse import urlparse
from collections import Counter
import difflib

def generate_session_id():
    return str(uuid.uuid4())

def validate_text(text):
    """
    Validate if input text has content
    """
    return text and text.strip() and len(text.strip()) > 10

def normalize_text(text):
    """
    Normalize text for comparison by removing extra whitespace and converting to lowercase
    """
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    # Convert to lowercase for comparison
    return text.lower()

def split_into_sentences(text):
    """
    Split text into sentences
    """
    # Simple sentence splitting - can be improved with more sophisticated NLP
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]

def calculate_jaccard_similarity(text1, text2):
    """
    Calculate Jaccard similarity between two texts
    """
    words1 = set(normalize_text(text1).split())
    words2 = set(normalize_text(text2).split())
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    if len(union) == 0:
        return 0
    
    return len(intersection) / len(union)

def calculate_cosine_similarity(text1, text2):
    """
    Calculate cosine similarity between two texts
    """
    # Create word frequency vectors
    words1 = normalize_text(text1).split()
    words2 = normalize_text(text2).split()
    
    # Count word frequencies
    counter1 = Counter(words1)
    counter2 = Counter(words2)
    
    # Get all unique words
    all_words = set(words1 + words2)
    
    # Create vectors
    vector1 = [counter1.get(word, 0) for word in all_words]
    vector2 = [counter2.get(word, 0) for word in all_words]
    
    # Calculate dot product
    dot_product = sum(v1 * v2 for v1, v2 in zip(vector1, vector2))
    
    # Calculate magnitudes
    magnitude1 = math.sqrt(sum(v1 ** 2 for v1 in vector1))
    magnitude2 = math.sqrt(sum(v2 ** 2 for v2 in vector2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0
    
    return dot_product / (magnitude1 * magnitude2)

def calculate_sequence_matcher(text1, text2):
    """
    Calculate similarity using difflib's SequenceMatcher
    """
    return difflib.SequenceMatcher(None, normalize_text(text1), normalize_text(text2)).ratio()

def check_sentence_similarity(input_sentence, source_sentence):
    """
    Check similarity between two sentences using multiple methods
    """
    # Calculate different similarity scores
    jaccard = calculate_jaccard_similarity(input_sentence, source_sentence)
    cosine = calculate_cosine_similarity(input_sentence, source_sentence)
    sequence = calculate_sequence_matcher(input_sentence, source_sentence)
    
    # Take the maximum similarity
    similarity = max(jaccard, cosine, sequence)
    
    # Check for exact or near-exact matches
    input_norm = normalize_text(input_sentence)
    source_norm = normalize_text(source_sentence)
    
    if input_norm == source_norm:
        return 1.0  # Exact match
    elif input_norm in source_norm or source_norm in input_norm:
        return 0.9  # One contains the other
    
    return similarity

def get_sample_sources():
    """
    Get a comprehensive list of sample sources for comparison
    """
    return [
        {
            "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "title": "Wikipedia - Artificial Intelligence",
            "content": "Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to the natural intelligence displayed by humans and animals. Leading AI textbooks define the field as the study of 'intelligent agents': any device that perceives its environment and takes actions that maximize its chance of successfully achieving its goals. Colloquially, the term 'artificial intelligence' is often used to describe machines that mimic 'cognitive' functions that humans associate with the human mind, such as 'learning' and 'problem solving'."
        },
        {
            "url": "https://www.techcrunch.com/2023/05/25/ai-and-the-future-of-work",
            "title": "TechCrunch - AI and Future of Work",
            "content": "Artificial intelligence is rapidly transforming the workplace. Many jobs that involve routine tasks are being automated, while new roles are emerging that require AI skills. Workers need to adapt by developing new competencies and embracing lifelong learning. Companies are investing heavily in AI training programs to help their employees transition to new roles that work alongside AI systems."
        },
        {
            "url": "https://www.researchgate.net/publication/Impact_of_social_media",
            "title": "ResearchGate - Impact of Social Media",
            "content": "Social media has fundamentally changed how we communicate and share information. Platforms like Facebook, Twitter, and Instagram have created new ways for people to connect, but they've also raised concerns about privacy, mental health, and the spread of misinformation. Researchers are studying both the positive and negative impacts of these technologies on society."
        },
        {
            "url": "https://scholar.google.com/scholar?q=academic+integrity",
            "title": "Google Scholar - Academic Integrity",
            "content": "Academic integrity is the moral code of academia. It involves values such as avoidance of cheating or plagiarism, maintenance of academic standards, honesty and rigor in research and academic publishing. Students are expected to maintain academic integrity by submitting their own original work and properly citing sources when using others' ideas or words."
        },
        {
            "url": "https://www.jstor.org/stable/23453643",
            "title": "JSTOR - Academic Database",
            "content": "Climate change represents one of the most pressing challenges of our time. Scientific evidence shows that human activities are the primary driver of global warming through the emission of greenhouse gases. The impacts include rising sea levels, extreme weather events, and disruptions to ecosystems. Immediate action is required to mitigate these effects and transition to sustainable practices."
        },
        {
            "url": "https://arxiv.org/abs/2312.10298",
            "title": "arXiv - Academic Papers",
            "content": "Machine learning algorithms have revolutionized many fields including computer vision, natural language processing, and robotics. Deep learning, a subset of machine learning, uses neural networks with multiple layers to progressively extract higher-level features from raw input. This approach has led to breakthroughs in image recognition, language translation, and game playing."
        },
        {
            "url": "https://www.example-blog.com/web-development-trends",
            "title": "Example Blog - Web Development Trends",
            "content": "Web development continues to evolve rapidly with new frameworks and technologies emerging regularly. Modern web applications use responsive design to work across devices, progressive web apps for native-like experiences, and serverless architectures for scalability. Developers must stay current with these trends to build effective and maintainable applications."
        },
        {
            "url": "https://www.nature.com/articles/s41586-023-05693-2",
            "title": "Nature - Scientific Journal",
            "content": "The human brain remains one of the most complex objects in the known universe. With approximately 86 billion neurons and trillions of synaptic connections, it processes information in parallel networks that enable consciousness, memory, and cognition. Understanding how these neural circuits work could lead to breakthroughs in treating neurological disorders and developing artificial intelligence."
        },
        {
            "url": "https://www.bbc.com/news/technology-67892345",
            "title": "BBC News - Technology",
            "content": "Quantum computing represents a paradigm shift in information processing. Unlike classical computers that use bits representing 0 or 1, quantum computers use quantum bits or qubits that can exist in superposition. This property allows quantum computers to process certain problems exponentially faster than classical computers, potentially revolutionizing fields like cryptography and drug discovery."
        },
        {
            "url": "https://www.theverge.com/2023/11/15/23660842/ai-regulation-eu-act",
            "title": "The Verge - AI Regulation",
            "content": "Governments worldwide are grappling with how to regulate artificial intelligence. The European Union's AI Act represents one of the most comprehensive attempts to create a legal framework for AI systems. It categorizes AI applications by risk level and imposes corresponding requirements, from minimal obligations for low-risk systems to strict requirements for high-risk applications."
        }
    ]

def check_plagiarism_accurate(text, exclude_quotes=False, check_type="comprehensive"):
    """
    Check plagiarism using accurate text similarity algorithms
    """
    try:
        # Simulate processing time
        time.sleep(1)
        
        # Extract text characteristics
        text_length = len(text)
        word_count = len(text.split())
        
        # Get input sentences
        input_sentences = split_into_sentences(text)
        
        # Get sample sources
        sources_data = get_sample_sources()
        
        # Track sentence-level matches
        sentence_matches = []
        matched_sentence_indices = set()
        total_similarity = 0
        
        for source in sources_data:
            source_sentences = split_into_sentences(source["content"])
            
            for input_idx, input_sentence in enumerate(input_sentences):
                if input_idx in matched_sentence_indices:
                    continue  # Skip already matched sentences
                    
                for source_idx, source_sentence in enumerate(source_sentences):
                    # Skip if excluding quotes and sentence is in quotes
                    if exclude_quotes and ('"' in input_sentence or "'" in input_sentence):
                        continue
                    
                    similarity = check_sentence_similarity(input_sentence, source_sentence)
                    
                    # Consider it a match if similarity is above threshold
                    if similarity >= 0.7:  # 70% similarity threshold
                        sentence_matches.append({
                            "url": source["url"],
                            "title": source["title"],
                            "similarity": round(similarity * 100, 1),
                            "userTextFragment": input_sentence,
                            "sourceTextFragment": source_sentence,
                            "inputSentenceIndex": input_idx,
                            "sourceSentenceIndex": source_idx,
                            "words": len(input_sentence.split())
                        })
                        total_similarity += similarity
                        matched_sentence_indices.add(input_idx)
                        break  # Move to next input sentence once matched
        
        # Calculate detailed statistics
        total_sentences = len(input_sentences)
        matched_sentences = len(matched_sentence_indices)
        unique_sentences = total_sentences - matched_sentences
        
        # Calculate word-level statistics
        total_words = word_count
        matched_words = sum(match["words"] for match in sentence_matches)
        unique_words = total_words - matched_words
        
        # Calculate overall plagiarism score
        if total_sentences > 0:
            # Base score on percentage of sentences that match
            sentence_match_ratio = matched_sentences / total_sentences
            # Also consider average similarity of matches
            avg_similarity = total_similarity / max(len(sentence_matches), 1)
            # Combine both metrics
            plagiarism_score = round((sentence_match_ratio * 0.6 + avg_similarity * 0.4) * 100, 1)
        else:
            plagiarism_score = 0
        
        # Calculate unique score
        unique_score = round(100 - plagiarism_score, 1)
        
        # Determine risk level
        if plagiarism_score < 15:
            risk_level = "Low"
            risk_color = "#10b981"  # Green
        elif plagiarism_score < 40:
            risk_level = "Medium"
            risk_color = "#f59e0b"  # Yellow
        elif plagiarism_score < 70:
            risk_level = "High"
            risk_color = "#ef4444"  # Red
        else:
            risk_level = "Very High"
            risk_color = "#991b1b"  # Dark Red
        
        # Sort matches by similarity (highest first)
        sentence_matches.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Limit to top matches
        sentence_matches = sentence_matches[:10]
        
        return {
            "score": plagiarism_score,
            "uniqueScore": unique_score,
            "riskLevel": risk_level,
            "riskColor": risk_color,
            "wordCount": total_words,
            "charCount": text_length,
            "totalSentences": total_sentences,
            "matchedSentences": matched_sentences,
            "uniqueSentences": unique_sentences,
            "matchedWords": matched_words,
            "uniqueWords": unique_words,
            "sources": sentence_matches,
            "analysis": {
                "sentenceMatchPercentage": round((matched_sentences / total_sentences) * 100, 1) if total_sentences > 0 else 0,
                "wordMatchPercentage": round((matched_words / total_words) * 100, 1) if total_words > 0 else 0,
                "averageSimilarity": round(total_similarity / max(len(sentence_matches), 1) * 100, 1) if sentence_matches else 0
            }
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
    
    # Get additional options
    exclude_quotes = os.environ.get("EXCLUDE_QUOTES", "false").lower() == "true"
    check_type = os.environ.get("CHECK_TYPE", "comprehensive")
    
    print(f"Starting plagiarism check for text of length {len(text)}")
    print(f"Session ID: {session_id}")
    print(f"Exclude quotes: {exclude_quotes}")
    print(f"Check type: {check_type}")
    
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
        
        # Check plagiarism using accurate algorithm
        print(f"Checking plagiarism for text of length {len(text)}")
        plagiarism_data = check_plagiarism_accurate(text, exclude_quotes, check_type)
        
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
