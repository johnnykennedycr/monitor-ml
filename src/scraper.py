import requests

# Categoria de Eletrônicos, Áudio e Vídeo (MLB1000 é a raiz de eletrônicos, MLB1051 é Celulares)
# Você pode mudar para uma busca por termo se preferir.
CATEGORY_ID = "MLB1051" 
API_URL = "https://api.mercadolibre.com/sites/MLB/search"

def get_best_sellers():
    # Parâmetros para buscar os mais relevantes/vendidos na categoria
    params = {
        "category": CATEGORY_ID,
        "sort": "relevance",  # Traz os mais relevantes (geralmente os mais vendidos)
        "limit": 20           # Limita a 20 resultados
    }

    # Headers são obrigatórios para evitar bloqueio (erro 403 ou lista vazia)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    print(f"[DEBUG] Consultando API: {API_URL} | Categoria: {CATEGORY_ID}")

    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"[DEBUG] Erro na resposta da API: {response.status_code}")
            return []
            
        data = response.json()
    except Exception as e:
        print("[DEBUG] Erro de conexão ou parse:", e)
        return []

    results = []

    # A API de Search retorna uma lista chamada "results"
    items = data.get("results", [])

    for item in items:
        title = item.get("title")
        link = item.get("permalink")
        price = item.get("price")
        currency = item.get("currency_id", "BRL")

        if title and link:
            # Formatação simples de preço para exibir bonito
            price_fmt = f"{currency} {price}" if price else "Preço não informado"
            
            results.append({
                "name": title,
                "link": link,
                "price": price_fmt,
                "id": item.get("id")
            })

    print(f"[DEBUG] Produtos coletados da API: {len(results)}")
    return results

if __name__ == "__main__":
    # Teste rápido se rodar o arquivo direto
    print(get_best_sellers())