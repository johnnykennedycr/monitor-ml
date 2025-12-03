import os
import requests
import json
from datetime import datetime, timedelta

# Recupera chaves do ambiente
API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_CX")

def get_best_sellers():
    if not API_KEY or not SEARCH_ENGINE_ID:
        print("[DEBUG] Erro: Chaves do Google não configuradas.")
        return []

    print("[DEBUG] Consultando Google Custom Search API...")

    # Termos mágicos para achar promoções
    # Buscamos por "R$" dentro do site do ML
    query = "site:mercadolivre.com.br/ofertas R$"
    
    # URL da API do Google
    url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        'key': API_KEY,
        'cx': SEARCH_ENGINE_ID,
        'q': query,
        'num': 10,               # Traz 10 resultados
        'dateRestrict': 'd1',    # Indexado no último dia (para ser recente)
        'gl': 'br',              # Região Brasil
        'sort': 'date'           # Ordenar por data de indexação
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if "error" in data:
            print(f"[DEBUG] Erro Google: {data['error']['message']}")
            return []

        if "items" not in data:
            print("[DEBUG] Google não retornou itens novos agora.")
            return []

        products = []
        
        for item in data['items']:
            title = item.get('title')
            link = item.get('link')
            snippet = item.get('snippet', '') # Descrição do Google

            # O título no Google geralmente vem "Nome do Produto | Mercado Livre"
            # Vamos limpar
            clean_name = title.split("|")[0].strip()
            if "Mercado Livre" in clean_name:
                clean_name = clean_name.replace("Mercado Livre", "").strip()

            # Tenta extrair preço do Snippet (O Google mostra: "R$ 1.200,00 ...")
            price = "Ver Oferta"
            if "R$" in snippet:
                try:
                    # Pega o texto logo após o R$
                    parts = snippet.split("R$")
                    price_val = parts[1].strip().split(" ")[0]
                    # Limpeza básica
                    price_val = price_val.replace(".", "").replace(",", ".")
                    # Verifica se é numero
                    float(price_val) 
                    price = f"R$ {parts[1].strip().split(' ')[0]}" # Reconstrói formatação BR
                except:
                    pass
            
            # Filtro de segurança: Garante que é link de produto
            if "/p/" in link or "/MLB-" in link:
                products.append({
                    "name": clean_name,
                    "link": link,
                    "price": price,
                    "id": link
                })

        print(f"[DEBUG] Sucesso! {len(products)} ofertas encontradas via Google.")
        return products

    except Exception as e:
        print(f"[DEBUG] Erro conexão Google: {e}")
        return []

if __name__ == "__main__":
    # Para testar local, exporte as variaveis no terminal ou defina aqui temporariamente
    # os.environ["GOOGLE_API_KEY"] = "SUA_KEY"
    # os.environ["GOOGLE_SEARCH_CX"] = "SEU_CX"
    items = get_best_sellers()
    for i in items:
        print(f"{i['name']} - {i['price']}")