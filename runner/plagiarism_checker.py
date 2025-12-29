import os
import json
import time
import sys
import re
import requests
import uuid
import random
import math
import hashlib
from datetime import datetime
from urllib.parse import urlparse, quote
from collections import Counter
import difflib
import html

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
    # Remove HTML tags if any
    text = re.sub(r'<[^>]+>', '', text)
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    # Convert to lowercase for comparison
    return text.lower()

def split_into_sentences(text):
    """
    Split text into sentences
    """
    # More sophisticated sentence splitting
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def split_into_phrases(text, min_length=8, max_length=12):
    """
    Split text into phrases of varying lengths for more comprehensive checking
    """
    words = text.split()
    phrases = []
    
    # Limit the number of phrases to prevent excessive processing
    max_phrases = min(50, len(words))
    
    # Generate phrases of different lengths
    for length in range(min_length, max_length + 1):
        for i in range(len(words) - length + 1):
            if len(phrases) >= max_phrases:
                break
            phrase = ' '.join(words[i:i+length])
            phrases.append(phrase)
    
    return phrases

def calculate_text_hash(text):
    """
    Calculate a hash for the text to identify exact matches
    """
    return hashlib.md5(normalize_text(text).encode()).hexdigest()

def is_common_phrase(phrase):
    """
    Check if a phrase is too common to be considered plagiarism
    """
    # Expanded list of common phrases that should not be considered plagiarism
    common_phrases = [
        "in order to", "as well as", "according to", "in addition to", 
        "due to the fact", "in the case of", "on the other hand", 
        "for the purpose of", "in the context of", "with respect to",
        "in terms of", "on the basis of", "in the absence of",
        "in the presence of", "in the direction of", "in the vicinity of",
        "in the middle of", "at the same time", "in the form of",
        "in the event of", "in the process of", "in the course of",
        "in the light of", "in the wake of", "in the face of",
        "in the name of", "in the interest of", "in the spirit of",
        "in the sense of", "in the field of", "in the area of",
        "in the realm of", "in the world of", "in the domain of",
        "in the scope of", "in the range of", "in the frame of",
        "it is important to note", "it should be noted that", 
        "it is worth mentioning", "it is interesting to note",
        "there are a number of", "a wide range of", "a variety of",
        "a number of factors", "a great deal of", "a lot of",
        "in recent years", "over the past few years", "in the last decade",
        "in the 21st century", "in the modern era", "in today's world",
        "in this day and age", "in the current climate", "at the present time",
        "on the one hand", "on the other hand", "in contrast",
        "by comparison", "in comparison", "in the same way",
        "in a similar way", "in a similar vein", "along the same lines",
        "in the long run", "in the short term", "in the foreseeable future",
        "in the coming years", "in the years to come", "moving forward",
        "looking ahead", "going forward", "in the future"
    ]
    
    normalized_phrase = normalize_text(phrase)
    return normalized_phrase in common_phrases

def calculate_ngram_similarity(text1, text2, n=4):
    """
    Calculate n-gram similarity between two texts
    """
    def get_ngrams(text, n):
        words = normalize_text(text).split()
        ngrams = []
        for i in range(len(words) - n + 1):
            ngrams.append(' '.join(words[i:i+n]))
        return ngrams
    
    ngrams1 = get_ngrams(text1, n)
    ngrams2 = get_ngrams(text2, n)
    
    if not ngrams1 or not ngrams2:
        return 0
    
    set1 = set(ngrams1)
    set2 = set(ngrams2)
    
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    
    return len(intersection) / len(union) if union else 0

def calculate_sequence_similarity(text1, text2):
    """
    Calculate sequence similarity using difflib
    """
    return difflib.SequenceMatcher(None, normalize_text(text1), normalize_text(text2)).ratio()

def check_exact_match(input_text, source_text):
    """
    Check for exact matches between input and source text
    """
    input_norm = normalize_text(input_text)
    source_norm = normalize_text(source_text)
    
    if input_norm == source_norm:
        return 1.0
    
    # Check if input contains source or vice versa
    if input_norm in source_norm:
        return 0.95
    if source_norm in input_norm:
        return 0.95
    
    return 0

