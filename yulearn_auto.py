import requests
from bs4 import BeautifulSoup
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Secrets'tan bilgiler çekiliyor
USERNAME = os.environ.get("MOODLE_USERNAME")
PASSWORD = os.environ.get("MOODLE_PASSWORD")
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER2")

COURSE_IDS = [45000, 46000] # BURAYA ARKADAŞININ DERS ID'LERİNİ YAZ
STATE_FILE = "arkadas_state.json"

def get_automated_session():
    # Bulduğumuz o özel giriş linki
    login_url = "https://yulearn.yeditepe.edu.tr/login/index.php?authmethod=moodle"
    session = requests.Session()
    
    try:
        # 1. Sayfayı aç ve logintoken yakala
        res = session.get(login_url)
        soup = BeautifulSoup(res.text, 'html.parser')
        token = soup.find('input', {'name': 'logintoken'})['value']
        
        # 2. Giriş yap
        payload = {
            'username': USERNAME,
            'password': PASSWORD,
            'logintoken': token
        }
        
        # Moodle bazen 'login' sonrası yönlendirme yapar, Session bunu otomatik tutar
        post_res = session.post("https://yulearn.yeditepe.edu.tr/login/index.php", data=payload)
        
        if "login" not in post_res.url:
            print("--> Başarılı: Arkadaşının hesabı için yeni bilet alındı!")
            return session
        else:
            print("--> Hata: Otomatik giriş başarısız. Şifreyi kontrol et.")
            return None
    except Exception as e:
        print(f"Otomasyon Hatası: {e}")
        return None

# (Geri kalan send_email ve main fonksiyonları senin kodunla aynı, 
# sadece get_course_materials içinde COOKIES yerine session.get kullanacağız)
