import requests

AFFILIATE_TAG = "tepa6477885"

def generate_affiliate_link(url):
    api_url = "https://www.mercadolivre.com.br/afiliados/api/linkbuilder/meli"

    payload = {
        "tag": AFFILIATE_TAG,
        "urls": [url]
    }

    try:
        r = requests.post(api_url, json=payload)
        data = r.json()

        if "links" in data and len(data["links"]) > 0:
            return data["links"][0]["url"]

        return f"{url}?matt_word={AFFILIATE_TAG}"

    except:
        return f"{url}?matt_word={AFFILIATE_TAG}"
