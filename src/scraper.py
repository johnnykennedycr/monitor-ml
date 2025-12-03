import os
import requests
import json
import re

API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_CX")

def get_best_sellers():
    if not API_KEY or not SEARCH_ENGINE_ID:
        print("[DEBUG] Erro: Chaves do Google ausentes.")
        return []

    print("[DEBUG] Consultando Google API (Busca de Produtos)...")
    
    # Busca ampla por produtos com indícios de oferta
    query = 'site:mercadolivre.com.br/p/ OR site:mercadolivre.com.br/MLB- "OFF" OR "Desconto"'
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': API_KEY,
        'cx': SEARCH_ENGINE_ID,
        'q': query,
        'num': 10, # Traz 10 para filtrar depois
        'gl': 'br',
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if "items" not in data:
            print("[DEBUG] Google não retornou itens.")
            return []

        products = []
        
        for item in data['items']:
            title = item.get('title', '')
            link = item.get('link', '')
            snippet = item.get('snippet', '')
            
            # --- NOVO: TENTATIVA DE EXTRAIR IMAGEM ---
            image_url = None
            try:
                # O Google costuma colocar a imagem principal aqui
                image_url = item.get('pagemap', {}).get('cse_image', [])[0].get('src')
            except:
                pass # Se não tiver imagem, tudo bem

            # Limpeza do título
            clean_name = title.split("|")[0].split("-")[0].strip()
            
            # Extração de preço do snippet
            price = "Ver Oferta"
            match_price = re.search(r'R\$\s?[\d\.]+,\d{2}', snippet)
            if match_price:
                price = match_price.group(0)
            
            if "/p/" in link or "/MLB-" in link:
                products.append({
                    "name": clean_name,
                    "link": link,
                    "price": price,
                    "id": link,
                    # Adicionamos a URL da imagem ao resultado
                    "image_url": image_url 
                })

        print(f"[DEBUG] {len(products)} produtos processados (com ou sem imagem).")
        return products

    except Exception as e:
        print(f"[DEBUG] Erro conexão Google: {e}")
        return []