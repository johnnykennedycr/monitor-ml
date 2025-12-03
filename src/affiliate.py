import requests

AFFILIATE_TAG = "tepa6477885"

def generate_affiliate_link(url):
    # API oficial do programa de afiliados
    api_url = "https://www.mercadolivre.com.br/afiliados/api/linkbuilder/meli"

    payload = {
        "tag": AFFILIATE_TAG,
        "urls": [url]
    }
    
    # Adicionei headers para evitar bloqueio 403/401
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(api_url, json=payload, headers=headers, timeout=10)
        data = r.json()

        # Verifica se a API retornou o link encurtado corretamente
        if "links" in data and len(data["links"]) > 0:
            return data["links"][0]["url"]
        
        # Fallback se a API falhar
        print(f"[DEBUG] API Afiliado falhou, usando fallback. Status: {r.status_code}")
        return f"{url}?matt_word={AFFILIATE_TAG}"

    except Exception as e:
        print(f"[DEBUG] Erro no afiliado: {e}")
        return f"{url}?matt_word={AFFILIATE_TAG}"