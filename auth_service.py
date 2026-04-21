# auth_service.py
import requests

def check_token_status(token: str) -> bool:
    """
    Validates the ThingsBoard JWT token using the internal pilti endpoint.
    Returns True if valid, False otherwise.
    """
    from config import THINGSBOARD_URL # Local import to avoid circular dependency
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

def fetch_pilti_urls():
    """
    Fetches the dynamic URL configuration from the PiltiServices endpoint.
    """
    from config import PILTI_CONFIG_URL # Local import to avoid circular dependency
    fetch_url = PILTI_CONFIG_URL
    
    try:
        print(f"[Config] Fetching dynamic URLs from {fetch_url}...")
        resp = requests.get(fetch_url, timeout=15)
        
        if resp.status_code != 200:
            print(f"[Config Warning] Failed to fetch URLs ({resp.status_code}). Using hardcoded defaults.")
            return None
            
        try:
            return resp.json()
        except Exception as json_err:
            print(f"[Config Error] Failed to parse JSON from {fetch_url}: {json_err}")
            return None
        
    except Exception as e:
        print(f"[Config Error] Dynamic fetch failed: {e}. Using hardcoded defaults.")
        return None

def extract_ollama_details(config_json):
    """
    Safely extracts Ollama IP and Port from the PiltiUrls structure.
    """
    if not config_json or "PiltiUrls" not in config_json:
        return None, None
        
    try:
        ollama_config = config_json["PiltiUrls"]["PiltiAIServer"]["PiltiOllamaServer"]
        ip = ollama_config.get("OllamaServerIP")
        port = ollama_config.get("port")
        return ip, port
    except KeyError as e:
        print(f"[Config Error] Root key missing in JSON: {e}")
        return None, None

def get_ollama_models(base_url):
    """
    Fetches available models from the Ollama server.
    Returns a list of model names.
    """
    if not base_url:
        return []
    
    try:
        url = f"{base_url}/api/tags"
        print(f"[Ollama] Fetching available models from {url}...")
        resp = requests.get(url, timeout=10)
        
        if resp.status_code != 200:
            print(f"[Ollama Warning] Failed to fetch models ({resp.status_code})")
            return []
            
        data = resp.json()
        models = [m["name"] for m in data.get("models", [])]
        return models
    except Exception as e:
        print(f"[Ollama Error] Failed to fetch models: {e}")
        return []
