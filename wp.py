import os
import requests
from bs4 import BeautifulSoup
import re
from fpdf import FPDF
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from datetime import datetime
from flask import Flask, request

app = Flask(__name__)

chapterCount = 0

def clean_text(text):
    text = re.sub(r'<p.*?>', '\n', text)
    text = re.sub(r'\xa0', '', text)
    return text

def clean_filename(title):
    filename = title
    for i in ['\\', '/', ':', '*', '?', '"', '<', '>', '|', '^']:
        if i in filename:
            filename = filename.replace(i, '')
    filename = filename.lstrip('.')
    return filename
    
def get_page(text_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(text_url, headers=headers)
    if response.status_code != 200:
        return ""
    soup = BeautifulSoup(response.content, 'html.parser')
    for element in soup.select('div.panel.panel-reading p[data-image-layout], div.panel.panel-reading span'):
        element.decompose()
    content_elem = soup.select('div.panel.panel-reading p[data-p-id]')
    cleaned_content = [clean_text(str(para)) for para in content_elem]
    return ''.join(cleaned_content)

def download_image(image_url):
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        image_filename = image_url.split("/")[-1]
        with open(image_filename, 'wb') as f:
            f.write(response.content)
        return image_filename
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def extract_wattpad_story(story_url):
    global chapterCount
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(story_url, headers=headers)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        print(f"Error fetching story: {e}")
        return [], [], "", "", ""

    soup = BeautifulSoup(html_content, 'html.parser')
    cover_image = soup.select_one('div.story-cover img')
    image_url = cover_image['src'] if cover_image else ""
    author_info = soup.select_one('div.author-info__username a')
    author_name = author_info.get_text(strip=True) if author_info else "Unknown Author"
    
    story_title_elem = soup.select('div.story-info__title')
    story_title = story_title_elem[0].get_text(strip=True) if story_title_elem else "Judul Tidak Ditemukan"
    story_title = clean_filename(story_title)
    
    chapterlist = soup.select('.story-parts ul li a')
    chapters = []
    seen_titles = set()

    for item in chapterlist:
        title = item.select_one('div.part__label .part-title').get_text(strip=True)
        link = item['href']
        if title not in seen_titles:
            chapters.append((title, link))
            seen_titles.add(title)

    story_content = []
    for title, link in chapters:
        chapterCount += 1
        chapter_url = f"https://www.wattpad.com{link}"
        try:
            chapter_response = requests.get(chapter_url, headers=headers)
            chapter_response.raise_for_status()
            chapter_soup = BeautifulSoup(chapter_response.text, 'html.parser')
            pages_re = re.compile('"pages":([0-9]*),', re.IGNORECASE)
            pages = int(pages_re.search(chapter_response.text).group(1))
            chapter_content = []
            chapter_title = chapter_soup.select_one('h1.h2').get_text(strip=True)

            for i in range(1, pages + 1):
                page_url = f"{chapter_url}/page/{i}"
                page_content = get_page(page_url)
                page_content = re.sub(r'<h1 class="h2">.*?</h1>', '', page_content)
                chapter_content.append('<div class="page">\n')
                chapter_content.append(page_content)
                chapter_content.append('</div>\n')

            story_content.append((chapter_title, ''.join(chapter_content)))
        except Exception as e:
            print(f"Error processing chapter {title}: {e}")
            continue

    return chapters, story_content, image_url, author_name, story_title

def format_content(content):
    content = re.sub(r'[^\x20-\x7E]', '', content)
    sentences = re.split(r'(?<=[.!?]) +', content)
    return '\n'.join(sentences)

def create_pdf(chapters, story_content, image_url, author_name, story_title, pdf_filename):
    pdf = FPDF()
    pdf.set_margins(left=15, top=15, right=15)
    pdf.set_auto_page_break(auto=True, margin=15)
    downloaded_image = download_image(image_url)

    if downloaded_image:
        pdf.add_page()
        pdf.image(downloaded_image, x=0, y=0, w=pdf.w, h=pdf.h)
        pdf.ln(5)

    pdf.add_page()
    pdf.set_y(105)
    pdf.set_font("Arial", 'B', 24)
    pdf.cell(0, 10, story_title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=16)
    pdf.cell(0, 10, f"Penulis {author_name.encode('latin-1', 'replace').decode('latin-1')}", ln=True, align='C')
    pdf.cell(0, 10, f"Tahun Terbit: {datetime.now().year}", ln=True, align='C')  # Tahun terbit otomatis
    pdf.cell(0, 10, f"Tanggal Cetak: {datetime.now().strftime('%d %B %Y')}", ln=True, align='C')  # Tanggal cetak otomatis
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 10, "Daftar Bab", ln=True, align='C')
    pdf.set_font("Arial", size=16)
    for chapter in chapters:
        pdf.cell(0, 10, chapter[0].encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=16)
    pdf.cell(0, 10, "Dibuat oleh: Wattpad Bot", ln=True, align='C')

    for page_num, (title, content) in enumerate(story_content, start=1):
        pdf.add_page()
        pdf.set_font("Arial", 'B', 27)
        pdf.multi_cell(0, 10, title.encode('latin-1', 'replace').decode('latin-1'), align='C')
        pdf.ln(5)
        pdf.set_font("Arial", 'I', 15)
        pdf.cell(0, 10, f"Oleh {author_name.encode('latin-1', 'replace').decode('latin-1')}", ln=True, align='C')
        pdf.ln(10)

        cleaned_content = re.sub(r'<[^>]+>', '', content)
        formatted_content = format_content(cleaned_content)
        pdf.set_font("Arial", size=20)
        paragraphs = formatted_content.split('\n')

        for paragraph in paragraphs:
            if paragraph.strip():
                pdf.multi_cell(0, 10, paragraph.encode('latin-1', 'replace').decode('latin-1'), align='L')
                pdf.ln(5)
        pdf.set_y(-25)
        pdf.set_font("Arial", size=15)
        pdf.cell(0, 10, story_title.encode('latin-1', 'replace').decode('latin-1'), ln=False, align='L')
        pdf.set_x(pdf.w - 15)
        pdf.cell(0, 10, f"WATTPAD BOT | {page_num}", ln=True, align='R')

    pdf.output(pdf_filename)

    # Hapus file setelah pengiriman
    if os.path.exists(pdf_filename):
        os.remove(pdf_filename)

