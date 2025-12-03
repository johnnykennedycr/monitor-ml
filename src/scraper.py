import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random

# URL: Ofertas do dia (Página visual)
URL_OFERTAS = "https://www.mercadolivre.com.br/ofertas?container_id=MLB779362-1&page=1"

def get_best_sellers():
    print("[DEBUG] Iniciando Undetected Chrome...")
    
    # Opções para rodar no GitHub Actions (Linux Server)
    options = uc.ChromeOptions()
    options.add_argument('--headless=new') # Modo invisível moderno
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-popup-blocking')
    
    # User-Agent randômico para parecer humano
    options.add_argument(f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.{random.randint(0, 99)} Safari/537.36')

    driver = None
    products = []

    try:
        # O undetected-chromedriver baixa e "hackeia" o driver automaticamente
        driver = uc.Chrome(options=options, version_main=119) # Tenta fixar versão estável ou remova version_main se der erro
        
        print(f"[DEBUG] Acessando: {URL_OFERTAS}")
        driver.get(URL_OFERTAS)
        
        # Espera aleatória humana
        time.sleep(random.uniform(3, 5))

        # --- DIAGNÓSTICO DE ERRO ---
        # Vamos imprimir o título da página para saber onde caímos
        print(f"[DEBUG] Título da Página Carregada: '{driver.title}'")

        if "Security" in driver.title or "human" in driver.title:
            print("[DEBUG] 🚨 ALERTA: O Mercado Livre detectou o robô e mostrou Captcha.")
            return []

        # Tenta rolar a página para carregar imagens (lazy load)
        driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(2)

        # Seletores de Ofertas (O ML muda isso sempre, tentamos 2 opções)
        print("[DEBUG] Buscando elementos de produto...")
        
        # Tentativa 1: Classe de Card de Promoção
        items = driver.find_elements(By.CLASS_NAME, "promotion-item")
        
        # Tentativa 2: Seletor Genérico de Grid (caso o layout mude)
        if not items:
            items = driver.find_elements(By.CSS_SELECTOR, "li.ui-search-layout__item")

        print(f"[DEBUG] Itens encontrados: {len(items)}")

        for item in items[:15]:
            try:
                # Extração resiliente (try/except dentro do loop)
                try:
                    # Tenta pegar título
                    title_elem = item.find_element(By.CSS_SELECTOR, ".promotion-item__title, h2, .ui-search-item__title")
                    title = title_elem.text
                except:
                    continue # Sem título não serve

                try:
                    # Tenta pegar link
                    link_elem = item.find_element(By.TAG_NAME, "a")
                    link = link_elem.get_attribute("href")
                except:
                    continue

                try:
                    # Tenta pegar preço
                    price_elem = item.find_element(By.CSS_SELECTOR, ".andes-money-amount__fraction")
                    price = f"R$ {price_elem.text}"
                except:
                    price = "Ver Oferta"

                if title and link:
                    products.append({
                        "name": title,
                        "link": link,
                        "price": price
                    })
            except:
                continue

    except Exception as e:
        print(f"[DEBUG] Erro Undetected-Chrome: {e}")
        # Se der erro, imprime um pedaço do HTML para sabermos o que aconteceu
        if driver:
            try:
                print("[DEBUG] HTML da página (Primeiros 500 chars):")
                print(driver.page_source[:500])
            except:
                pass

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

    print(f"[DEBUG] Total extraído: {len(products)}")
    return products

if __name__ == "__main__":
    get_best_sellers()