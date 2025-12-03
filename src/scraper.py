import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# URL da página de ofertas do dia (HTML real)
URL_OFERTAS = "https://www.mercadolivre.com.br/ofertas?container_id=MLB779362-1&page=1"

def get_best_sellers():
    print("[DEBUG] Iniciando Selenium (Chrome Headless)...")
    
    # Configurações para rodar no servidor (GitHub Actions)
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Roda sem interface gráfica
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    # User-Agent real para não parecer robô
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    products = []

    try:
        # Instala e inicia o driver do Chrome automaticamente
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print(f"[DEBUG] Acessando URL: {URL_OFERTAS}")
        driver.get(URL_OFERTAS)
        
        # Espera até 10s para a lista de produtos carregar
        print("[DEBUG] Aguardando carregamento da página...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "promotion-item"))
        )
        
        # Pequeno scroll para garantir que imagens/preços carreguem
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)

        # Busca os cards de produto (a classe pode variar, ajustamos as mais comuns)
        items = driver.find_elements(By.CLASS_NAME, "promotion-item")
        
        print(f"[DEBUG] Elementos encontrados no HTML: {len(items)}")

        for item in items[:15]: # Pega os top 15
            try:
                # Tenta extrair título
                try:
                    title = item.find_element(By.CLASS_NAME, "promotion-item__title").text
                except:
                    continue # Sem título, pula

                # Tenta extrair link
                try:
                    link = item.find_element(By.CLASS_NAME, "promotion-item__link-container").get_attribute("href")
                except:
                    continue

                # Tenta extrair preço
                try:
                    price_container = item.find_element(By.CLASS_NAME, "andes-money-amount__fraction")
                    price = f"R$ {price_container.text}"
                except:
                    price = "Ver Oferta"

                if title and link:
                    products.append({
                        "name": title,
                        "link": link,
                        "price": price
                    })
            except Exception as e:
                # Erro ao processar um item específico, ignora e vai pro próximo
                continue

    except Exception as e:
        print(f"[DEBUG] Erro Crítico no Selenium: {e}")
        # Tira um print da tela para debug se der erro (opcional, ajuda muito)
        if driver:
             print("[DEBUG] Url final:", driver.current_url)

    finally:
        if driver:
            driver.quit()
            print("[DEBUG] Navegador fechado.")

    print(f"[DEBUG] Total de produtos extraídos: {len(products)}")
    return products

if __name__ == "__main__":
    res = get_best_sellers()
    for p in res:
        print(f"{p['name']} - {p['price']}")