def check_phrase_similarity(input_phrases, source_phrases):
    """
    Check similarity between sets of phrases
    """
    max_similarity = 0
    best_input_phrase = ""
    best_source_phrase = ""
    
    # Limit the number of phrase comparisons to prevent timeouts
    max_comparisons = 300
    comparison_count = 0
    
    for input_phrase in input_phrases:
        # Skip common phrases
        if is_common_phrase(input_phrase):
            continue
            
        for source_phrase in source_phrases:
            if comparison_count >= max_comparisons:
                break
                
            # Skip common phrases
            if is_common_phrase(source_phrase):
                continue
                
            # Check for exact match first
            if normalize_text(input_phrase) == normalize_text(source_phrase):
                return 1.0, input_phrase, source_phrase
            
            # Calculate similarity
            similarity = calculate_sequence_similarity(input_phrase, source_phrase)
            
            if similarity > max_similarity:
                max_similarity = similarity
                best_input_phrase = input_phrase
                best_source_phrase = source_phrase
                
            comparison_count += 1
        
        if comparison_count >= max_comparisons:
            break
    
    return max_similarity, best_input_phrase, best_source_phrase

def search_web_sources(query, max_results=5):
    """
    Search for web sources related to the query
    Note: This is a placeholder function. In a real implementation, 
    you would use a search API like Google, Bing, or DuckDuckGo
    """
    # This is a mock implementation
    # In a real scenario, you would make API calls to search engines
    
    # Extract key phrases from the query to simulate search results
    words = query.split()
    key_phrases = []
    
    # Create 3-5 word phrases
    for i in range(len(words) - 2):
        if i < 10:  # Limit to first 10 phrases
            phrase = ' '.join(words[i:i+3])
            if not is_common_phrase(phrase):
                key_phrases.append(phrase)
    
    # Generate mock search results
    results = []
    for i, phrase in enumerate(key_phrases[:max_results]):
        # Create a mock URL and title
        url = f"https://example-website-{i+1}.com/article/{quote(phrase.replace(' ', '-'))}"
        title = f"Article about {phrase}"
        
        # Create mock content that includes the phrase
        content = f"This is an example article about {phrase}. In this article, we discuss various aspects of {phrase} and its implications. Research has shown that {phrase} plays an important role in many contexts. Scientists have been studying {phrase} for decades, and new discoveries are made regularly. The impact of {phrase} on society cannot be underestimated."
        
        results.append({
            "url": url,
            "title": title,
            "content": content
        })
    
    return results

def get_academic_sources():
    """
    Get a list of academic sources for comparison
    """
    return [
        {
            "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "title": "Wikipedia - Artificial Intelligence",
            "content": "Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to the natural intelligence displayed by humans and animals. Leading AI textbooks define the field as the study of 'intelligent agents': any device that perceives its environment and takes actions that maximize its chance of successfully achieving its goals. Colloquially, the term 'artificial intelligence' is often used to describe machines that mimic 'cognitive' functions that humans associate with the human mind, such as 'learning' and 'problem solving'. AI applications include advanced web search engines, recommendation systems, understanding human speech, self-driving cars, and competing at the highest level in strategic games."
        },
        {
            "url": "https://www.researchgate.net/publication/Impact_of_social_media",
            "title": "ResearchGate - Impact of Social Media",
            "content": "Social media has fundamentally changed how we communicate and share information. Platforms like Facebook, Twitter, and Instagram have created new ways for people to connect, but they've also raised concerns about privacy, mental health, and the spread of misinformation. Researchers are studying both the positive and negative impacts of these technologies on society. The algorithmic nature of these platforms can create echo chambers and filter bubbles that reinforce existing beliefs."
        },
        {
            "url": "https://scholar.google.com/scholar?q=academic+integrity",
            "title": "Google Scholar - Academic Integrity",
            "content": "Academic integrity is the moral code of academia. It involves values such as avoidance of cheating or plagiarism, maintenance of academic standards, honesty and rigor in research and academic publishing. Students are expected to maintain academic integrity by submitting their own original work and properly citing sources when using others' ideas or words. Violations of academic integrity can result in severe consequences including failure, suspension, or expulsion from educational institutions."
        },
        {
            "url": "https://www.jstor.org/stable/23453643",
            "title": "JSTOR - Academic Database",
            "content": "Climate change represents one of the most pressing challenges of our time. Scientific evidence shows that human activities are the primary driver of global warming through the emission of greenhouse gases. The impacts include rising sea levels, extreme weather events, and disruptions to ecosystems. Immediate action is required to mitigate these effects and transition to sustainable practices. The Paris Agreement and other international efforts aim to limit global temperature rise to avoid catastrophic consequences."
        },
        {
            "url": "https://arxiv.org/abs/2312.10298",
            "title": "arXiv - Academic Papers",
            "content": "Machine learning algorithms have revolutionized many fields including computer vision, natural language processing, and robotics. Deep learning, a subset of machine learning, uses neural networks with multiple layers to progressively extract higher-level features from raw input. This approach has led to breakthroughs in image recognition, language translation, and game playing. Transformer architectures have particularly advanced the field of natural language processing, enabling models like GPT to generate human-like text."
        }
    ]

