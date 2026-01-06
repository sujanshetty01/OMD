import re
# Trigger reload for model load
import spacy
from typing import List, Optional

# Try to load spacy, handle if missing
try:
    nlp = spacy.load("en_core_web_lg")
except:
    nlp = None

# --------------------------
# PATTERNS & HEURISTICS
# --------------------------

SENSITIVE_NAMES = [
    "ssn", "social_security", "social_security_number", "passport", "credit_card", "cc_num", "dob", "birth_date", "birth", "pwd", "password"
]

PII_NAMES = [
    "first_name", "last_name", "full_name", "email", "phone", "address", "zip_code"
]

REGEX_PATTERNS = {
    "PII.Sensitive.SSN": r"^\d{3}-\d{2}-\d{4}$",
    "PII.Contact.Email": r"[^@]+@[^@]+\.[^@]+",
    # Flexible Phone Regex: (123) 456-7890, 123-456-7890, 123.456.7890, +1 123 456 7890
    "PII.Contact.Phone": r"^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$",
    "PII.Sensitive.CreditCard": r"^\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}$"
}

# --------------------------
# LOGIC
# --------------------------

def classify_column_content(series) -> (str, float):
    """
    Returns (BestTag, Confidence) based on content check (Regex).
    """
    # Sample non-null values
    values = series.dropna().astype(str).tolist()
    if not values:
        return None, 0.0
    
    sample_size = len(values)
    
    # Check each regex
    best_tag = None
    best_score = 0.0
    
    for tag, pattern in REGEX_PATTERNS.items():
        matches = sum(1 for v in values if re.match(pattern, v))
        score = matches / sample_size
        
        if score > best_score:
            best_score = score
            best_tag = tag
            
    # Heuristic: If > 80% match, it's a strong signal
    if best_score > 0.8:
        return best_tag, best_score
        
    return None, 0.0

def classify_column_name(col_name: str) -> (str, float):
    """
    Returns (BestTag, Confidence) based on name (NLP/Fuzzy).
    """
    clean = col_name.lower().strip()
    
    # 1. Exact/Partial keyword match
    if any(k in clean for k in SENSITIVE_NAMES):
        return "PII.Sensitive", 0.9
        
    if any(k in clean for k in PII_NAMES):
        return "PII.Contact", 0.8 # Generic PII
        
    # 2. NLP Embeddings (Semantic Similarity)
    if nlp:
        token = nlp(clean)
        if token.has_vector: # Ensure word has a vector
            # Check Sensitive
            for sens in SENSITIVE_NAMES:
                sim = token.similarity(nlp(sens))
                if sim > 0.7:
                     return "PII.Sensitive", sim
            
            # Check PII
            for pii in PII_NAMES:
                sim = token.similarity(nlp(pii))
                if sim > 0.7:
                    return "PII.Contact", sim # Generic PII
        
    return None, 0.0

def classify(col_name: str, col_series) -> dict:
    """
    Main entry point.
    Returns: {tag: str, confidence: float, source: str}
    """
    # 1. Content Analysis (Priority)
    content_tag, content_conf = classify_column_content(col_series)
    
    # 2. Name Analysis
    name_tag, name_conf = classify_column_name(col_name)
    
    # 3. Decision
    # If content is strong, trust it.
    if content_tag and content_conf > 0.85:
        return {
            "tag": content_tag,
            "confidence": content_conf,
            "source": "CONTENT"
        }
    
    # If name is strong and no conflicting strong content
    if name_tag and name_conf > 0.7:
        return {
            "tag": name_tag,
            "confidence": name_conf,
            "source": "NLP"
        }
        
    # Weak content match?
    if content_tag and content_conf > 0.5:
         return {
            "tag": content_tag,
            "confidence": content_conf,
            "source": "CONTENT_WEAK"
        }

    return None
