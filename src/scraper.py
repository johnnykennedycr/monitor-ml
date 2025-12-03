import os
import requests
import json
import re

# Recupera chaves
API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_CX")

def get_best_sellers():
    if not API_KEY or not SEARCH_ENGINE_ID:
        print("[DEBUG] Erro: Chaves do Google ausentes.")
        return []

    print("[DEBUG] Consultando Google API (Busca de Produtos)...")

    # ESTRATÉGIA NOVA:
    # 1. Buscamos em todo o domínio (não só /ofertas)
    # 2. Focamos em padrões de URL de produto (/p/ e /MLB-)
    # 3. Procuramos palavras-chave de promoção
    query = 'site:mercadolivre.com.br/p/ OR site:mercadolivre.com.br/MLB- "OFF" OR "Desconto"'
    
    url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        'key': API_KEY,
        'cx': SEARCH_ENGINE_ID,
        'q': query,
        'num': 10,
        'gl': 'br',  # Brasil
        # REMOVEMOS 'dateRestrict' e 'sort' para garantir que venham resultados.
        # O filtro de novidade será feito pelo seu database.json
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        # Debug avançado para entender o retorno do Google
        if "error" in data:
            print(f"[DEBUG] Erro Google: {data['error']['message']}")
            return []
            
        total_results = data.get('searchInformation', {}).get('totalResults', '0')
        print(f"[DEBUG] O Google encontrou {total_results} resultados no índice total.")

        if "items" not in data:
            print("[DEBUG] Lista de 'items' vazia no JSON recebido.")
            return []

        products = []
        
        for item in data['items']:
            title = item.get('title', '')
            link = item.get('link', '')
            snippet = item.get('snippet', '')

            # Limpeza do título (Google traz "Nome | Mercado Livre")
            clean_name = title.split("|")[0].split("-")[0].strip()
            
            # Tenta extrair preço do snippet
            # O Google costuma mostrar: "R$ 1.200,00, 12x de R$ 100..."
            price = "Ver Oferta"
            
            # Regex poderoso para achar preço (R$ 1.234,56 ou R$ 1234)
            match_price = re.search(r'R\$\s?[\d\.]+,\d{2}', snippet)
            if match_price:
                price = match_price.group(0)
            
            # Validação: Só aceita se for link de produto mesmo
            if "/p/" in link or "/MLB-" in link:
                products.append({
                    "name": clean_name,
                    "link": link,
                    "price": price,
                    "id": link # ID único para o database
                })

        print(f"[DEBUG] {len(products)} produtos válidos processados.")
        return products

    except Exception as e:
        print(f"[DEBUG] Erro conexão Google: {e}")
        return []

if __name__ == "__main__":
    items = get_best_sellers()
    for i in items:
        print(f"{i['name']} -> {i['price']}")