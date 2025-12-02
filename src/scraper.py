import requests
from bs4 import BeautifulSoup

URL_BEST_SELLERS = "https://www.mercadolivre.com.br/mais-vendidos"

def get_best_sellers():
    response = requests.get(URL_BEST_Sellers, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")

    products = []
    items = soup.select("a.ui-item__link")

    for item in items[:20]:
        name = item.get("title") or item.text.strip()
        link = item.get("href")

        if name and link:
            products.append({
                "name": name,
                "link": link
            })

    return products
