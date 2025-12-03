import cloudscraper
from bs4 import BeautifulSoup
import re

def extract_details(url):
    """
    Entra no link e tenta pegar Título, Preço e Foto (OpenGraph)
    """
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    
    try:
        # Baixa o HTML
        resp = scraper.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 1. Título (Meta Tags são mais confiáveis)
        title = soup.find("meta", property="og:title")
        title = title["content"] if title else soup.title.string
        
        # Limpeza do título
        title = title.replace(" | Mercado Livre", "").strip()
        
        # 2. Imagem
        image = soup.find("meta", property="og:image")
        image_url = image["content"] if image else None
        
        # 3. Preço (Tenta achar nos metadados ou no HTML)
        price = "Ver Oferta"
        
        # Tenta meta price
        meta_price = soup.find("meta", property="product:price:amount")
        if meta_price:
            try:
                val = float(meta_price["content"])
                price = f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except: pass
            
        # Se falhar, tenta regex no título ou descrição
        if price == "Ver Oferta":
            desc = soup.find("meta", dict(name="description"))
            if desc:
                content = desc.get("content", "")
                match = re.search(r'R\$\s?[\d\.,]+', content)
                if match:
                    price = match.group(0)

        return {
            "title": title,
            "price": price,
            "image_url": image_url
        }

    except Exception as e:
        print(f"[EXTRACTOR] Erro ao ler link: {e}")
        return None