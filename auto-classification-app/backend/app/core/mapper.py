# Pure logic mapping rules

# Hardcoded generic rules for fallback or init
DEFAULT_RULES = [
    {"source": "PII.Sensitive", "target": "DataClassification.Confidential"},
    {"source": "PII.Sensitive.SSN", "target": "DataClassification.Confidential"},
    {"source": "PII.Sensitive.CreditCard", "target": "DataClassification.Confidential"},
    {"source": "PII.Contact", "target": "DataClassification.Personal"},
]

def get_mapped_tags(source_fqns: list):
    """
    Pure logic: Input a list of existing tags, return new tags to apply based on rules.
    """
    new_tags = []
    
    for s_fqn in source_fqns:
        for rule in DEFAULT_RULES:
            if s_fqn == rule["source"] or rule["source"] in s_fqn:
                new_tags.append(rule["target"])
    
    return list(set(new_tags)) # Unique only
