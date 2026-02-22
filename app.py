import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import re
import time

st.title("🚌 りっちゃん＆パパのバス予報")

URL_A = "https://transfer-cloud.navitime.biz/tobubus/approachings?departure-busstop=00310731&arrival-busstop=00310765"
URL_B = "https://transfer-cloud.navitime.biz/tobubus/approachings?departure-busstop=00310731&arrival-busstop=00310737"

def get_bus_data(target_url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    # サーバー上のパスを直接指定するのだ！
    options.binary_location = "/usr/bin/chromium" 
    
    # Serviceの設定をシンプルにするのだ
    service = Service("/usr/bin/chromedriver")
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(target_url)
        time.sleep(3)
        body_text = driver.find_element("tag name", "body").text
        match = re.search(r"約\d+分", body_text)
        return match.group() if match else "情報なし"
    except Exception as e:
        return f"エラー発生なのだ"
    finally:
        try:
            driver.quit()
        except:
            pass

if st.button('最新のバスを調べるのだ！'):
    with st.spinner('スキャン中なのだ...'):
        res_a = get_bus_data(URL_A)
        res_b = get_bus_data(URL_B)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("上尾駅行き", res_a)
        with col2:
            st.metric("宮原駅行き", res_b)
