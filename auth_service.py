# auth_service.py
import requests
from config import THINGSBOARD_URL

def check_token_status(token: str) -> bool:
    """
    Validates the ThingsBoard JWT token using the internal pilti endpoint.
    Returns True if valid, False otherwise.
    """
    url = f"{THINGSBOARD_URL}/api/pilti/checkTokenStatus"
    headers = {
        "X-Authorization": f"Bearer {token}",
        "Authorization": f"Bearer {token}"  # Adding both for compatibility
    }
    try:
        print(f"[Auth] Validating token against: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"[Auth] Validation failed. Status: {response.status_code}")
            print(f"[Auth] Response body: {response.text[:200]}")
            return False
            
        print(f"[Auth] Token valid for {url}")
        return True
    except Exception as e:
        print(f"[Auth Error] {e}")
        return False
