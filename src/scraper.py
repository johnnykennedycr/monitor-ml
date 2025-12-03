import requests
from auth import get_access_token
import random

# Endpoint oficial de busca
API_URL = "https://api.mercadolibre.com/sites/MLB/search"

def get_best_sellers():
    # 1. Pega token válido
    token = get_access_token()
    if not token:
        print("[DEBUG] Token ausente. Abortando busca.")
        return []

    # 2. Configura headers para PARECER UM NAVEGADOR (Isso evita o 403)
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json"
    }

    # 3. Parâmetros da busca
    params = {
        "q": "iphone", # Teste com algo popular primeiro
        "sort": "relevance",
        "limit": 10,
    }

    print(f"[DEBUG] Buscando produtos via API Oficial...")

    try:
        response = requests.get(API_URL, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            clean_products = []
            for item in results:
                price = item.get("price")
                currency = item.get("currency_id", "BRL")
                permalink = item.get("permalink")
                
                # Garante que temos link e nome
                if permalink and item.get("title"):
                    clean_products.append({
                        "name": item.get("title"),
                        "link": permalink,
                        "price": f"{currency} {price}",
                        "id": item.get("id")
                    })
            
            print(f"[DEBUG] Sucesso! {len(clean_products)} produtos encontrados.")
            return clean_products
        else:
            print(f"[DEBUG] Erro API: {response.status_code} - {response.text}")
            return []

    except Exception as e:
        print(f"[DEBUG] Erro de conexão: {e}")
        return []

if __name__ == "__main__":
    get_best_sellers()