import cloudscraper
import json
import re
from bs4 import BeautifulSoup

# URL de busca
SEARCH_URL = "https://lista.mercadolivre.com.br/celulares-telefones/celulares-smartphones/celulares_NoIndex_True"

def get_best_sellers():
    print(f"[DEBUG] Iniciando scraping na URL: {SEARCH_URL}")
    
    # Simula um navegador Android (muitas vezes o ML é menos agressivo com mobile)
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'android',
            'mobile': True
        }
    )

    try:
        response = scraper.get(SEARCH_URL)
        
        # Parseia o HTML
        soup = BeautifulSoup(response.text, "html.parser")
        
        # --- DIAGNÓSTICO DE BLOQUEIO ---
        page_title = soup.title.string if soup.title else "Sem Título"
        print(f"[DEBUG] Título da página recebida: '{page_title}'")
        
        if "human" in page_title.lower() or "bot" in page_title.lower() or "security" in page_title.lower():
            print("[DEBUG] CRÍTICO: O GitHub Actions caiu no Captcha do Mercado Livre.")
            return []

        results = []

        # TENTATIVA 1: Busca via JSON embutido (Mais robusto)
        # O ML guarda o estado da busca numa variável javascript window.__PRELOADED_STATE__
        try:
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and "window.__PRELOADED_STATE__" in script.string:
                    print("[DEBUG] Encontrado state JSON oculto. Extraindo...")
                    
                    # Regex para limpar o javascript e pegar só o JSON
                    match = re.search(r"window\.__PRELOADED_STATE__\s*=\s*({.+?});", script.string)
                    if match:
                        json_str = match.group(1)
                        data = json.loads(json_str)
                        
                        # Navega no JSON gigante para achar os resultados
                        # A estrutura varia, mas geralmente é initialState -> results
                        results_data = data.get("initialState", {}).get("results", [])
                        
                        if results_data:
                            for item in results_data[:20]:
                                results.append({
                                    "name": item.get("title"),
                                    "link": item.get("permalink"),
                                    "price": f"R$ {item.get('price', {}).get('amount', 0)}",
                                    "id": item.get("id")
                                })
                            print(f"[DEBUG] Sucesso via JSON Extraction: {len(results)} produtos.")
                            return results
        except Exception as e:
            print(f"[DEBUG] Falha na extração JSON: {e}")

        # TENTATIVA 2: Seletores CSS Genéricos (Fallback)
        # Se o JSON falhar, tenta achar qualquer link que pareça um produto
        print("[DEBUG] Tentando fallback via HTML Tags...")
        
        # Procura containers de resultados genéricos
        items = soup.find_all("li", class_="ui-search-layout__item")
        
        if not items:
            # Tenta layout de grid
            items = soup.find_all("div", class_="ui-search-result__wrapper")
            
        for item in items[:20]:
            try:
                # Tenta achar o link
                link_tag = item.find("a", href=True)
                if not link_tag: continue
                
                link = link_tag['href']
                
                # Tenta achar o título (pode estar em h2, h3 ou span)
                title_tag = item.find("h2") or item.find("h3") or item.find("span", class_="ui-search-item__title")
                title = title_tag.get_text().strip() if title_tag else "Produto sem nome"
                
                # Preço
                price_tag = item.find("span", class_="andes-money-amount__fraction")
                price = f"R$ {price_tag.get_text()}" if price_tag else "R$ --"

                results.append({
                    "name": title,
                    "link": link,
                    "price": price
                })
            except:
                continue

        print(f"[DEBUG] Produtos extraídos via HTML: {len(results)}")
        return results

    except Exception as e:
        print(f"[DEBUG] Erro fatal no scraper: {e}")
        return []

if __name__ == "__main__":
    get_best_sellers()