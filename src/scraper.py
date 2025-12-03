import feedparser
import requests
import time

# URL do Feed RSS do Gatry (Promoções Gerais)
RSS_URL = "https://gatry.com/feed"

def get_real_link(url):
    """
    O link do RSS vem como 'gatry.com/...'
    Essa função segue o redirecionamento para pegar o link final 'mercadolivre.com.br...'
    para que você possa gerar seu link de afiliado corretamente.
    """
    try:
        # Faz uma requisição HEAD (sem baixar o corpo) só para seguir o redirect
        resp = requests.head(url, allow_redirects=True, timeout=5)
        return resp.url
    except:
        return url

def get_best_sellers():
    print(f"[DEBUG] Lendo Feed RSS: {RSS_URL}")
    
    # 1. Baixa e processa o XML do RSS
    feed = feedparser.parse(RSS_URL)
    
    print(f"[DEBUG] Itens no feed: {len(feed.entries)}")
    
    products = []
    
    # 2. Itera sobre as últimas notícias
    for entry in feed.entries[:20]: # Olha as 20 últimas
        title = entry.title
        link_gatry = entry.link
        category = entry.get('category', '').lower()
        
        # 3. FILTRO: Só queremos Mercado Livre
        # O Gatry costuma colocar a loja no título ou na categoria
        # Ex: "iPhone 13 - R$ 3000 - Mercado Livre"
        is_ml = "mercado livre" in title.lower() or "mercadolivre" in title.lower()
        
        if is_ml:
            # Pega o preço se estiver na descrição (O Gatry poe o preço no titulo geralmente)
            # Mas vamos deixar genérico
            price = "Ver Oferta"
            if "R$" in title:
                # Tenta extrair o preço do título de forma simples
                parts = title.split("R$")
                if len(parts) > 1:
                    price = "R$" + parts[1].split(" ")[1] # Pega o valor logo depois do R$

            # Descobre o link real do ML
            final_link = get_real_link(link_gatry)
            
            # Só adiciona se o link final for realmente do ML (segurança extra)
            if "mercadolivre.com.br" in final_link:
                products.append({
                    "name": title,
                    "link": final_link, # Link limpo do ML
                    "price": price,
                    "id": entry.id # ID único do post para não repetir
                })

    print(f"[DEBUG] Produtos do Mercado Livre encontrados: {len(products)}")
    return products

if __name__ == "__main__":
    items = get_best_sellers()
    for i in items:
        print(f"itemName: {i['name']} | Link: {i['link']}")