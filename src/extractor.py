import cloudscraper
from bs4 import BeautifulSoup
import re
import json

def format_price(value):
    """ Converte float 1200.5 para string 'R$ 1.200,50' """
    if not value:
        return None
    try:
        val = float(value)
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return value

def extract_details(url):
    """
    Entra no link e tenta pegar Título, Preço e Foto usando JSON-LD (Dados Estruturados)
    """
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    
    try:
        # Baixa o HTML
        resp = scraper.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        title = None
        price = None
        image_url = None

        # --- ESTRATÉGIA 1: JSON-LD (A mais confiável) ---
        # O ML entrega um JSON limpo para o Google, vamos pegar ele.
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                
                # Às vezes o JSON é uma lista, às vezes um objeto
                if isinstance(data, list):
                    data = data[0]
                
                if data.get('@type') == 'Product':
                    title = data.get('name')
                    image_url = data.get('image')
                    
                    # Preço no JSON-LD
                    offers = data.get('offers')
                    if isinstance(offers, dict):
                        price_val = offers.get('price') or offers.get('lowPrice')
                        if price_val:
                            price = format_price(price_val)
                    elif isinstance(offers, list) and len(offers) > 0:
                        price_val = offers[0].get('price')
                        if price_val:
                            price = format_price(price_val)
                    break # Achamos, pode parar
            except:
                continue

        # --- ESTRATÉGIA 2: META TAGS (Fallback) ---
        if not title:
            meta_title = soup.find("meta", property="og:title")
            if meta_title: title = meta_title["content"]
            else: title = soup.title.string if soup.title else "Oferta Mercado Livre"

        if not image_url:
            meta_image = soup.find("meta", property="og:image")
            if meta_image: image_url = meta_image["content"]

        if not price:
            # Tenta tags específicas de preço
            meta_price = soup.find("meta", property="product:price:amount")
            if meta_price:
                price = format_price(meta_price["content"])

        # --- ESTRATÉGIA 3: REGEX BRUTO (Desespero) ---
        # Se ainda não temos preço, procuramos por "R$" no texto visível
        if not price:
            # Procura na descrição ou título
            text_blob = str(soup.find("meta", dict(name="description"))) + str(title)
            # Regex que busca R$ 1.000,00 ou R$1000
            match = re.search(r'R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)', text_blob)
            if match:
                price = f"R$ {match.group(1)}"
        
        # --- LIMPEZA FINAL ---
        if title:
            title = title.replace(" | Mercado Livre", "").strip()
        
        if not price:
            price = "Ver Oferta" # Texto padrão se falhar tudo

        return {
            "title": title,
            "price": price,
            "image_url": image_url
        }

    except Exception as e:
        print(f"[EXTRACTOR] Erro ao ler link: {e}")
        return None