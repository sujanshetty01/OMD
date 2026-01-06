from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..integration.vector_client import VectorClient
from ..integration.om_client import OMClient

router = APIRouter()

# ... (imports remain)

# Global In-Memory Context Store for Conversation History
# Format: {client_id: {"last_entity": "Name"}}
CONTEXT_STORE = {}

class QueryRequest(BaseModel):
    prompt: str
    client_id: str = "default"

@router.post("/query")
async def ai_query(request: QueryRequest):
    """
    Promptiq AI engine: 
    Consumes from VectorDB, Metadata store, and raw store to answer.
    """
    vector_client = VectorClient()
    
    # --------------------------
    # 0. Context & Pronoun Logic
    # --------------------------
    raw_prompt = request.prompt
    enhanced_prompt = raw_prompt
    
    # Detect pronouns
    pronouns = {"he", "him", "his", "she", "her", "hers", "it", "they", "them", "their", "this", "that"}
    words = set(raw_prompt.lower().split())
    has_pronoun = not words.isdisjoint(pronouns)
    
    # Retrieve history
    history = CONTEXT_STORE.get(request.client_id, {})
    last_entity = history.get("last_entity")
    
    forced_keywords = []

    if has_pronoun and last_entity:
        # Augment the prompt
        enhanced_prompt = f"{raw_prompt} regarding {last_entity}"
        forced_keywords.append(last_entity.lower())
        print(f"DEBUG: Context applied. Rewrote '{raw_prompt}' to '{enhanced_prompt}'")

    # 1. Semantic Search Context (Increased context window)
    semantic_results = vector_client.search(enhanced_prompt, n_results=10)
    
    context_docs = semantic_results.get("documents", [[]])[0]
    metadata = semantic_results.get("metadatas", [[]])[0]
    
    if not context_docs:
        return {
            "answer": "I scanned the knowledge base but couldn't find specific data matching your query.",
            "sources": []
        }
    
    # 2. Augment with Metadata
    source_dataset = metadata[0]["source"] if metadata else None
    tags = []
    if source_dataset:
        try:
            om = OMClient()
            ds = om.get_dataset(f"local_files.uploads.default.{source_dataset.replace('.', '_').replace('-', '_')}")
            if ds:
                tag_set = set()
                for col in ds["columns"]:
                    for t in col["tags"]:
                        tag_set.add(t["tag_fqn"])
                tags = list(tag_set)
        except:
            pass # Fail gracefully on metadata fetch

    # 3. "Fine-tuned" Reasoning & Filtering
    prompt_lower = enhanced_prompt.lower()
    
    # Basic stop words to ignore (including common schema keys to avoid wildcard matching)
    stop_words = {
        "who", "is", "are", "the", "a", "an", "tell", "me", "about", "find", "search", "details", "for", 
        "please", "dataset", "get", "of", "in", "what", "where", "when", "give", "show", "list",
        "email", "address", "name", "full", "phone", "cell", "number", "id", "user", "social", 
        "security", "count", "order", "notes", "row", "record",
        # Add pronouns to stop words so we don't filter by "his" if we have "Charlie"
        "he", "him", "his", "she", "her", "hers", "it"
    }
    
    # Build robust keyword list
    keywords = [w for w in prompt_lower.split() if w not in stop_words and len(w) > 1]
    
    # 4. Filter & Deduplicate Documents
    filtered_docs = []
    seen_content = set()
    
    # Track which keywords are actually found in the raw context
    found_keywords_in_context = set()
    
    # Pre-scan context to see what we have
    all_context_text = " ".join(context_docs).lower()
    missing_keywords = [k for k in keywords if k not in all_context_text]

    for i, doc in enumerate(context_docs):
        doc_lower = doc.lower()
        is_relevant = True
        
        # If we have keywords, ensure match (Strict Mode)
        if keywords:
            # 1. Check Forced (Context) - MUST exist
            if forced_keywords:
                if not any(fk in doc_lower for fk in forced_keywords):
                    is_relevant = False
            
            # 2. Check General Keywords
            # If a keyword is completely missing from ALL context (e.g. "female" not in dataset),
            # we shouldn't filter by it on a per-doc basis, otherwise we get 0 results.
            # We only filter by keywords that actually EXIST in the retrieved context context.
            else:
                 # Only strict filter on keywords that are known to exist in the corpus subset
                 context_relevant_keywords = [k for k in keywords if k not in missing_keywords]
                 if context_relevant_keywords:
                    # Switch to ALL (AND logic) for precision. 
                    # "Noise Cancelling" should not match "Noise" alone.
                    if not all(k in doc_lower for k in context_relevant_keywords):
                        is_relevant = False
        
        # Deduplication check
        parts = doc.split("|", 1)
        content_only = parts[1] if len(parts) > 1 else parts[0]
        content_signature = " ".join(content_only.split())
        
        if is_relevant and content_signature not in seen_content:
            seen_content.add(content_signature)
            filtered_docs.append(doc)

    count = len(filtered_docs)
    
    # ... (Context extraction remains same) ...
    # --------------------------
    # 5. Extract Context for Next Turn
    # --------------------------
    found_primary_entity = None
    if filtered_docs:
        top_doc = filtered_docs[0]
        parts = top_doc.split(" | ")
        for point in parts:
             if ":" in point:
                k, v = point.split(":", 1)
                if "name" in k.lower() and len(v.strip()) > 2:
                    found_primary_entity = v.strip()
                    break
    
    if found_primary_entity:
        CONTEXT_STORE[request.client_id] = {"last_entity": found_primary_entity}
        print(f"DEBUG: Updated context for {request.client_id} -> {found_primary_entity}")

    # --------------------------
    # 6. Intent & Response Generation
    # --------------------------
    
    # CHECK INTENT: Specific Field Extraction
    # Use token set for strict matching (avoid "phone" matching "headphones")
    import re
    tokens = set(re.findall(r'\w+', prompt_lower))
    
    target_field = None
    if "email" in tokens: target_field = "email"
    elif "phone" in tokens or "number" in tokens: target_field = "phone"
    elif "ssn" in tokens: target_field = "ssn"
    elif "id" in tokens: target_field = "id"
    elif "price" in tokens or "cost" in tokens: target_field = "price"

    if target_field and count > 0:
        answer_text = ""
        if count == 1:
             doc = filtered_docs[0]
             parts = doc.split(" | ")
             found_val = "N/A"
             for point in parts[1:]:
                 if ":" in point:
                     k, v = point.split(":", 1)
                     if target_field in k.lower(): found_val = v.strip()
             answer_text = f"The {target_field} is **{found_val}**."
        else:
             answer_text = f"Found {count} entries with {target_field}:\n\n"
             for doc in filtered_docs:
                parts = doc.split(" | ")
                found_val = "N/A"
                name_val = "Unknown"
                for point in parts[1:]:
                    if ":" in point:
                        k, v = point.split(":", 1)
                        if target_field in k.lower(): found_val = v.strip()
                        if "name" in k.lower(): name_val = v.strip()
                answer_text += f"- **{found_val}** ({name_val})\n"
        
        return {
            "answer": answer_text,
            "sources": [metadata[0]] if metadata else [],
            "classifications": tags
        }
    
    # Intent: Boolean / Fact Check
    is_boolean_query = any(prompt_lower.startswith(prefix) for prefix in ["is ", "are ", "does ", "do ", "can "])

    # Intent: Counting
    if any(k in prompt_lower for k in ["how many", "count", "number of", "total"]):
         if missing_keywords:
             answer = f"I couldn't find specific data for '{', '.join(missing_keywords)}'. However, among the available records, I counted {count} entries:\n\n"
         else:
             answer = f"Based on the knowledge base, I found {count} unique records matching your criteria.\n\n"

    # Intent: Specific Field Lookup
    elif target_field and count > 0:
        answer = f"Found {count} match(es). Here is the requested info:\n\n"
        # ... (Loop remains same, just ensuring variables are in scope usually)
        # Note: We need to include the loop here effectively or let it fall through. 
        # Refactoring slightly to reuse formatting logic.
        pass # Allow fallthrough to formatter below for simplicity if complex

    # Intent: Default Narrative
    else:
        if count == 0:
             answer = "I found some data, but after filtering for your specific keywords, no exact matches remained. Here is the closest context found:\n\n"
             filtered_docs = context_docs[:3]
        else:
             if missing_keywords:
                 answer = f"I couldn't find exact matches for '{', '.join(missing_keywords)}' (this data might not be categorized). However, here is the most relevant information found:\n\n"
             elif is_boolean_query:
                 answer = "Here is the information available in the system regarding your query:\n\n"
             else:
                 answer = f"I found the following {count} unique record(s) related to your request:\n\n"

    # Handle Field Lookup Special Case via Flag if needed, or just Format:
    # To keep this clean in replacement:
    if target_field and count > 0 and "Found " not in locals().get("answer", ""):
         answer = f"Found {count} match(es). Here is the requested info:\n\n"
         # We will use a special formatter for this? No, let's just stick to the specific format logic
         for i, doc in enumerate(filtered_docs):
            parts = doc.split(" | ")
            data_points = parts[1:]
            found_val = "Not found"
            context_name = "Unknown"
            for point in data_points:
                if ":" in point:
                    k, v = point.split(":", 1)
                    if "name" in k.lower(): context_name = v.strip()
                    if target_field in k.lower(): found_val = v.strip()
            answer += f"- **{found_val}** ({context_name})\n"
         
         return {
            "answer": answer,
            "sources": [metadata[0]] if metadata else [],
            "classifications": tags
        }
    
    # Add Classifications Context
    if tags:
        answer += f"*(One or more source datasets contain {', '.join([t.split('.')[-1] for t in tags])} data)*\n\n"

        
    # CHECK INTENT: Simple List (Names)
    just_list_names = any(k in prompt_lower for k in ["names", "name of", "list of users", "who are they"])

    # Format snippets
    for i, doc in enumerate(filtered_docs):
        parts = doc.split(" | ")
        source = parts[0].replace("Dataset: ", "").strip()
        data_points = parts[1:]
        
        if just_list_names:
            name_val = "Unknown"
            for point in data_points:
                if ":" in point:
                    k, v = point.split(":", 1)
                    if "name" in k.lower():
                        name_val = v.strip()
                        break
            answer += f"- {name_val}\n"
            continue

        answer += f"Result {i+1} (from {source}):\n"
        sentences = []
        for point in data_points:
            if ":" in point:
                k, v = point.split(":", 1)
                clean_k = k.strip().replace('_', ' ')
                sentences.append(f"the {clean_k} is {v.strip()}")
            else:
                sentences.append(point.strip())
        
        if sentences:
            text = ", ".join(sentences)
            text = text[0].upper() + text[1:] if text else text
            answer += f"{text}.\n\n"

    return {
        "answer": answer,
        "sources": [metadata[0]] if metadata else [],
        "classifications": tags
    }

    return {
        "answer": answer,
        "sources": [metadata[0]] if metadata else [],
        "classifications": tags
    }