def get_web_sources():
    """
    Get a list of web sources for comparison
    """
    return [
        {
            "url": "https://www.techcrunch.com/2023/05/25/ai-and-the-future-of-work",
            "title": "TechCrunch - AI and Future of Work",
            "content": "Artificial intelligence is rapidly transforming the workplace. Many jobs that involve routine tasks are being automated, while new roles are emerging that require AI skills. Workers need to adapt by developing new competencies and embracing lifelong learning. Companies are investing heavily in AI training programs to help their employees transition to new roles that work alongside AI systems. The future of work will likely involve humans collaborating with AI systems rather than being replaced by them."
        },
        {
            "url": "https://www.example-blog.com/web-development-trends",
            "title": "Example Blog - Web Development Trends",
            "content": "Web development continues to evolve rapidly with new frameworks and technologies emerging regularly. Modern web applications use responsive design to work across devices, progressive web apps for native-like experiences, and serverless architectures for scalability. Developers must stay current with these trends to build effective and maintainable applications. The rise of JavaScript frameworks like React, Vue, and Angular has transformed front-end development."
        },
        {
            "url": "https://www.bbc.com/news/technology-67892345",
            "title": "BBC News - Technology",
            "content": "Quantum computing represents a paradigm shift in information processing. Unlike classical computers that use bits representing 0 or 1, quantum computers use quantum bits or qubits that can exist in superposition. This property allows quantum computers to process certain problems exponentially faster than classical computers, potentially revolutionizing fields like cryptography and drug discovery. Major technology companies and governments are investing heavily in quantum research to gain competitive advantages."
        },
        {
            "url": "https://www.theverge.com/2023/11/15/23660842/ai-regulation-eu-act",
            "title": "The Verge - AI Regulation",
            "content": "Governments worldwide are grappling with how to regulate artificial intelligence. The European Union's AI Act represents one of the most comprehensive attempts to create a legal framework for AI systems. It categorizes AI applications by risk level and imposes corresponding requirements, from minimal obligations for low-risk systems to strict requirements for high-risk applications. The challenge is balancing innovation with protection against potential harms."
        },
        {
            "url": "https://www.nytimes.com/2023/10/12/technology/cryptocurrency-regulation.html",
            "title": "New York Times - Cryptocurrency",
            "content": "Cryptocurrency continues to disrupt traditional financial systems despite regulatory challenges. Bitcoin and other digital assets offer decentralized alternatives to government-issued currencies, but their volatility and use in illicit activities have drawn scrutiny from regulators worldwide. Blockchain technology, which underlies most cryptocurrencies, has applications beyond finance including supply chain management, digital identity verification, and smart contracts."
        }
    ]

