import jwt
import time
from cryptography.hazmat.primitives import serialization

import os
# Path to private key
# resolved relative to this script location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(BASE_DIR, "../../openmetadata-docker/conf/private_key.der")

# Payload from previous request (Step 139)
payload = {
    "iss": "open-metadata.org",
    "sub": "ingestion-bot",
    "roles": ["IngestionBotRole"],
    "email": "ingestion-bot@open-metadata.org",
    "isBot": True,
    "tokenType": "BOT",
    "username": "ingestion-bot",
    "preferred_username": "ingestion-bot",
    # Set IAT to now, EXP to null (or far future)
    "iat": int(time.time()),
    "exp": None 
}

# The Kid (Key ID) we saw in the JWKS endpoint
# "kid":"Gb389a-9f76-gdjs-a92j-0242bk94356"
# WAIT. If I changed the keys, the 'kid' might have changed if the server calculates it from the key header?
# BUT I don't see the server doing that. The 'kid' seems hardcoded in OM config??
# In docker-compose.yml: JWT_KEY_ID: ${JWT_KEY_ID:-"Gb389a-9f76-gdjs-a92j-0242bk94356"}
# YES! It's hardcoded. So I must use THAT kid.
headers = {
    "kid": "Gb389a-9f76-gdjs-a92j-0242bk94356"
}

with open(KEY_PATH, "rb") as f:
    private_key = serialization.load_der_private_key(f.read(), password=None)

token = jwt.encode(payload, private_key, algorithm="RS256", headers=headers)
print(token)
