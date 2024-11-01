import random
import requests
import re
import threading
import time
from datetime import datetime
import pytz
import cloudscraper
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, Updater, CallbackContext, CallbackQueryHandler
from flask import Flask, request

# Variabel Global
previous_issuer_content = 'Tidak ada'
scraping_enabled = True
chat_id = None
delay_time = 5  # Default delay time in seconds


# Inisialisasi Flask
app = Flask(__name__)

# Fungsi untuk menggenerate user-agent acak
def generate_random_user_agent():
    android_versions = ["4.0.3", "4.1.1", "4.2.2", "4.3", "4.4", "5.0.2", "5.1", "6.0", "7.0", "8.0", "9.0", "10.0", "11.0"]
    device_models = ["M2004J19C", "S2020X3", "Xiaomi4S", "RedmiNote9", "SamsungS21", "GooglePixel5"]
    build_versions = ["RP1A.200720.011", "RP1A.210505.003", "RP1A.210812.016", "QKQ1.200114.002", "RQ2A.210505.003"]

    selected_model = random.choice(device_models)
    selected_build = random.choice(build_versions)
    chrome_version = f"Chrome/{random.randint(1, 80)}.{random.randint(1, 999)}.{random.randint(1, 9999)}"

    return (f"Mozilla/5.0 (Linux; Android {random.choice(android_versions)}; {selected_model} "
            f"Build/{selected_build}) AppleWebKit/537.36 (KHTML, like Gecko) {chrome_version} "
            "Mobile Safari/537.36")

# Fungsi untuk menghasilkan referer acak
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

# Fungsi untuk mengekstrak konten
def extract_content(html, class_name):
    regex = re.compile(rf'<div class="{class_name}">\s*(.*?)\s*</div>', re.IGNORECASE)
    match = regex.search(html)
    return match.group(1).strip() if match else 'Tidak ada'

# Fungsi untuk mengirim notifikasi ke Telegram
def send_notification(bot: Bot, issuer_content, title_new):
    text_message = (f"<b>New Token Alert</b>\n"
                    f"<b>🔥 {title_new}</b>\n"
                    f"<code>{issuer_content}</code>\n"
                    f"<b><a href='https://t.me/firstledger_bot?start=FLDEEPLINK_{title_new}-{issuer_content}'>Buy with First Ledger</a></b>")
    
    bot.send_message(chat_id=chat_id, text=text_message, parse_mode='HTML')

# Fungsi untuk memantau token
def monitor_tokens(bot: Bot):
    global previous_issuer_content
    url = 'https://firstledger.net/tokens'
    scraper = cloudscraper.create_scraper()  

    while True:
        if not scraping_enabled:
            time.sleep(5)
            continue

        try:
            headers = {
                'User-Agent': generate_random_user_agent(),
                'Referer': generate_random_referer()  # Menambahkan Referer acak
            }
            response = scraper.get(url, headers=headers)
            response.raise_for_status()  
            html = response.text

            issuer_content = extract_content(html, 'issuer')            
            title_content = extract_content(html, 'title')

            if issuer_content != previous_issuer_content and issuer_content != 'Tidak ada':
                send_notification(bot, issuer_content, title_content)
                previous_issuer_content = issuer_content
                print('🔥 Sukses Mengirim:', title_content)
        
        except requests.RequestException as error:
            print('Error fetching or processing data:', error)

        time.sleep(delay_time)

# Fungsi untuk mengatur chat ID
def set_chat_id(update: Update, context: CallbackContext):
    global chat_id
    chat_id = update.message.chat_id
    update.message.reply_text(f"Chat ID telah diset: {chat_id}")

# Fungsi untuk mengatur delay
def set_delay(update: Update, context: CallbackContext):
    global delay_time
    if context.args:
        delay_time = int(context.args[0])
        update.message.reply_text(f"Delay time telah diset ke {delay_time} detik.")
    else:
        update.message.reply_text("Silakan masukkan waktu delay dalam detik.")

# Fungsi untuk membuat tombol untuk toggle scraping
def alerts(update: Update, context: CallbackContext):
    global scraping_enabled
    scraping_enabled = not scraping_enabled
    status = "diaktifkan" if scraping_enabled else "dinonaktifkan"
    
    keyboard = [
        [InlineKeyboardButton("Alerts On Off", callback_data='alerts')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(f"Scraping telah {status}.", reply_markup=reply_markup)

# Fungsi untuk menangani callback dari tombol
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    global scraping_enabled
    
    if query.data == 'alerts':
        scraping_enabled = not scraping_enabled
        status = "diaktifkan" if scraping_enabled else "dinonaktifkan"
        query.edit_message_text(text=f"Scraping telah {status}.")

# Fungsi untuk menampilkan bantuan
def help_command(update: Update, context: CallbackContext):
    help_text = (
        "Ini adalah bot untuk memantau token baru.\n\n"
        "Perintah yang tersedia:\n"
        "/set_chat_id - Atur chat ID untuk menerima notifikasi.\n"
        "/set_delay <detik> - Atur waktu delay antara scraping.\n"
        "/alerts - Hidupkan atau matikan fitur scraping dengan tombol.\n"
        "/help - Tampilkan pesan bantuan ini."
    )
    update.message.reply_text(help_text)

# Endpoint Flask untuk menerima permintaan
@app.route('/webhook', methods=['POST'])
def webhook():
    json_data = request.json
    # Logika untuk mengolah data dari permintaan dapat ditambahkan di sini
    return "Webhook received!", 200

# Fungsi utama untuk menjalankan bot
def main():
    global chat_id
    TOKEN = "7550906536:AAHCsudygDNhTUccm3JpmvqA21Br5WqM1dI"  # Ganti dengan token bot Anda
    updater = Updater(TOKEN, use_context=True)
    bot = updater.bot

    # Menambahkan handler command
    updater.dispatcher.add_handler(CommandHandler("set_chat_id", set_chat_id))
    updater.dispatcher.add_handler(CommandHandler("set_delay", set_delay))
    updater.dispatcher.add_handler(CommandHandler("alerts", alerts))
    updater.dispatcher.add_handler(CommandHandler("help", help_command))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    # Memulai monitoring token di thread terpisah
    threading.Thread(target=monitor_tokens, args=(bot,), daemon=True).start()

    # Menjalankan bot
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    # Menjalankan Flask di thread terpisah
    threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000}, daemon=True).start()
    main()