def start(update: Update, context: CallbackContext):
    update.message.reply_text('Kirimkan link cerita Wattpad yang ingin Anda konversi ke PDF.')

def handle_message(update: Update, context: CallbackContext):
    if update.message and update.message.text:
        url = update.message.text
        # Mengirim pesan proses konversi
        message = update.message.reply_text('Proses konversi sedang berlangsung, mohon tunggu...')
        chapters, story_content, image_url, author_name, story_title = extract_wattpad_story(url)

        if not chapters or not story_content:
            update.message.reply_text('Gagal mengambil cerita. Pastikan URL Wattpad valid.')
            return

        pdf_filename = f"{story_title} by {author_name}.pdf"
        create_pdf(chapters, story_content, image_url, author_name, story_title, pdf_filename)
        
        with open(pdf_filename, 'rb') as pdf:
            update.message.reply_document(pdf)
        
        # Hapus pesan proses konversi setelah pengiriman PDF
        context.bot.delete_message(chat_id=update.message.chat_id, message_id=message.message_id)
    else:
        print("Received update does not contain a message or text.")

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    print(update)  # Log the received update for debugging
    if "message" in update and "text" in update["message"]:
        handle_message(update)
    return '', 200

def main():
    # Inisialisasi bot Telegram
    updater = Updater("6308990102:AAFH_eAfo4imTAWnQ5CZeDUFNAC35rytnT0")
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Jalankan bot di thread terpisah
    updater.start_polling()

    # Jalankan Flask app
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

if __name__ == '__main__':
    main()
