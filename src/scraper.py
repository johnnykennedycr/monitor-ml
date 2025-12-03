import feedparser
import cloudscraper
import requests
import time

# Lista de Feeds para monitorar
FEEDS = [
    {"name": "Gatry", "url": "https://gatry.com/feed"},
    {"name": "Hardmob", "url": "https://www.hardmob.com.br/external.php?type=RSS2&forumids=407"}
]

def get_real_link(url):
    """
    Segue o redirecionamento para pegar o link final do Mercado Livre
    """
    try:
        # Headers para evitar bloqueio no HEAD request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        resp = requests.head(url, headers=headers, allow_redirects=True, timeout=5)
        return resp.url
    except:
        return url

def get_best_sellers():
    print("[DEBUG] Iniciando Agregador de RSS (Blindado)...")
    
    # Cria o scraper para baixar o XML passando pelo Cloudflare
    scraper = cloudscraper.create_scraper()
    
    all_products = []
    
    for source in FEEDS:
        print(f"[DEBUG] Lendo Feed: {source['name']} ({source['url']})")
        
        try:
            # 1. Baixa o conteúdo XML usando o scraper (fura bloqueio)
            response = scraper.get(source['url'])
            
            if response.status_code != 200:
                print(f"[DEBUG] Erro ao baixar feed {source['name']}: {response.status_code}")
                continue

            # 2. Passa o texto XML baixado para o feedparser
            feed = feedparser.parse(response.text)
            
            print(f"[DEBUG] {source['name']}: {len(feed.entries)} itens encontrados.")
            
            # 3. Processa os itens
            for entry in feed.entries[:15]: # Top 15 de cada site
                title = entry.title
                link_original = entry.link
                
                # Filtro: Busca por "Mercado Livre" no título ou link
                # (Hardmob e Gatry costumam colocar o nome da loja no titulo)
                is_ml = "mercado livre" in title.lower() or "mercadolivre" in title.lower() or "mercadolivre" in link_original.lower()
                
                if is_ml:
                    # Tenta limpar o preço do título (Ex: "iPhone - R$ 2000 - ML")
                    price = "Ver Oferta"
                    if "R$" in title:
                        try:
                            # Lógica simples para pegar o valor após R$
                            parts = title.split("R$")
                            if len(parts) > 1:
                                price_part = parts[1].strip().split(" ")[0] # Pega o primeiro token depois do R$
                                # Remove caracteres estranhos se vierem (ex: 2.000,00...)
                                price = f"R$ {price_part}"
                        except:
                            pass

                    # Resolve link final (importante para afiliado)
                    final_link = get_real_link(link_original)
                    
                    # Verifica novamente se o link final é ML (segurança)
                    if "mercadolivre.com.br" in final_link:
                        # Remove parâmetros de tracking antigos para por o seu limpo depois
                        if "?" in final_link:
                            final_link = final_link.split("?")[0]

                        all_products.append({
                            "name": title,
                            "link": final_link,
                            "price": price,
                            # Usa o link como ID único para evitar duplicatas
                            "id": final_link 
                        })

        except Exception as e:
            print(f"[DEBUG] Erro processando {source['name']}: {e}")

    # Remove duplicatas (caso o mesmo produto apareça nos dois feeds)
    unique_products = []
    seen_links = set()
    for p in all_products:
        if p['link'] not in seen_links:
            unique_products.append(p)
            seen_links.add(p['link'])

    print(f"[DEBUG] Total de produtos ML filtrados: {len(unique_products)}")
    return unique_products

if __name__ == "__main__":
    items = get_best_sellers()
    for i in items:
        print(f" > {i['name']}")