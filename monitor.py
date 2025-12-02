import os
import requests

SEU_CODIGO_SEC = os.getenv("SEU_CODIGO_SEC")

# Categorias do Mercado Livre para monitorar
CATEGORIAS = {
    "Smart TVs": "MLB1002",
    "Eletrônicos": "MLB186456",
    "Celulares": "MLB1055",
    "Informática": "MLB1648",
    "Eletrodomésticos": "MLB5726"
}

def gerar_link_afiliado(url_produto):
    return f"https://mercadolivre.com/sec/{SEU_CODIGO_SEC}?u={url_produto}"

def buscar_ofertas_categoria(category_id, desconto_minimo=15):
    url = f"https://api.mercadolibre.com/sites/MLB/search?category={category_id}&sort=discount_rate_desc"
    response = requests.get(url).json()
    results = response.get("results", [])

    ofertas = []

    for item in results:
        desconto = item.get("discount_rate", 0)
        preco_original = item.get("original_price")
        preco_atual = item["price"]

        if desconto and desconto >= desconto_minimo and preco_original:
            ofertas.append({
                "titulo": item["title"],
                "preco_atual": preco_atual,
                "preco_original": preco_original,
                "desconto": desconto,
                "link": gerar_link_afiliado(item["permalink"])
            })

    return ofertas


def main():
    print("🔍 Executando monitor Mercado Livre...")

    for nome, categoria in CATEGORIAS.items():
        ofertas = buscar_ofertas_categoria(categoria)

        if not ofertas:
            print(f"Nada novo em: {nome}")
            continue

        print(f"\n🔥 Ofertas encontradas em: {nome}")

        for oferta in ofertas[:5]:  # limita para evitar spam
            print("\n----------------------------------")
            print(f"📌 {oferta['titulo']}")
            print(f"💲 De R$ {oferta['preco_original']} por R$ {oferta['preco_atual']}")
            print(f"📉 Desconto: {oferta['desconto']}%")
            print(f"🔗 {oferta['link']}")
            print("----------------------------------")

    print("\n✔ Execução concluída.")


if __name__ == "__main__":
    main()
