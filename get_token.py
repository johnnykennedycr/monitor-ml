import requests

# --- PREENCHA SEUS DADOS AQUI ---
APP_ID = "5666604139240361"
CLIENT_SECRET = "g54iMbUXHQzOY9EAeiBevhVlUHTWfTR0"

# O código que você acabou de me mandar:
CODE = "TG-69300a02f23d730001b7f172-403543551"

# IMPORTANTE: Coloque aqui EXATAMENTE a url que você usou para conseguir o código.
# Se usou o Google, ponha "https://www.google.com"
# Se usou o seu site, ponha "https://www.jitatech.com.br"
REDIRECT_URI = "https://jitatech.com.br" 

print("Trocando código por token...")

url = "https://api.mercadolibre.com/oauth/token"
data = {
    "grant_type": "authorization_code",
    "client_id": APP_ID,
    "client_secret": CLIENT_SECRET,
    "code": CODE,
    "redirect_uri": REDIRECT_URI
}

resp = requests.post(url, data=data)

if resp.status_code == 200:
    data = resp.json()
    print("\n✅ SUCESSO! Aqui está seu Refresh Token:")
    print("------------------------------------------------")
    print(data['refresh_token'])
    print("------------------------------------------------")
    print("Copie este código acima e coloque no GitHub Secrets como ML_REFRESH_TOKEN")
else:
    print("❌ Erro:", resp.json())