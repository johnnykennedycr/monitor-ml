import requests
import time
import random

# Categoria de Celulares e Telefones (MLB1051)
CATEGORY_ID = "MLB1051"
API_URL = "https://api.mercadolibre.com/sites/MLB/search"

def get_best_sellers():
    """
    Busca produtos usando headers avançados para simular um navegador real
    e evitar o erro 403 (Forbidden).
    """
    
    # 1. Configura uma Sessão (ajuda a manter cookies e parece mais humano)
    session = requests.Session()

    # 2. Headers Completos (Copiados de um navegador Chrome real)
    # Isso é CRUCIAL para não tomar bloqueio 403
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.mercadolivre.com.br/",
        "Origin": "https://www.mercadolivre.com.br",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
    }

    # Parâmetros de busca
    params = {
        "category": CATEGORY_ID,
        "sort": "relevance", 
        "limit": 20,
        # Adicionamos um offset aleatório pequeno as vezes para não parecer cache
        "offset": 0 
    }

    print(f"[DEBUG] Consultando API: {API_URL} | Categoria: {CATEGORY_ID}")

    try:
        # Faz a requisição usando a sessão
        response = session.get(API_URL, params=params, headers=headers, timeout=15)
        
        # DEBUG DA RESPOSTA SE DER ERRO
        if response.status_code != 200:
            print(f"[DEBUG] Erro na resposta da API: {response.status_code}")
            # Se for 403, as vezes o corpo da mensagem diz o motivo
            if response.status_code == 403:
                print("[DEBUG] Acesso negado. O Mercado Livre bloqueou este IP/Script.")
            return []
            
        data = response.json()
        
    except Exception as e:
        print(f"[DEBUG] Erro de conexão: {e}")
        return []

    results = []
    items = data.get("results", [])

    for item in items:
        # Extração segura dos dados
        title = item.get("title")
        link = item.get("permalink")
        price = item.get("price")
        currency = item.get("currency_id", "BRL")
        original_price = item.get("original_price")

        if title and link:
            price_fmt = f"{currency} {price}" if price else "R$ --"
            
            # Lógica simples para detectar se é promoção (se tem preço original riscado)
            is_promo = False
            if original_price and original_price > price:
                is_promo = True
                discount = int(((original_price - price) / original_price) * 100)
                price_fmt = f"{price_fmt} (Desconto de {discount}%)"

            results.append({
                "name": title,
                "link": link,
                "price": price_fmt,
                "id": item.get("id")
            })

    print(f"[DEBUG] Produtos coletados da API: {len(results)}")
    return results

if __name__ == "__main__":
    # Teste isolado
    items = get_best_sellers()
    for item in items:
        print(f"- {item['name']} | {item['price']}")