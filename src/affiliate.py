import requests
import json

AFFILIATE_TAG = "tepa6477885"

def generate_affiliate_link(url):
    # transforma qualquer link em link afiliado
    api_url = "https://www.mercadolivre.com.br/afiliados/api/linkbuilder/meli"

    payload = {
        "urls": [url],
        "tag": AFFILIATE_TAG
    }

    try:
        response = requests.post(api_url, json=payload)
        data = response.json()

        return data["links"][0]["url"]
    except:
        # fallback: adiciona tag manualmente
        return f"{url}?matt_word={AFFILIATE_TAG}"
