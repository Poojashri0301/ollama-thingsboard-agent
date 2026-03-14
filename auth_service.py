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
        "X-Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # Assuming the endpoint returns 200 for valid tokens.
        # If it returns a JSON with status, we can check that too.
        # Based on user description, it is used for validation.
        return response.status_code == 200
    except Exception as e:
        print(f"[Auth Error] {e}")
        return False
