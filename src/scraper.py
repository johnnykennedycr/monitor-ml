import cloudscraper
from bs4 import BeautifulSoup
import re
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
    
    # Navegador falso para não ser bloqueado
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
        
        # Pega a lista de tópicos (threads)
        threads = soup.find_all("li", class_="threadbit")
        print(f"[DEBUG] Tópicos lidos: {len(threads)}")

        products = []
        
        for thread in threads[:20]: # Analisa os 20 mais recentes
            try:
                # Extrai o título do tópico
                title_tag = thread.find("a", class_="title")
                if not title_tag: continue
                
                title = title_tag.get_text().strip()
                link_thread = "https://www.hardmob.com.br/" + title_tag['href']

                # 2. FILTRO: Verifica se é Mercado Livre
                # A Hardmob costuma usar padrão [Loja] no título
                if "mercado livre" in title.lower() or "mercadolivre" in title.lower() or "[ml]" in title.lower():
                    print(f"[DEBUG] Candidato encontrado: {title}")
                    
                    # 3. Entra no tópico para caçar o link do produto
                    time.sleep(1) # Respeito ao servidor
                    resp_thread = scraper.get(link_thread)
                    soup_thread = BeautifulSoup(resp_thread.text, "html.parser")
                    
                    # O link do produto geralmente é o primeiro link externo no primeiro post
                    # Procura na div do post
                    first_post = soup_thread.find("div", class_="content")
                    if first_post:
                        links = first_post.find_all("a", href=True)
                        
                        target_link = None
                        for l in links:
                            href = l['href']
                            # Procura link que pareça ser o da oferta
                            if "mercadolivre.com.br" in href or "mercado.li" in href:
                                target_link = href
                                break
                        
                        if target_link:
                            # Limpa o link (remove sujeira de tracking de outros)
                            clean_link = get_real_link(target_link, scraper)
                            if "?" in clean_link:
                                clean_link = clean_link.split("?")[0]

                            # Extrai preço do título (Ex: [ML] iPhone - R$ 2000)
                            price = "Ver Oferta"
                            if "R$" in title:
                                parts = title.split("R$")
                                if len(parts) > 1:
                                    price = "R$ " + parts[1].split(" ")[1]

                            products.append({
                                "name": title,
                                "link": clean_link, # AGORA SIM: Link do ML
                                "price": price,
                                "id": clean_link
                            })
                            print(f"[DEBUG] -> Link extraído com sucesso!")

            except Exception as e:
                print(f"[DEBUG] Erro ao ler tópico: {e}")
                continue

        print(f"[DEBUG] Total de produtos ML prontos para afiliar: {len(products)}")
        return products

    except Exception as e:
        print(f"[DEBUG] Erro Crítico: {e}")
        return []

if __name__ == "__main__":
    items = get_best_sellers()
    for i in items:
        print(f" > {i['name']} | {i['link']}")