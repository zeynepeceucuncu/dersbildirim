import requests
from bs4 import BeautifulSoup
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- YAPILANDIRMA ---
USERNAME = os.environ.get("Onur_USERNAME")
PASSWORD = os.environ.get("Onur_PASSWORD")
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("Onur_USERNAME") # Secrets'ta ARKADAS_EMAIL olarak kaydetmeni öneririm

COURSE_IDS = [47716] # Onur'un ders ID'leri
STATE_FILE = "arkadas_state.json"

def get_automated_session():
    """Kullanıcı adı ve şifre ile giriş yapıp canlı bir session döndürür."""
    login_url = "https://yulearn.yeditepe.edu.tr/login/index.php?authmethod=moodle"
    session = requests.Session()
    
    try:
        # 1. Giriş sayfasındaki gizli token'ı al
        res = session.get(login_url)
        soup = BeautifulSoup(res.text, 'html.parser')
        token = soup.find('input', {'name': 'logintoken'})['value']
        
        # 2. Giriş bilgilerini gönder
        payload = {
            'username': USERNAME,
            'password': PASSWORD,
            'logintoken': token
        }
        
        post_res = session.post("https://yulearn.yeditepe.edu.tr/login/index.php", data=payload)
        
        if "login" not in post_res.url:
            print(f"--> Başarılı: {USERNAME} için otomatik giriş yapıldı!")
            return session
        else:
            print("--> Hata: Giriş başarısız! Şifre yanlış olabilir veya Google duvarı çıktı.")
            return None
    except Exception as e:
        print(f"Otomasyon Hatası: {e}")
        return None

def get_course_materials(course_id, user_cookie):
    url = f"https://yulearn.yeditepe.edu.tr/course/view.php?id={course_id}"
    cookies = {"MoodleSession": user_cookie}
    try:
        # allow_redirects=False yaparak sonsuz yönlendirme döngüsünü en başta kırıyoruz!
        response = requests.get(url, cookies=cookies, allow_redirects=False)
        
        # Moodle, bilet geçersiz olduğunda 302 (Yönlendirme) kodu döndürür
        if response.status_code == 302 or "login" in response.headers.get('Location', ''):
            return "EXPIRED"
            
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        items = {}
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # 1. Klasik Dosyalar (PDF, Ödev, Slide)
            if '/mod/' in href and 'id=' in href:
                item_name = a_tag.get_text(strip=True)
                if item_name and "Mark as done" not in item_name:
                    items[href] = item_name
            
            # 2. ÖZEL DURUM: Eğer bu bir 'Duyurular' forumu ise içine girip başlıkları tara
            if '/mod/forum/view.php' in href:
                print(f"--> Duyuru panosuna giriliyor: {href}")
                forum_res = requests.get(href, cookies=cookies, allow_redirects=False)
                
                # Duyuru linkinde de bilet kontrolü yapalım
                if forum_res.status_code == 302:
                    continue
                    
                forum_soup = BeautifulSoup(forum_res.text, 'html.parser')
                for discussion in forum_soup.find_all('a', href=True):
                    if 'discuss.php?d=' in discussion['href']:
                        disc_title = "📣 DUYURU: " + discussion.get_text(strip=True)
                        items[discussion['href']] = disc_title

        return items
    except Exception as e:
        print(f"Hata (Ders {course_id}): {e}")
        return None

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("--> Arkadaşına mail başarıyla gönderildi!")
    except Exception as e:
        print(f"Mail Gönderim Hatası: {e}")

def main():
    # 1. Önce giriş yapıp bileti (session) al
    session = get_automated_session()
    if not session:
        return # Giriş yapılamadıysa dur

    # 2. Eski durumu yükle
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
    else:
        state = {}

    changes_detected = False
    email_body = "Yulearn sisteminde senin için yeni güncellemeler var!\n\n"

    for course_id in COURSE_IDS:
        print(f"Ders {course_id} taranıyor...")
        current_materials = get_course_materials(session, course_id)
        
        if current_materials is None: continue
            
        old_materials = state.get(str(course_id), {})
        new_links = set(current_materials.keys()) - set(old_materials.keys())
        
        if new_links and old_materials:
            changes_detected = True
            email_body += f"--- DERS ID: {course_id} ---\n"
            for link in new_links:
                item_name = current_materials[link]
                email_body += f"📌 YENİ EKLENDİ: {item_name}\n   Link: {link}\n\n"
        
        state[str(course_id)] = current_materials

    # 3. Değişiklik varsa mail at
    if changes_detected:
        send_email("Yulearn Otomatik Duyuru Sistemi", email_body)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
    else:
        print("Arkadaşın için yeni bir güncelleme yok.")

if __name__ == "__main__":
    main()
