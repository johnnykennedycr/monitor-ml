import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import os

# URL: Ofertas do dia
URL_OFERTAS = "https://www.mercadolivre.com.br/ofertas?container_id=MLB779362-1&page=1"

def get_best_sellers():
    print("[DEBUG] Iniciando Undetected Chrome (Auto-Version)...")
    
    options = uc.ChromeOptions()
    # Argumentos CRITICOS para rodar no GitHub Actions (Linux Headless)
    options.add_argument('--headless=new') 
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-popup-blocking')
    
    # User-Agent randômico
    options.add_argument(f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.{random.randint(0, 99)} Safari/537.36')

    driver = None
    products = []

    try:
        # CORREÇÃO PRINCIPAL: Removemos version_main=119.
        # Deixamos ele auto-detectar ou baixar a mais recente compatível.
        # O use_subprocess=True ajuda a evitar travamentos no Linux.
        driver = uc.Chrome(options=options, use_subprocess=True)
        
        print(f"[DEBUG] Acessando: {URL_OFERTAS}")
        driver.get(URL_OFERTAS)
        
        # Espera para carregar
        time.sleep(random.uniform(3, 5))
        
        print(f"[DEBUG] Título: '{driver.title}'")

        if "Security" in driver.title or "human" in driver.title:
            print("[DEBUG] 🚨 ALERTA: Captcha detectado.")
            # Tira um print para debug nos artefatos se precisar
            # driver.save_screenshot('captcha_error.png')
            return []

        # Scroll para carregar imagens
        driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(2)

        print("[DEBUG] Buscando elementos...")
        
        # Tenta coletores diferentes
        items = driver.find_elements(By.CLASS_NAME, "promotion-item")
        if not items:
            items = driver.find_elements(By.CSS_SELECTOR, "li.ui-search-layout__item")
            
        print(f"[DEBUG] Itens encontrados: {len(items)}")

        for item in items[:15]:
            try:
                # Tenta extrair dados (com tratamento de erro individual)
                try:
                    title = item.find_element(By.CSS_SELECTOR, ".promotion-item__title, h2, .ui-search-item__title").text
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
        print(f"[DEBUG] Erro Driver: {e}")
        # Se falhar a conexão, geralmente é erro de binário
        if "cannot connect" in str(e):
             print("[DEBUG] DICA: O driver falhou ao iniciar o processo do Chrome.")

    finally:
        if driver:
            try:
                driver.quit()
            except: pass

    print(f"[DEBUG] Total extraído: {len(products)}")
    return products

if __name__ == "__main__":
    get_best_sellers()