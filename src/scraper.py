import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# URL simplificada (menos chance de erro)
URL_OFERTAS = "https://www.mercadolivre.com.br/ofertas"

def get_best_sellers():
    print("[DEBUG] Iniciando Selenium (Estratégia Genérica)...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Disfarce Anti-Bot
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    products = []

    try:
        print("[DEBUG] Instalando driver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Mascarar webdriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print(f"[DEBUG] Acessando: {URL_OFERTAS}")
        driver.get(URL_OFERTAS)
        
        time.sleep(random.uniform(3, 6))
        
        # Scroll progressivo para garantir carregamento
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(2)

        print(f"[DEBUG] Título: '{driver.title}'")

        if "Security" in driver.title:
            print("[DEBUG] 🚨 Bloqueio de Segurança detectado.")
            return []

        # --- ESTRATÉGIA: REDE DE ARRASTO (XPath) ---
        print("[DEBUG] Procurando produtos via estrutura genérica...")
        
        # Procura qualquer elemento que contenha texto de preço (R$)
        # E sobe na árvore DOM para achar o container do produto
        found_elements = driver.find_elements(By.XPATH, "//li[descendant::span[contains(text(), 'R$')]]")
        
        if not found_elements:
            # Fallback para divs (as vezes muda para div)
            found_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'item') and descendant::span[contains(text(), 'R$')]]")

        print(f"[DEBUG] Elementos candidatos encontrados: {len(found_elements)}")

        # DEBUG SUPREMO: Se der 0, imprime o HTML para vermos o que tem na página
        if len(found_elements) == 0:
            print("\n--- INICIO DEBUG HTML (Primeiros 2000 chars) ---")
            print(driver.page_source[:2000])
            print("--- FIM DEBUG HTML ---\n")

        for item in found_elements[:15]:
            try:
                # Tenta extrair texto completo do elemento para parsear
                text_content = item.text.split('\n')
                
                # Link é fundamental
                try:
                    link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                except:
                    continue

                # Preço (busca pelo símbolo)
                price = "Ver Oferta"
                for line in text_content:
                    if "R$" in line:
                        price = line
                        break
                
                # Título (geralmente a primeira ou segunda linha que não é preço)
                title = "Oferta Imperdível"
                for line in text_content:
                    if len(line) > 10 and "R$" not in line and "%" not in line:
                        title = line
                        break

                if link and "mercadolivre" in link:
                    products.append({"name": title, "link": link, "price": price})

            except Exception as e:
                continue

    except Exception as e:
        print(f"[DEBUG] Erro Geral: {e}")

    finally:
        if driver:
            driver.quit()

    print(f"[DEBUG] Total extraído: {len(products)}")
    return products

if __name__ == "__main__":
    get_best_sellers()