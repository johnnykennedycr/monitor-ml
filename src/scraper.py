import os
import requests
import re
import json

API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_CX")

def format_price(value):
    """ Converte 1200.50 para R$ 1.200,50 """
    try:
        val = float(value)
        # Formatação brasileira
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return None

def get_best_sellers():
    if not API_KEY or not SEARCH_ENGINE_ID:
        print("[DEBUG] Erro: Chaves do Google ausentes.")
        return []

    print("[DEBUG] Consultando Google API (Modo Rich Snippets)...")
    
    # Adicionei "price" na query para forçar resultados que tenham preço
    query = 'site:mercadolivre.com.br/p/ OR site:mercadolivre.com.br/MLB- "OFF" OR "Desconto"'
    
    url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        'key': API_KEY,
        'cx': SEARCH_ENGINE_ID,
        'q': query,
        'num': 10,
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
            pagemap = item.get('pagemap', {}) # AQUI ESTÁ O OURO
            
            # 1. TENTATIVA DE PREÇO VIA DADOS ESTRUTURADOS (Offer)
            # O ML envia isso para o Google. É o preço mais confiável.
            price = None
            
            # Tenta via schema.org/Offer
            if 'offer' in pagemap and len(pagemap['offer']) > 0:
                price_raw = pagemap['offer'][0].get('price')
                if price_raw:
                    price = format_price(price_raw)
            
            # Tenta via metatags (twitter:data1 ou product:price:amount)
            if not price and 'metatags' in pagemap and len(pagemap['metatags']) > 0:
                meta = pagemap['metatags'][0]
                price_raw = meta.get('product:price:amount') or meta.get('twitter:data1') or meta.get('og:price:amount')
                if price_raw:
                    price = format_price(price_raw)

            # Última tentativa: Regex no snippet (Plano C)
            if not price:
                match = re.search(r'R\$\s?([\d\.]+,\d{2})', snippet)
                if match:
                    price = f"R$ {match.group(1)}"
            
            # Se ainda assim não achou, define um padrão
            if not price:
                price = "🔥 Ver Oferta no Site"

            # 2. TENTATIVA DE IMAGEM (Melhorada)
            image_url = None
            if 'cse_image' in pagemap:
                image_url = pagemap['cse_image'][0]['src']
            elif 'cse_thumbnail' in pagemap:
                image_url = pagemap['cse_thumbnail'][0]['src']
            elif 'metatags' in pagemap and 'og:image' in pagemap['metatags'][0]:
                image_url = pagemap['metatags'][0]['og:image']

            # 3. LIMPEZA DE TÍTULO
            clean_name = title.split("|")[0].strip()
            # Remove sufixos comuns do ML
            clean_name = re.sub(r'\s*-\s*R\$.*', '', clean_name) # Remove preço do titulo se tiver
            clean_name = clean_name.replace("Mercado Livre", "").strip()

            if "/p/" in link or "/MLB-" in link:
                products.append({
                    "name": clean_name,
                    "link": link,
                    "price": price,
                    "id": link,
                    "image_url": image_url
                })

        print(f"[DEBUG] {len(products)} produtos processados.")
        return products

    except Exception as e:
        print(f"[DEBUG] Erro scraper: {e}")
        return []