import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# URL da página de ofertas
URL_OFERTAS = "https://www.mercadolivre.com.br/ofertas?container_id=MLB779362-1&page=1"

def get_best_sellers():
    print("[DEBUG] Iniciando Selenium Padrão (com Stealth)...")
    
    # 1. Configurações para rodar no GitHub Actions
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # Modo invisível novo
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 2. TRUQUES ANTI-ROBÔ (Stealth Manual)
    # Isso remove a flag "navigator.webdriver" que denuncia o bot
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # User-Agent real
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    products = []

    try:
        # 3. Gerenciador de Driver AUTOMÁTICO (Resolve o erro v142 vs v143)
        print("[DEBUG] Instalando driver compatível...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Mascarar propriedades do navegador
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print(f"[DEBUG] Acessando: {URL_OFERTAS}")
        driver.get(URL_OFERTAS)
        
        # Espera humana
        time.sleep(random.uniform(3, 5))
        
        # Diagnóstico
        print(f"[DEBUG] Título da página: '{driver.title}'")
        
        if "Security" in driver.title or "human" in driver.title:
            print("[DEBUG] 🚨 Captcha detectado.")
            return []

        # Scroll para carregar imagens
        driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(2)

        print("[DEBUG] Extraindo produtos...")
        
        # Seletores
        items = driver.find_elements(By.CLASS_NAME, "promotion-item")
        if not items:
            items = driver.find_elements(By.CSS_SELECTOR, "li.ui-search-layout__item")
            
        print(f"[DEBUG] Itens encontrados no HTML: {len(items)}")

        for item in items[:15]:
            try:
                # Tenta extrair dados
                try:
                    title = item.find_element(By.CSS_SELECTOR, ".promotion-item__title, h2").text
                except: continue

                try:
                    link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                except: continue

                try:
                    price = f"R$ {item.find_element(By.CSS_SELECTOR, '.andes-money-amount__fraction').text}"
                except: price = "Ver Oferta"

                if title and link:
                    products.append({"name": title, "link": link, "price": price})
            except:
                continue

    except Exception as e:
        print(f"[DEBUG] Erro Selenium: {e}")

    finally:
        if driver:
            driver.quit()

    print(f"[DEBUG] Total extraído: {len(products)}")
    return products

if __name__ == "__main__":
    get_best_sellers()