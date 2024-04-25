# -*- coding: utf-8 -*-
"""
Created on Tue Apr  9 23:04:47 2024

@author: pedro
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup
import pandas as pd
import re

# Função para processar a coluna de descrição
def process_description(description):
    
    # Dicionário para mapear os meses de inglês para números
    months_map = {
        'January': '01', 'February': '02', 'March': '03', 'April': '04',
        'May': '05', 'June': '06', 'July': '07', 'August': '08',
        'September': '09', 'October': '10', 'November': '11', 'December': '12'
    }
    
    # Extrair likes
    likes_match = re.search(r'(\d+[\.,]?\d*|\d+K) likes', description)
    if likes_match:
        likes = likes_match.group(1).replace('K', '000').replace(',', '')
        likes = int(float(likes)) if '.' in likes else int(likes)
    else:
        likes = 0  # Assume zero se não encontrado
    
    # Extrair comments
    comments_match = re.search(r'(\d+[\.,]?\d*|\d+K) comments', description)
    if comments_match:
        comments = comments_match.group(1).replace('K', '000').replace(',', '')
        comments = int(float(comments)) if '.' in comments else int(comments)
    else:
        comments = 0  # Assume zero se não encontrado

    # Extrair a data
    month_found = re.search(r'(' + '|'.join(months_map.keys()) + ')', description)
    day_year_match = re.search(r'(\d+), (\d{4})', description)
    if month_found and day_year_match:
        day, year = day_year_match.groups()
        month = months_map[month_found.group(0)]
        date = f'{day}/{month}/{year}'
    else:
        date = 'Unknown'

    # Extrair a descrição resumida
    desc_text = description.split(' : ')[-1].strip('"')

    return pd.Series([likes, comments, date, desc_text])

def instagram_login(driver, username, password):
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5)  # Espera a página de login carregar

    # Encontra os campos de login e senha, preenche e submete o formulário
    username_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.NAME, "username")))
    password_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.NAME, "password")))

    username_input.send_keys(username)
    password_input.send_keys(password)

    password_input.submit()  # Submetendo o formulário de login
    time.sleep(5)  # Espera para a autenticação ser processada

def scrape_profile(driver, profile_url, scrolls):
    driver.get(profile_url)
    driver.execute_script("document.body.style.zoom='75%'")  # Ajustando o zoom para 75%
    time.sleep(2)

    post_urls = set()  # Utiliza um conjunto para evitar URLs duplicados
    scroll_height = 2000  # Define a altura do scroll

    for _ in range(scrolls):  # Aumentar o número de iterações conforme necessário
        current_posts = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a[href*="/p/"]'))
        )
        post_urls.update([post.get_attribute('href') for post in current_posts if '/p/' in post.get_attribute('href')])

        driver.execute_script(f"window.scrollBy(0, {scroll_height});")  # Rola uma altura específica em pixels
        time.sleep(3)  # Tempo para carregar novos posts após cada rolagem

    return list(post_urls)

def scrape_instagram_posts(profile_posts):
    data = []
    failed_urls = []
    driver = webdriver.Chrome()
    driver.set_window_position(1920, 0)
    driver.maximize_window()

    for profile, urls in profile_posts.items():
        source = profile.split('/')[-2]  # Extrai o nome da fonte do URL do perfil
        for url in urls:
            attempts = 0
            successful = False
            while attempts < 3 and not successful:
                try:
                    driver.get(url)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    page_html = driver.page_source
                    soup = BeautifulSoup(page_html, 'html.parser')
                    
                    title_tag = soup.find('meta', property='og:title')
                    description_tag = soup.find('meta', property='og:description')
                    
                    title = title_tag['content'] if title_tag else 'Título não encontrado'
                    description = description_tag['content'] if description_tag else 'Descrição não encontrada'
                    print(f'Titulo encontrado: {title}\n')
                    print(f'description encontrada: {description}\n')
                    if title != 'Título não encontrado':
                        data.append({
                            'url': url,
                            'title': title,
                            'description': description,
                            'source': source
                        })
                        successful = True
                        
                    else:
                        raise ValueError("Conteúdo não encontrado")
                        
                except Exception as e:
                    print(f"Erro ao carregar a página {url}, tentativa {attempts+1}: {e}")
                    # Fecha a aba antiga e abre uma nova
                    driver.close()
                    driver.execute_script("window.open('');")
                    driver.switch_to.window(driver.window_handles[-1])
                    attempts += 1
                    time.sleep(10)  # Espera antes de tentar novamente

            if not successful:
                print(f"Desistindo após 3 tentativas: {url}")
                failed_urls.append(url)
                # Salva os dados e URLs falhos em um arquivo Excel com duas abas
                try:
                    # Salva os dados e URLs falhos em um arquivo Excel com duas abas
                    writer = pd.ExcelWriter('instagram_scraping_results.xlsx', engine='xlsxwriter')
                    pd.DataFrame(data).to_excel(writer, sheet_name='Data', index=False)
                    pd.DataFrame({'Failed URLs': failed_urls}).to_excel(writer, sheet_name='Failed URLs', index=False)
                    writer.save()
                except Exception as save_error:
                    print(f"Erro ao salvar o arquivo Excel: {save_error}")
                    
    driver.quit()
    return pd.DataFrame(data)

username = 'YOUR_INSTAGRAM_ACCOUNT'
password = 'YOUR_INSTAGRAM_PASSWORD'

profiles = ["https://www.instagram.com/infomoney/", "https://www.instagram.com/estadao/",
             "https://www.instagram.com/valoreconomico/", "https://www.instagram.com/jornaloglobo/",
             "https://www.instagram.com/cnnbrasil/", "https://www.instagram.com/valorinveste/",
             "https://www.instagram.com/bbcbrasil/", "https://www.instagram.com/folhadespaulo/",
             "https://www.instagram.com/portalg1/", "https://www.instagram.com/uolnoticias/",
             "https://www.instagram.com/exame/", "https://www.instagram.com/elpaisbrasil/",
             "https://www.instagram.com/revistaoeste/", "https://www.instagram.com/cartacapital/",
             "https://www.instagram.com/agencia.brasil/", "https://www.instagram.com/thecompass.br/",
             "https://www.instagram.com/sbtnews/", "https://www.instagram.com/jovempannews/",
             "https://www.instagram.com/revistaepoca/", "https://www.instagram.com/revistaistoe/",
             "https://www.instagram.com/bandnewstv/"            
            ]

driver = webdriver.Chrome()
driver.set_window_position(1920, 0)
driver.maximize_window()
instagram_login(driver, username, password)

scrolls = 60
profile_posts = {}
for profile in profiles:
    profile_posts[profile] = scrape_profile(driver, profile, scrolls)

driver.quit()

df_insta_news = scrape_instagram_posts(profile_posts)

# Aplicar a função ao dataframe para criar novas colunas
df_insta_news[['likes', 'comments', 'date', 'short_description']] = df_insta_news['description'].apply(process_description)
