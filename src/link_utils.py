import requests
import re
import cloudscraper
from bs4 import BeautifulSoup

def format_price(value):
    try:
        val = float(value)
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return value

def get_ml_data(url):
    """ Extrai Título e Preço da página do ML """
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'mobile': False})
    data = {"title": "Oferta Imperdível", "price": None, "image": None}
    
    try:
        resp = scraper.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Título
        title = soup.find("h1", class_="ui-pdp-title")
        if title: 
            data["title"] = title.text.strip()
        
        # Preço
        price_meta = soup.find("meta", property="product:price:amount")
        if price_meta:
            data["price"] = format_price(price_meta["content"])
        
        return data
    except Exception as e:
        print(f"Erro scraping: {e}")
        return data

def generate_affiliate_link(url, tag):
    """ Limpa o link e afilia """
    # 1. Resolve redirecionamento (/sec/)
    final_url = url
    if "/sec/" in url or "mercado.li" in url or "bit.ly" in url:
        try:
            resp = requests.get(url, allow_redirects=True, timeout=10)
            final_url = resp.url
        except:
            pass

    # 2. Extrai ID do Produto (MLB)
    match = re.search(r'(MLB-?\d+)', final_url)
    clean_link = final_url.split("?")[0] # Fallback
    
    if match:
        clean_id = match.group(1).replace("-", "")
        clean_link = f"https://www.mercadolivre.com.br/p/{clean_id}"
    
    # 3. Gera link API Oficial
    api_url = "https://www.mercadolivre.com.br/afiliados/api/linkbuilder/meli"
    payload = {"tag": tag, "urls": [clean_link]}
    try:
        r = requests.post(api_url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            js = r.json()
            if "links" in js and js["links"]:
                return js["links"][0]["url"]
    except:
        pass
    
    return f"{clean_link}?matt_word={tag}"