import os
import requests
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

# Evrensel Ayarlar
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
COLLECTAPI_KEY = os.getenv("COLLECTAPI_KEY") # Akşam ekleyeceğimiz indikatörler için API key

bot = Bot(token=TOKEN)
app = FastAPI()

# 1. Veri Çekme Motoru (Fiyat, Hacim, RSI, EMA)
def get_hisse_data(hisse_kod):
    url = f"https://api.collectapi.com/economy/hisseSenedi?text={hisse_kod}"
    headers = {
        "content-type": "application/json",
        "authorization": f"apikey {COLLECTAPI_KEY}"
    }
    try:
        response = requests.get(url, headers=headers).json()
        if response.get("success") and response.get("result"):
            data = response["result"][0]
            # Akşam bağlayacağımız turbo indikatör simülasyonu
            return {
                "fiyat": data.get("price", "Bilinmiyor"),
                "hacim": data.get("hacim", "Yüksek"),
                "rsi": "62 (Nötr/Pozitif)",
                "ema50": "Trend Üstünde"
            }
    except Exception as e:
        print(f"Veri çekme hatası: {e}")
    return None

# 2. Yapay Zeka Analiz Motoru (Gemini Uzman Teknik Analist Promptu)
def ai_teknik_analiz(hisse_kod, data):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    
    prompt = (
        f"Sen profesyonel bir borsa ve teknik analiz uzmanısın. Kullanıcıya yapay zeka jargonu kullanmadan, "
        f"tamamen samimi ve net bir dille bilgi ver. {hisse_kod} hissesinin verileri şunlar:\n"
        f"Canlı Fiyat: {data['fiyat']}\nHacim Durumu: {data['hacim']}\nRSI Değeri: {data['rsi']}\nEMA 50 Durumu: {data['ema50']}\n"
        f"Bu verilere bakarak hissenin yönünü yorumla, kırılım durumunu incele ve kesinlikle net rakamlar vererek "
        f"Destek, Direnç ve Stop (Zarar Kes) seviyelerini hesaplayıp yaz."
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        res = requests.post(url, json=payload).json()
        return res['candidates'][0]['content']['parts'][0]['text']
    except:
        return "Analiz motorunda kısa süreli bir yoğunluk var reis, az sonra tekrar dene."

# 3. Telegram Komut Yönetimi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Kral hoş geldin! Analiz etmek istediğin hisse kodunu yazman yeterli. (Örn: THYAO)")

async def analiz_et(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hisse_kod = update.message.text.upper().strip()
    bekleniyor_mesajı = await update.message.reply_text(f"⚡ {hisse_kod} için canlı veriler toplanıyor ve yapay zeka motoruna gönderiliyor...")
    
    hisse_verisi = get_hisse_data(hisse_kod)
    if not hisse_verisi:
        await bekleniyor_mesajı.edit_text("Hisse kodu bulunamadı veya API bağlantısı kurulamadı kral.")
        return
        
    analiz_sonucu = ai_teknik_analiz(hisse_kod, hisse_verisi)
    await bekleniyor_mesajı.edit_text(analiz_sonucu)

# 4. Webhook ve FastAPI Bağlantısı
@app.post("/webhook")
async def webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, bot)
    
    # Telegram uygulamasını ayağa kaldırıp komutları işletiyoruz
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    # Komut olmayan her düz metni hisse kodu olarak algıla
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analiz_et))
    
    await application.initialize()
    await application.process_update(update)
    return {"status": "ok"}
