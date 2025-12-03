import requests
from auth import get_access_token

# Endpoint oficial de busca
API_URL = "https://api.mercadolibre.com/sites/MLB/search"

def get_best_sellers():
    # 1. Pega token válido
    token = get_access_token()
    if not token:
        return []

    # 2. Configura headers com o Token
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "MonitorBot/1.0"
    }

    # 3. Parâmetros da busca (Edite o 'q' para o que quiser monitorar)
    params = {
        "q": "ofertas",  
        "sort": "relevance",
        "limit": 20
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
                
                clean_products.append({
                    "name": item.get("title"),
                    "link": item.get("permalink"),
                    "price": f"{currency} {price}",
                    "id": item.get("id")
                })
            
            print(f"[DEBUG] Sucesso! {len(clean_products)} produtos encontrados.")
            return clean_products
        else:
            print(f"[DEBUG] Erro API: {response.status_code} - {response.text}")
            return []

    except Exception as e:
        print(f"[DEBUG] Erro: {e}")
        return []