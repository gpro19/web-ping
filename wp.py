import random
import requests
import re
from flask import Flask, jsonify
import threading
import time
import cloudscraper  # Import cloudscraper

app = Flask(__name__)

# Variabel global untuk menyimpan konten penerbit terakhir
previous_issuer_content = 'Tidak ada'




def send_pesan(chat_id, text_message):


    payload = {
        'chat_id': str(chat_id),
        'parse_mode': 'HTML',
        'text': text_message,
        'message_thread_id': 26  # Jika Anda menggunakan thread, pastikan ini sesuai
    }

    # URL untuk mengirim pesan ke Telegram bot
    url = "https://api.telegram.org/bot7550906536:AAHCsudygDNhTUccm3JpmvqA21Br5WqM1dI/sendMessage"

    # Mengirim permintaan POST
    response = requests.post(url, json=payload)
    return response  # Mungkin perlu memeriksa respons


def generate_random_ip():
    return f"{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

def generate_random_user_agent():
    android_versions = ["4.0.3", "4.1.1", "4.2.2", "4.3", "4.4", "5.0.2", "5.1", "6.0", "7.0", "8.0", "9.0", "10.0", "11.0"]
    device_models = ["M2004J19C", "S2020X3", "Xiaomi4S", "RedmiNote9", "SamsungS21", "GooglePixel5"]
    build_versions = ["RP1A.200720.011", "RP1A.210505.003", "RP1A.210812.016", "QKQ1.200114.002", "RQ2A.210505.003"]

    selected_model = random.choice(device_models)
    selected_build = random.choice(build_versions)
    chrome_version = f"Chrome/{random.randint(1, 80)}.{random.randint(1, 999)}.{random.randint(1, 9999)}"

    return (f"Mozilla/5.0 (Linux; Android {random.choice(android_versions)}; {selected_model} "
            f"Build/{selected_build}) AppleWebKit/537.36 (KHTML, like Gecko) {chrome_version} "
            "Mobile Safari/537.36 WhatsApp/1.{random.randint(1, 9)}.{random.randint(1, 9)}")

def generate_random_referer():
    referers = [
        "https://www.google.com/",
        "https://www.bing.com/",
        "https://www.yahoo.com/",
        "https://www.mozilla.com/", 
        "https://www.wikipedia.org/",
        "https://firstledger.net/",
        "https://www.reddit.com/",
        "https://www.quora.com/",
        "https://www.facebook.com/",
        "https://www.twitter.com/",
        "https://www.instagram.com/",
        "https://www.linkedin.com/",
        "https://www.amazon.com/",
        "https://www.netflix.com/",
        "https://www.github.com/",
        "https://www.stackoverflow.com/",
        "https://www.medium.com/",
        "https://www.pinterest.com/",
        "https://www.tumblr.com/",
        "https://www.quora.com/"
    ]
    return random.choice(referers)

def extract_content(html, class_name):
    regex = re.compile(rf'<div class="{class_name}">\s*(.*?)\s*</div>', re.IGNORECASE)
    match = regex.search(html)
    return match.group(1).strip() if match else 'Tidak ada'

def extract_title_content(title_html):
    match = re.search(r'<div class="title">\$(.*?)</div>', title_html)
    return match.group(1).strip() if match else 'Tidak ada'

def send_notification(issuer_content, title_new):
    text_message = (f"<b>New Token Alert</b>\n"
                    f"<b>🔥 {title_new}</b>\n"
                    f"<code>{issuer_content}</code>\n"
                    f"<b><a href='https://t.me/firstledger_bot?start=FLDEEPLINK_{title_new}-{issuer_content}'>Buy with First Ledger</a></b>")
    
    send_text(-1002448557341, text_message)







def send_text(chatid, text):
    payload = {
        'chat_id': str(chatid),
        'parse_mode': 'HTML',
        'text': text,
        'message_thread_id': 26
    }
    
    url = f"https://api.telegram.org/bot7550906536:AAHCsudygDNhTUccm3JpmvqA21Br5WqM1dI/sendMessage"

    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Failed to send message: {response.text}")


def monitor_tokens():
    global previous_issuer_content
    url = 'https://firstledger.net/tokens'
    scraper = cloudscraper.create_scraper()  # Menggunakan cloudscraper

    while True:
        try:
            headers = {
                'User-Agent': generate_random_user_agent(),
                'Referer': generate_random_referer()  # Menggunakan referer acak
            }
            response = scraper.get(url, headers=headers)  # Menyertakan headers
            response.raise_for_status()  # Memicu exception jika terjadi kesalahan
            html = response.text

            issuer_content = extract_content(html, 'issuer')            
            title_content = extract_title_content(html)

            title_new = title_content.replace('$', '').replace('<!-- -->', '')

            if issuer_content != previous_issuer_content and issuer_content != 'Tidak ada':
                send_notification(issuer_content, title_new)
                previous_issuer_content = issuer_content
                print('🔥 Sukses Mengirim:', title_new)
        
        except requests.RequestException as error:
            print('Error fetching or processing data:', error)

        time.sleep(5)  # Tunggu 10 detik sebelum melakukan permintaan lagi

@app.route('/')
def index():
    return jsonify({"message": "Bot is running! by @MzCoder"})

if __name__ == "__main__":
    threading.Thread(target=monitor_tokens, daemon=True).start()
    app.run(host='0.0.0.0', port=8000)
