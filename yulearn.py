import requests
from bs4 import BeautifulSoup
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- GENEL AYARLAR (SENDER AYNI KALABİLİR) ---
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
STATE_FILE = "yulearn_scraping_state.json"

# --- KULLANICI YAPILANDIRMASI ---
USERS = [
    {
        "name": "Zeynep",
        "cookie": os.environ.get("MOODLE_COOKIE"), # Senin biletin
        "receiver": os.environ.get("EMAIL_RECEIVER"), # Senin mailin
        "courses": [46059,47716,46062,46064,47717,46078,47719,45212] # Senin ders ID'lerin
    },
    {
        "name": "Onur",
        "cookie": os.environ.get("ONUR_COOKIE"), # Onur'un bileti
        "receiver": os.environ.get("ONUR_EMAIL"), # Onur'un maili
        "courses": [47011, 47028,48538,47033,47186,47697] # Onur'un ders ID'leri (örnektir, düzeltmeyi unutma)
    }
]

def send_email(subject, body, to_email):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"--> E-posta gönderildi: {to_email}")
    except Exception as e:
        print(f"Mail Hatası ({to_email}): {e}")

def get_course_materials(course_id, user_cookie):
    url = f"https://yulearn.yeditepe.edu.tr/course/view.php?id={course_id}"
    cookies = {"MoodleSession": user_cookie}
    try:
        response = requests.get(url, cookies=cookies, allow_redirects=True)
        if "login" in response.url:
            return "EXPIRED"
        
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
                # Duyuru sayfasını da indiriyoruz
                forum_res = requests.get(href, cookies=cookies)
                forum_soup = BeautifulSoup(forum_res.text, 'html.parser')
                # Duyuru başlıklarının linklerini bul (genelde discuss.php ile başlar)
                for discussion in forum_soup.find_all('a', href=True):
                    if 'discuss.php?d=' in discussion['href']:
                        # Başına '📣' koyalım ki mailde duyuru olduğu belli olsun
                        disc_title = "📣 DUYURU: " + discussion.get_text(strip=True)
                        items[discussion['href']] = disc_title

        return items
    except Exception as e:
        print(f"Hata (Ders {course_id}): {e}")
        return None

def main():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
    else:
        state = {}

    for user in USERS:
        print(f"\n--- {user['name']} için tarama başlıyor ---")
        user_changes = False
        user_email_body = f"Merhaba {user['name']},\n\nYulearn sisteminde senin için güncellemeler var!\n\n"

        for course_id in user['courses']:
            print(f"Ders {course_id} kontrol ediliyor...")
            materials = get_course_materials(course_id, user['cookie'])

            if materials == "EXPIRED":
                send_email("🚨 Yulearn Alarm: Biletin Süresi Doldu!", 
                           f"Biletin (Cookie) süresi dolmuş. Lütfen yenile!", user['receiver'])
                continue
            
            if materials is None: continue

            old_materials = state.get(str(course_id), {})
            new_links = set(materials.keys()) - set(old_materials.keys())

            if new_links and old_materials:
                user_changes = True
                user_email_body += f"--- DERS ID: {course_id} ---\n"
                for link in new_links:
                    user_email_body += f"📌 YENİ: {materials[link]}\nLink: {link}\n\n"
            
            state[str(course_id)] = materials

        if user_changes:
            send_email("Yulearn Yeni Materyal Duyurusu", user_email_body, user['receiver'])
        else:
            send_email("Yulearn Yeni Materyal Duyurusu", "yeni materyal yok" ,user['receiver'])
            print(f"{user['name']} için yeni bir şey yok.")

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
