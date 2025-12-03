import cloudscraper
from bs4 import BeautifulSoup
import time

# URL do fórum de promoções da Hardmob
HARDMOB_URL = "https://www.hardmob.com.br/forums/407-Promocoes"

def get_real_link(url, scraper):
    """
    Hardmob usa redirecionador. Essa função segue ele para achar o link final.
    """
    try:
        # Pede apenas o cabeçalho para ver para onde o link aponta
        resp = scraper.head(url, allow_redirects=True, timeout=10)
        return resp.url
    except:
        return url

def get_best_sellers():
    print(f"[DEBUG] Iniciando Mineração na Hardmob...")
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )

    try:
        # 1. Acessa a lista de tópicos
        response = scraper.get(HARDMOB_URL)
        if response.status_code != 200:
            print(f"[DEBUG] Erro Hardmob: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        threads = soup.find_all("li", class_="threadbit")
        print(f"[DEBUG] Tópicos lidos: {len(threads)}")

        products = []
        
        for thread in threads[:20]: # Analisa os 20 mais recentes
            try:
                # Extrai o título
                title_tag = thread.find("a", class_="title")
                if not title_tag: continue
                
                title = title_tag.get_text().strip()
                link_thread = "https://www.hardmob.com.br/" + title_tag['href']

                # 2. FILTRO: Verifica se é Mercado Livre
                if "mercado livre" in title.lower() or "mercadolivre" in title.lower() or "[ml]" in title.lower():
                    print(f"[DEBUG] Analisando: {title}")
                    
                    time.sleep(1) # Delay educado
                    resp_thread = scraper.get(link_thread)
                    soup_thread = BeautifulSoup(resp_thread.text, "html.parser")
                    
                    # Procura o primeiro post
                    first_post = soup_thread.find("div", class_="content")
                    if first_post:
                        links = first_post.find_all("a", href=True)
                        
                        target_link = None
                        for l in links:
                            href = l['href']
                            if "mercadolivre.com.br" in href or "mercado.li" in href:
                                target_link = href
                                break
                        
                        if target_link:
                            # Limpa o link
                            clean_link = get_real_link(target_link, scraper)
                            if "?" in clean_link:
                                clean_link = clean_link.split("?")[0]

                            # Extração de Preço (BLINDADA CONTRA ERRO)
                            price = "Ver Oferta"
                            try:
                                if "R$" in title:
                                    parts = title.split("R$")
                                    if len(parts) > 1:
                                        # Pega o pedaço depois do R$, limpa espaços e pega o primeiro token
                                        price_str = parts[1].strip().split(" ")[0]
                                        # Remove pontuação final se vier colada (ex: 50,00!)
                                        price_str = price_str.rstrip(".,!)]")
                                        if any(char.isdigit() for char in price_str):
                                            price = f"R$ {price_str}"
                            except Exception as e:
                                print(f"[DEBUG] Aviso: Não consegui ler o preço de '{title}'. Usando padrão.")

                            products.append({
                                "name": title,
                                "link": clean_link,
                                "price": price,
                                "id": clean_link
                            })

            except Exception as e:
                # Se um tópico falhar, apenas loga e vai para o próximo
                print(f"[DEBUG] Pulei tópico problemático: {e}")
                continue

        print(f"[DEBUG] Total de produtos extraídos: {len(products)}")
        return products

    except Exception as e:
        print(f"[DEBUG] Erro Crítico: {e}")
        return []

if __name__ == "__main__":
    items = get_best_sellers()
    for i in items:
        print(f" > {i['name']} | {i['link']}")