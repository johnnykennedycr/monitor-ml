import cloudscraper
from bs4 import BeautifulSoup
import time
import random

# URL de busca direta no site (não na API)
# Ordenado por "Mais relevantes" ou "Menor preço"
# Exemplo: Celulares em oferta
SEARCH_URL = "https://lista.mercadolivre.com.br/celulares-telefones/celulares-smartphones/celulares_NoIndex_True"

def get_best_sellers():
    print(f"[DEBUG] Iniciando scraping via HTML na URL: {SEARCH_URL}")
    
    # Cria um scraper que simula um navegador real (Chrome/Firefox)
    # Isso ajuda a burlar o erro 403 do Cloudflare/WAF
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )

    try:
        # Faz a requisição
        response = scraper.get(SEARCH_URL)
        
        if response.status_code != 200:
            print(f"[DEBUG] Falha ao acessar site: Status {response.status_code}")
            return []

        # Parseia o HTML
        soup = BeautifulSoup(response.text, "html.parser")
        
        # O Mercado Livre muda as classes CSS com frequência.
        # Buscamos pela lista de resultados (geralmente li.ui-search-layout__item)
        items = soup.find_all("li", class_="ui-search-layout__item")
        
        if not items:
            # Tenta um seletor alternativo (caso o layout mude para grade)
            items = soup.find_all("div", class_="ui-search-result__wrapper")

        print(f"[DEBUG] Encontrados {len(items)} elementos HTML de produtos.")

        results = []
        for item in items[:20]: # Pega os 20 primeiros
            try:
                # 1. Busca Título
                # Tenta achar H2, se não achar, tenta o link com classe de titulo
                title_tag = item.find("h2", class_="ui-search-item__title")
                if not title_tag:
                    title_tag = item.find("a", class_="ui-search-item__group__element")
                
                if not title_tag:
                    continue
                
                title = title_tag.get_text().strip()

                # 2. Busca Link
                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue
                link = link_tag['href']

                # 3. Busca Preço
                # O preço no ML é dividido em spans (moeda, valor, centavos)
                price_container = item.find("div", class_="ui-search-price__second-line")
                if not price_container:
                    price_container = item.find("div", class_="ui-search-result__price")
                
                price_text = "Preço não informado"
                if price_container:
                    price_fraction = price_container.find("span", class_="andes-money-amount__fraction")
                    if price_fraction:
                        price_text = f"R$ {price_fraction.get_text()}"

                results.append({
                    "name": title,
                    "link": link,
                    "price": price_text
                })

            except Exception as e:
                print(f"[DEBUG] Erro ao extrair item individual: {e}")
                continue

        print(f"[DEBUG] Produtos extraídos com sucesso: {len(results)}")
        return results

    except Exception as e:
        print(f"[DEBUG] Erro fatal no scraper HTML: {e}")
        return []

if __name__ == "__main__":
    # Teste local
    prod = get_best_sellers()
    for p in prod:
        print(f"{p['name']} - {p['price']}")