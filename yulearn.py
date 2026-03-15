import requests
from bs4 import BeautifulSoup
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- YAPILANDIRMA AYARLARI (GÜVENLİ VERSİYON) ---
# Bilgiler artık GitHub Secrets üzerinden çekilecek
COOKIES = {
    "MoodleSession": os.environ.get("MOODLE_COOKIE") 
}

COURSE_IDS = [47716] # İşletim Sistemleri

EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") 
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

STATE_FILE = "yulearn_scraping_state.json"

# ... KODUN GERİ KALANI BURADAN İTİBAREN AYNI ...

def get_course_materials(course_id):
    """Dersin sayfasına girer ve eklenmiş tüm materyal/duyuru linklerini toplar."""
    url = f"https://yulearn.yeditepe.edu.tr/course/view.php?id={course_id}"
    
    try:
        # Siteye cookie (bilet) ile giriş yapıyoruz
        response = requests.get(url, cookies=COOKIES, allow_redirects=True)
        response.raise_for_status()
        
        # Eğer site bizi giriş sayfasına atarsa biletin süresi dolmuş demektir
        if "login" in response.url:
            print(f"HATA: Biletin (Cookie) süresi dolmuş! Lütfen tarayıcıdan yeni bir MoodleSession al.")
            send_email("🚨 Yulearn Bot Alarmı: Biletin Süresi Doldu!", " MoodleSession biletinin süresi dolmuş.\n\nMüsait olduğunda tarayıcıdan Yulearn'e girip yeni bileti GitHub Secrets (MOODLE_COOKIE) kısmına yapıştırabilir misin?\n\nYenisini ekleyene kadar nöbeti durduruyorum. 🫡")
            return None

        # Sayfanın HTML kodunu okuyoruz
        soup = BeautifulSoup(response.text, 'html.parser')
        items = {}
        
        # Sayfadaki TÜM tıklanabilir linkleri (a etiketlerini) bul
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Eğer linkin içinde "/mod/" varsa bu bir Moodle materyalidir (ödev, dosya, forum vb.)
            if '/mod/' in href and 'id=' in href:
                item_name = a_tag.get_text(strip=True)
                
                # İsim boş değilse ve gereksiz "Mark as done" gibi yazılar içermiyorsa kaydet
                if item_name and "Mark as done" not in item_name:
                    # Linkin kendisini benzersiz bir ID olarak kullanıyoruz
                    items[href] = item_name
                    
        return items
        
    except Exception as e:
        print(f"Sayfa okuma hatası (Ders {course_id}): {e}")
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
        print("--> E-posta başarıyla gönderildi!")
    except Exception as e:
        print(f"Mail Hatası: {e}")

def main():
    # Eski durumu yükle
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
    else:
        state = {}

    changes_detected = False
    email_body = "Yulearn sisteminde yeni güncellemeler var!\n\n"

    for course_id in COURSE_IDS:
        print(f"Ders {course_id} taranıyor...")
        current_materials = get_course_materials(course_id)
        
        if current_materials is None:
            continue # Hata varsa veya bilet süresi dolduysa bu dersi atla
            
        old_materials = state.get(str(course_id), {})
        
        # Yeni eklenenleri bul (Eski listede olmayan linkler)
        new_links = set(current_materials.keys()) - set(old_materials.keys())
        
        if new_links and old_materials: # İlk çalışmada her şeyi yeni sanmasın diye kontrol
            changes_detected = True
            email_body += f"--- DERS ID: {course_id} ---\n"
            for link in new_links:
                item_name = current_materials[link]
                email_body += f"📌 YENİ EKLENDİ: {item_name}\n   Link: {link}\n\n"
                print(f"Yeni bulundu: {item_name}")
                
        # Durumu güncelle
        state[str(course_id)] = current_materials

    # Değişiklik varsa e-posta at ve dosyayı kaydet
    if changes_detected:
        send_email("Yulearn Yeni Materyal/Duyuru", email_body)
    else:
        print("BINGO! Güncel kod kesinlikle okunuyor!")
        send_email("Yulearn Kontrolü: Yeni Materyal Yok", "Yeni Materyal Yok...")
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
