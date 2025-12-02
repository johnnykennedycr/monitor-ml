import requests

API_URL = "https://api.mercadolibre.com/sites/MLB/trends/MLB1051"

def get_best_sellers():
    try:
        response = requests.get(API_URL, timeout=10)
        data = response.json()
    except Exception as e:
        print("[DEBUG] Erro na API:", e)
        return []

    products = []
    for item in data[:20]:  # limita para evitar spam
        title = item.get("keyword")
        link = item.get("url")

        if title and link:
            products.append({"name": title, "link": link})

    return products
