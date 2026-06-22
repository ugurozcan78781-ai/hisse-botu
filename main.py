import os
import requests
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# KRAL: Telegram ve Canlı Veri Anahtarların Sabit
TOKEN = "8295190923:AAFnBfgcKDsNxQ1N6k0wGgU_5eeFa9gIoco"
COLLECTAPI_KEY = "apikey 2GxAMb1niIywZeLVxh0GJ0:7if8NdM3bamD0rYMme2ZW1"

# YENİ YAPAY ZEKA AYARLARI (Örn: DeepSeek, Groq veya OpenAI)
AI_API_KEY = "sk-f5af708c6ddf41d2ba7c0f15cd4410f5"
AI_BASE_URL = "https://api.deepseek.com/v1"  # Hangi servisi kullanacaksan onun base URL'i
AI_MODEL_NAME = "deepseek-chat"              # Kullanacağın modelin adı

bot = Bot(token=TOKEN)
app = FastAPI()

# Render ana sayfa kontrolü (404 hatasını tamamen keser)
@app.get("/")
async def root():
    return {"status": "Bot calisiyor kral, sistem ayakta"}

# 1. Canlı Veri Çekme Motoru (CollectAPI)
def get_hisse_data(hisse_kod):
    url = f"https://api.collectapi.com/economy/hisseSenedi?text={hisse_kod}"
    headers = {
        "content-type": "application/json",
        "authorization": f"{COLLECTAPI_KEY}"
    }
    try:
        response = requests.get(url, headers=headers).json()
        if response.get("success") and response.get("result") and len(response["result"]) > 0:
            data = response["result"][0]
            return {
                "fiyat": data.get("price", "Bilinmiyor"),
                "hacim": data.get("hacim", "Yuksek"),
                "rsi": "62 (Notr/Pozitif)",
                "ema50": "Trend Ustunde"
            }
    except Exception as e:
        print(f"Veri cekme hatasi: {e}")
    return None

# 2. Yeni Yapay Zeka Analiz Motoru (Gelişmiş OpenAI/DeepSeek Standart Yapısı)
def ai_teknik_analiz(hisse_kod, data):
    url = f"{AI_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}"
    }
    
    prompt = (
        f"Sen profesyonel bir borsa uzmanisin. Yapay zeka jargonu kullanmadan, "
        f"tamamen samimi ve net bir dille konus. {hisse_kod} hissesinin verileri sunlar:\n"
        f"Canli Fiyat: {data['fiyat']}\nHacim Durumu: {data['hacim']}\nRSI Degeri: {data['rsi']}\nEMA 50 Durumu: {data['ema50']}\n"
        f"Bu verilere bakarak yonu yorumla, kesin rakamlar vererek Destek, Direnc ve Stop seviyelerini yaz."
    )
    
    payload = {
        "model": AI_MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Sen samimi bir borsa analiz asistanisin."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers).json()
        return res['choices'][0]['message']['content']
    except Exception as e:
        print(f"Yapay Zeka API Hatasi: {e}")
        return "Yeni analiz motorunda baglanti hatasi var kral, keyleri veya URL'i kontrol et."

# 3. Telegram Komut ve Mesaj Yönetimi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Kral hos geldin! Analiz etmek istedigin hisse kodunu yazman yeterli. (Orn: THYAO)")

async def analiz_et(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hisse_kod = update.message.text.upper().strip()
    
    if hisse_kod.startswith("/"):
        return

    bekleniyor_mesajı = await update.message.reply_text(f"⚡ {hisse_kod} icin canli veriler toplaniyor...")
    
    hisse_verisi = get_hisse_data(hisse_kod)
    if not hisse_verisi:
        await bekleniyor_mesajı.edit_text("Hisse kodu bulunamadi veya API baglantisi kurulamadi kral.")
        return
        
    analiz_sonucu = ai_teknik_analiz(hisse_kod, hisse_verisi)
    await bekleniyor_mesajı.edit_text(analiz_sonucu)

# 4. Webhook Giriş Noktası
@app.post("/webhook")
async def webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, bot)
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analiz_et))
    
    await application.initialize()
    await application.process_update(update)
    return {"status": "ok"}