def check_plagiarism_comprehensive(text, exclude_quotes=False, check_type="comprehensive"):
    """
    Check plagiarism using comprehensive text analysis
    """
    try:
        # Track start time for timeout handling
        start_time = time.time()
        max_processing_time = 240  # 4 minutes to stay well under the 5-minute timeout
        
        # Extract text characteristics
        text_length = len(text)
        word_count = len(text.split())
        
        # Get input sentences and phrases
        input_sentences = split_into_sentences(text)
        input_phrases = split_into_phrases(text)
        
        # Get sources based on check type
        sources_data = []
        
        if check_type in ["comprehensive", "academic"]:
            sources_data.extend(get_academic_sources())
        
        if check_type in ["comprehensive", "web"]:
            sources_data.extend(get_web_sources())
        
        # For comprehensive checks, also search for relevant web sources
        if check_type == "comprehensive" and word_count > 50:
            # Extract key phrases from the text to search for
            key_phrases = []
            for sentence in input_sentences[:5]:  # Use first 5 sentences
                words = sentence.split()
                for i in range(len(words) - 2):
                    if len(key_phrases) < 5:  # Limit to 5 key phrases
                        phrase = ' '.join(words[i:i+3])
                        if not is_common_phrase(phrase) and len(phrase) > 15:
                            key_phrases.append(phrase)
            
            # Search for web sources based on key phrases
            for phrase in key_phrases:
                web_sources = search_web_sources(phrase, max_results=2)
                sources_data.extend(web_sources)
        
        # Track matches at different levels
        exact_matches = []
        sentence_matches = []
        phrase_matches = []
        
        # Track which parts of the input have been matched
        matched_sentence_indices = set()
        matched_phrase_indices = set()
        
        # Limit the number of sources to check based on text length
        max_sources_to_check = min(15, len(sources_data))
        if word_count < 100:
            max_sources_to_check = min(8, len(sources_data))
        
        # Shuffle sources to get a diverse sample
        random.shuffle(sources_data)
        
        for source in sources_data[:max_sources_to_check]:
            # Check if we're approaching the timeout
            if time.time() - start_time > max_processing_time:
                print(f"Approaching timeout, stopping analysis after checking {len(exact_matches) + len(sentence_matches) + len(phrase_matches)} matches")
                break
                
            source_sentences = split_into_sentences(source["content"])
            source_phrases = split_into_phrases(source["content"])
            
            # Check for exact matches first
            exact_match_score = check_exact_match(text, source["content"])
            if exact_match_score >= 0.95:
                exact_matches.append({
                    "url": source["url"],
                    "title": source["title"],
                    "similarity": round(exact_match_score * 100, 1),
                    "userTextFragment": text,
                    "sourceTextFragment": source["content"],
                    "matchType": "Exact"
                })
                continue  # If exact match found, no need to check further
            
            # Check sentence-level matches
            for input_idx, input_sentence in enumerate(input_sentences):
                if input_idx in matched_sentence_indices:
                    continue  # Skip already matched sentences
                
                # Skip short sentences (less than 10 words) as they're more likely to be common phrases
                if len(input_sentence.split()) < 10:
                    continue
                
                # Check if we're approaching the timeout
                if time.time() - start_time > max_processing_time:
                    break
                
                for source_idx, source_sentence in enumerate(source_sentences):
                    # Skip if excluding quotes and sentence is in quotes
                    if exclude_quotes and ('"' in input_sentence or "'" in input_sentence):
                        continue
                    
                    # Skip short sentences
                    if len(source_sentence.split()) < 10:
                        continue
                    
                    # Calculate similarity using multiple methods
                    ngram_sim = calculate_ngram_similarity(input_sentence, source_sentence, n=4)
                    sequence_sim = calculate_sequence_similarity(input_sentence, source_sentence)
                    
                    # Take the maximum similarity
                    similarity = max(ngram_sim, sequence_sim)
                    
                    # Threshold for sentence similarity
                    if similarity >= 0.7:  # 70% similarity threshold
                        sentence_matches.append({
                            "url": source["url"],
                            "title": source["title"],
                            "similarity": round(similarity * 100, 1),
                            "userTextFragment": input_sentence,
                            "sourceTextFragment": source_sentence,
                            "inputSentenceIndex": input_idx,
                            "sourceSentenceIndex": source_idx,
                            "words": len(input_sentence.split()),
                            "matchType": "Sentence"
                        })
                        matched_sentence_indices.add(input_idx)
                        break  # Move to next input sentence once matched
            
            # Check phrase-level matches for any remaining unmatched content
            phrase_similarity, best_input_phrase, best_source_phrase = check_phrase_similarity(input_phrases, source_phrases)
            if phrase_similarity >= 0.8:  # 80% similarity threshold for phrases
                phrase_matches.append({
                    "url": source["url"],
                    "title": source["title"],
                    "similarity": round(phrase_similarity * 100, 1),
                    "userTextFragment": best_input_phrase,
                    "sourceTextFragment": best_source_phrase,
                    "words": len(best_input_phrase.split()),
                    "matchType": "Phrase"
                })
        
        # Combine all matches, prioritizing exact matches
        all_matches = exact_matches + sentence_matches + phrase_matches
        
        # Calculate detailed statistics
        total_sentences = len(input_sentences)
        matched_sentences = len(matched_sentence_indices)
        unique_sentences = total_sentences - matched_sentences
        
        # Calculate word-level statistics
        total_words = word_count
        matched_words = sum(match.get("words", 0) for match in all_matches)
        unique_words = total_words - matched_words
        
        # Calculate overall plagiarism score with improved algorithm
        if total_sentences > 0:
            # Base score on percentage of sentences that match
            sentence_match_ratio = matched_sentences / total_sentences
            
            # Also consider average similarity of matches
            avg_similarity = sum(match["similarity"] for match in all_matches) / max(len(all_matches), 1) / 100
            
            # Weight exact matches more heavily
            exact_match_weight = len(exact_matches) * 0.5
            
            # Only consider significant matches (more than 15 words)
            significant_matches = [m for m in all_matches if m.get("words", 0) > 15]
            significant_match_ratio = len(significant_matches) / total_sentences if total_sentences > 0 else 0
            
            # Combine all metrics with more weight on significant matches
            plagiarism_score = round((sentence_match_ratio * 0.3 + avg_similarity * 0.2 + exact_match_weight + significant_match_ratio * 0.5) * 100, 1)
            
            # Cap at 100%
            plagiarism_score = min(plagiarism_score, 100)
        else:
            plagiarism_score = 0
        
        # Calculate unique score
        unique_score = round(100 - plagiarism_score, 1)
        
        # Determine risk level with adjusted thresholds
        if plagiarism_score < 10:
            risk_level = "Low"
            risk_color = "#10b981"  # Green
        elif plagiarism_score < 25:
            risk_level = "Medium"
            risk_color = "#f59e0b"  # Yellow
        elif plagiarism_score < 50:
            risk_level = "High"
            risk_color = "#ef4444"  # Red
        else:
            risk_level = "Very High"
            risk_color = "#991b1b"  # Dark Red
        
        # Sort matches by similarity (highest first)
        all_matches.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Limit to top matches
        all_matches = all_matches[:10]
        
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
            "sources": all_matches,
            "analysis": {
                "sentenceMatchPercentage": round((matched_sentences / total_sentences) * 100, 1) if total_sentences > 0 else 0,
                "wordMatchPercentage": round((matched_words / total_words) * 100, 1) if total_words > 0 else 0,
                "averageSimilarity": round(sum(match["similarity"] for match in all_matches) / max(len(all_matches), 1), 1) if all_matches else 0,
                "exactMatches": len(exact_matches)
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
        
        # Check plagiarism using comprehensive algorithm
        print(f"Checking plagiarism for text of length {len(text)}")
        plagiarism_data = check_plagiarism_comprehensive(text, exclude_quotes, check_type)
        
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
