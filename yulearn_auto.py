import requests
from bs4 import BeautifulSoup
import os

# GitHub Secrets'tan gelecek bilgiler
USERNAME = os.environ.get("EMAIL_RECEIVER") # Okul numaran
PASSWORD = os.environ.get("MOODLE_PASSWORD") # Okul şifren

def get_session_with_login():
    login_url = "https://yulearn.yeditepe.edu.tr/login/index.php"
    session = requests.Session()
    
    try:
        # 1. Giriş sayfasını açıp gizli "logintoken"ı almamız gerekir (Moodle güvenliği)
        response = session.get(login_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        login_token = soup.find('input', {'name': 'logintoken'})['value']
        
        # 2. Giriş bilgilerini gönder
        payload = {
            'username': USERNAME,
            'password': PASSWORD,
            'logintoken': login_token
        }
        
        post_response = session.post(login_url, data=payload)
        
        # Giriş başarılı mı kontrol et (URL değişmiş olmalı)
        if "login" not in post_response.url:
            print("--> Otomatik giriş başarılı!")
            return session
        else:
            print("--> Giriş başarısız! Bilgileri kontrol et.")
            return None
            
    except Exception as e:
        print(f"Giriş hatası: {e}")
        return None

# Test için çalıştıralım
if __name__ == "__main__":
    session = get_session_with_login()
    if session:
        # Örnek bir ders sayfasını çekmeye çalışalım
        test_url = "https://yulearn.yeditepe.edu.tr/course/view.php?id=47716"
        res = session.get(test_url)
        if "İşletim Sistemleri" in res.text:
            print("BAŞARILI: Ders içeriğine ulaşıldı!")
