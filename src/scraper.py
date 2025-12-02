import requests

# Categoria de eletrônicos como exemplo
# (Podemos adicionar várias depois)
CATEGORY_ID = "MLB1051"  # TVs, vídeo e áudio

API_URL = f"https://api.mercadolibre.com/highlights/MLB/category/{CATEGORY_ID}"

def get_best_sellers():
    try:
        response = requests.get(API_URL, timeout=10)
        data = response.json()
    except Exception as e:
        print("[DEBUG] Erro na API:", e)
        return []

    results = []

    # A API retorna assim:
    # {
    #   "content": {
    #       "top_selling": [ { "id": "...", "title": "...", "permalink": "..."}, ... ]
    #   }
    # }

    top = data.get("content", {}).get("top_selling", [])

    for item in top[:20]:
        title = item.get("title")
        link = item.get("permalink")

        if title and link:
            results.append({
                "name": title,
                "link": link
            })

    print(f"[DEBUG] Produtos coletados da API: {len(results)}")
    return results
