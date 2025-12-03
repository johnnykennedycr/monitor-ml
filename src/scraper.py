import cloudscraper
import random
import time

# Categorias: Celulares (MLB1051), Games (MLB1144), Informática (MLB1648)
CATEGORIES = ["MLB1051", "MLB1144"]

def get_best_sellers():
    print("[DEBUG] Iniciando scraper em MODO ANÔNIMO (Bypassing Token)...")
    
    # Cria um navegador falso robusto (finge ser Chrome no Windows)
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )

    all_products = []

    for cat_id in CATEGORIES:
        # TÁTICA 1: API Pública sem Token (Como um visitante comum)
        # O segredo aqui é NÃO mandar o header Authorization
        url = "https://api.mercadolibre.com/sites/MLB/search"
        
        params = {
            "category": cat_id,
            "sort": "relevance", # Ou 'price_asc' para baratos
            "limit": 5,
            "condition": "new" # Apenas novos
        }

        print(f"[DEBUG] Tentando categoria {cat_id} via API Pública...")
        
        try:
            # Usamos scraper.get em vez de requests.get para enganar o WAF (Firewall)
            response = scraper.get(url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"[DEBUG] SUCESSO! {len(results)} produtos encontrados.")
                
                for item in results:
                    price = item.get("price")
                    currency = item.get("currency_id", "BRL")
                    
                    all_products.append({
                        "name": item.get("title"),
                        "link": item.get("permalink"),
                        "price": f"{currency} {price}",
                        "id": item.get("id")
                    })
                
                # Pequena pausa para não parecer ataque DDoS
                time.sleep(2)
                continue # Vai para a próxima categoria
            
            elif response.status_code == 403:
                print("[DEBUG] Bloqueio 403 na API Pública (IP do GitHub queimado).")
            else:
                print(f"[DEBUG] Falha API: {response.status_code}")

        except Exception as e:
            print(f"[DEBUG] Erro de conexão: {e}")

        # TÁTICA 2 (Plano B): API Interna do Frontend (JMS)
        # Se a API oficial falhar, tentamos a API que o site www.mercadolivre.com.br usa
        print("[DEBUG] Tentando Plano B (API Interna Frontend)...")
        try:
            # Esta URL é "secreta", usada pelo javascript do site
            internal_url = f"https://www.mercadolivre.com.br/jms/mlb/search?category={cat_id}&limit=5"
            # Precisamos de headers que pareçam muito reais
            headers_b = {
                "Referer": "https://www.mercadolivre.com.br/",
                "X-Requested-With": "XMLHttpRequest"
            }
            
            resp_b = scraper.get(internal_url, headers=headers_b)
            
            if resp_b.status_code == 200:
                data_b = resp_b.json()
                # A estrutura aqui é diferente (Geralmente results ou groups)
                # O JMS retorna uma estrutura complexa, tentamos achar a lista
                items_b = data_b.get("results", [])
                
                # Se não achar em results, tenta achar nos componentes de layout (mais complexo)
                if not items_b and "content" in data_b:
                     # Lógica simplificada para não quebrar
                     pass

                if items_b:
                    print(f"[DEBUG] SUCESSO via Plano B! {len(items_b)} itens.")
                    for item in items_b:
                        # Extração adaptada para o JSON interno
                        title = item.get("title", {}).get("text", "Oferta") if isinstance(item.get("title"), dict) else item.get("title")
                        link = item.get("permalink")
                        price_obj = item.get("price", {}).get("amount", 0)
                        
                        if title and link:
                            all_products.append({
                                "name": title,
                                "link": link,
                                "price": f"R$ {price_obj}",
                                "id": item.get("id")
                            })
            else:
                print(f"[DEBUG] Plano B falhou: {resp_b.status_code}")

        except Exception as e:
            print(f"[DEBUG] Erro no Plano B: {e}")

    return all_products

if __name__ == "__main__":
    items = get_best_sellers()
    for i in items:
        print(f"- {i['name']}")