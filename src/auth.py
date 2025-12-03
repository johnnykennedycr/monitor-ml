import os
import requests

def get_access_token():
    app_id = os.getenv("ML_APP_ID")
    client_secret = os.getenv("ML_CLIENT_SECRET")
    refresh_token = os.getenv("ML_REFRESH_TOKEN")

    if not all([app_id, client_secret, refresh_token]):
        print("[AUTH] Erro: Faltam credenciais (App ID, Secret ou Refresh Token).")
        return None

    url = "https://api.mercadolibre.com/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": app_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token
    }

    try:
        response = requests.post(url, data=payload)
        data = response.json()
        
        if response.status_code == 200:
            return data["access_token"]
        else:
            print(f"[AUTH] Falha ao renovar token: {data}")
            return None
    except Exception as e:
        print(f"[AUTH] Erro de conexão: {e}")
        return None