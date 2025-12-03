import requests
from auth import get_access_token
import random

# IDs de categorias para monitorar (Ex: Celulares, Games, Eletrônicos)
# Você pode adicionar mais depois. MLB1051 = Celulares.
CATEGORIES = ["MLB1051", "MLB1144"] 

def get_best_sellers():
    token = get_access_token()
    if not token:
        print("[DEBUG] Token não disponível.")
        return []

    # Headers limpos (Sem disfarce de Chrome, pois estamos autenticados)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    all_products = []

    for cat_id in CATEGORIES:
        print(f"[DEBUG] Consultando categoria {cat_id}...")
        
        # TENTATIVA 1: API de Destaques (Highlights)
        # Essa rota geralmente não bloqueia tokens novos
        url_highlights = f"https://api.mercadolibre.com/highlights/MLB/category/{cat_id}"
        
        try:
            response = requests.get(url_highlights, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("content", [])
                print(f"[DEBUG] Sucesso via Highlights! {len(items)} itens recuperados.")
                
                for item in items:
                    # Highlights retorna dados parciais, as vezes precisamos tratar
                    if item.get("type") == "ITEM":
                        all_products.append({
                            "name": "Produto em Destaque (Ver Link)", # As vezes o highlight nao traz titulo direto
                            "link": item.get("permalink") or f"https://produto.mercadolivre.com.br/MLB-{item.get('id').replace('MLB', '')}",
                            "price": "Ver Oferta",
                            "id": item.get("id")
                        })
                continue # Se deu certo, vai pra proxima categoria
                
        except Exception as e:
            print(f"[DEBUG] Erro em Highlights: {e}")

        # TENTATIVA 2: Busca Filtrada (Sem termo de busca 'q', só filtros)
        # O ML bloqueia 'q=iphone' mas costuma liberar 'category=MLB...'
        url_search = "https://api.mercadolibre.com/sites/MLB/search"
        params = {
            "category": cat_id,
            "sort": "relevance",
            "limit": 5,
            # Filtro: Apenas itens novos (ajuda a evitar bloqueio de 'usados')
            "ITEM_CONDITION": "2230284" 
        }

        try:
            print("[DEBUG] Tentando busca direta por categoria...")
            response = requests.get(url_search, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                results = response.json().get("results", [])
                print(f"[DEBUG] Sucesso via Busca Categorizada! {len(results)} itens.")
                
                for item in results:
                    price = item.get("price")
                    currency = item.get("currency_id", "BRL")
                    
                    all_products.append({
                        "name": item.get("title"),
                        "link": item.get("permalink"),
                        "price": f"{currency} {price}",
                        "id": item.get("id")
                    })
            else:
                print(f"[DEBUG] Falha na busca da categoria {cat_id}: {response.status_code}")
                # Se der 403 aqui, é bloqueio final dessa categoria
                if response.status_code == 403:
                    print(f"[DEBUG] Detalhe do erro: {response.text}")

        except Exception as e:
            print(f"[DEBUG] Erro conexão busca: {e}")

    return all_products

if __name__ == "__main__":
    # Teste local
    items = get_best_sellers()
    for i in items:
        print(f"- {i['link']}")