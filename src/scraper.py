import cloudscraper
from bs4 import BeautifulSoup
import time
import random

# Página dedicada do Mercado Livre no Promobit
PROMOBIT_URL = "https://www.promobit.com.br/loja/mercadolivre/"

def get_best_sellers():
    print(f"[DEBUG] Iniciando Scraper do Promobit: {PROMOBIT_URL}")
    
    # 1. Configura navegador falso (Windows/Chrome)
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )

    try:
        # 2. Baixa o HTML da página
        response = scraper.get(PROMOBIT_URL)
        
        if response.status_code != 200:
            print(f"[DEBUG] Erro ao acessar Promobit: {response.status_code}")
            return []

        # 3. Parseia o HTML
        soup = BeautifulSoup(response.text, "html.parser")
        
        # O Promobit usa classes dinâmicas (ex: css-1hj7), então não podemos confiar nelas.
        # Estratégia: Buscar todos os links que contém "/oferta/" no href
        offer_links = soup.find_all("a", href=True)
        
        products = []
        seen_urls = set()

        print(f"[DEBUG] Total de links encontrados na página: {len(offer_links)}")

        for link_tag in offer_links:
            href = link_tag['href']
            
            # Filtra apenas links de oferta
            if "/oferta/" in href and href not in seen_urls:
                try:
                    # O Promobit estrutura o card assim: Link -> Divs -> Título/Preço
                    # Vamos tentar extrair dados de dentro desse link ou do pai dele
                    
                    # Título: Geralmente está num h1, h2 ou span dentro do link
                    title_tag = link_tag.find("h2") or link_tag.find("p") or link_tag.find("span")
                    if not title_tag:
                        # Às vezes o título está na propriedade 'title' do link ou imagem
                        img_tag = link_tag.find("img")
                        if img_tag and img_tag.get('alt'):
                            title = img_tag.get('alt')
                        else:
                            continue # Sem título, pula
                    else:
                        title = title_tag.get_text().strip()

                    # Preço: Procura qualquer texto com "R$" dentro do card
                    # Subimos para o elemento pai para ter uma visão melhor do card
                    card_container = link_tag.parent
                    price = "Ver Oferta"
                    
                    # Procura texto de preço no container
                    if card_container:
                        text_content = card_container.get_text()
                        if "R$" in text_content:
                            # Extração bruta do preço
                            import re
                            match = re.search(r'R\$\s?[\d\.,]+', text_content)
                            if match:
                                price = match.group(0)

                    # Link Final
                    full_link = f"https://www.promobit.com.br{href}"
                    
                    # Salvamos
                    seen_urls.add(href)
                    products.append({
                        "name": title,
                        "link": full_link,
                        "price": price,
                        "id": href # ID único
                    })
                    
                except Exception as e:
                    continue

        # Limita a 15 produtos para não spammar
        print(f"[DEBUG] Produtos extraídos do Promobit: {len(products)}")
        return products[:15]

    except Exception as e:
        print(f"[DEBUG] Erro crítico no scraper: {e}")
        return []

if __name__ == "__main__":
    items = get_best_sellers()
    for i in items:
        print(f" > {i['name']} | {i['price']}")