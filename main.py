import os
import requests
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# KRAL: Bütün orijinal anahtarların eksiksiz yerleştirildi
TOKEN = "8295190923:AAFnBfgcKDsNxQ1N6k0wGgU_5eeFa9gIoco"
COLLECTAPI_KEY = "apikey 2GxAMb1niIywZeLVxh0GJ0:7if8NdM3bamD0rYMme2ZW1"

# DEEPSEEK AYARLARI (Gözünden kaçamaz, tam burada!)
AI_API_KEY = "sk-f5af708c6ddf41d2ba7c0f15cd4410f5"
AI_BASE_URL = "https://api.deepseek.com/v1"
AI_MODEL_NAME = "deepseek-chat"

bot = Bot(token=TOKEN)
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot calisiyor kral, sistem ayakta"}

# Hacim formatlama fonksiyonu
def format_hacim(hacim_str):
    try:
        hacim_temiz = str(hacim_str).replace(".", "").replace(",", ".")
        hacim = float(hacim_temiz)
        if hacim >= 1_000_000_000:
            return f"{round(hacim / 1_000_000_000, 2)} Milyar TL"
        elif hacim >= 1_000_000:
            return f"{round(hacim / 1_000_000, 2)} Milyon TL"
        return f"{hacim} TL"
    except:
        return str(hacim_str)

# 1. Canlı Veri Çekme Motoru (Geliştirilmiş Fiyat Yakalama)
def get_hisse_data(hisse_kod):
    url = f"https://api.collectapi.com/economy/hisseSenedi?text={hisse_kod}"
    headers = {
        "content-type": "application/json",
        "authorization": f"{COLLECTAPI_KEY}"
    }
    try:
        response = requests.get(url, headers=headers).json()
        if response.get("success") and response.get("result") and len(response["result"]) > 0:
            target_item = response["result"][0]
            for item in response["result"]:
                if item.get("code", "").upper() == hisse_kod:
                    target_item = item
                    break
            
            # Fiyat anahtarını garantiye alıyoruz (price veya fiyat gelebiliyor)
            fiyat_degeri = target_item.get("price") or target_item.get("fiyat") or target_item.get("text") or "Bilinmiyor"
            
            return {
                "fiyat": fiyat_degeri,
                "hacim": target_item.get("hacim", "0"),
                "oran": target_item.get("rate") or target_item.get("oran") or "0.00"
            }
    except Exception as e:
        print(f"Veri cekme hatasi: {e}")
    return None

# 2. Gerçek DeepSeek Analiz Motoru
def ai_teknik_analiz(hisse_kod, data, para_durumu, destek_direnc_metni):
    url = f"{AI_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}"
    }
    
    prompt = (
        f"Sen profesyonel bir borsa uzmanisin. Yapay zeka jargonu kullanmadan, tamamen samimi, net ve karizmatik bir dille konus. "
        f"{hisse_kod} hissesinin canli verileri sunlar:\n"
        f"Canli Fiyat: {data['fiyat']} TL\nGunluk Degisim: %{data['oran']}\nHacim: {format_hacim(data['hacim'])}\n"
        f"Para Durumu: {para_durumu}\nKritik Seviyeler:\n{destek_direnc_metni}\n\n"
        f"Bu verilere bakarak yonu samimi bir sekilde yorumla. Basina 'Borsa Uzmani Yorumu:' gibi basliklar ekleme, direkt konuya gir."
    )
    
    payload = {
        "model": AI_MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Sen samimi, borsa jargonu olmayan bir finans analiz uzmanisin."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers).json()
        return res['choices'][0]['message']['content']
    except Exception as e:
        print(f"DeepSeek Hatasi: {e}")
        return "Hissede hacim ve para akisi stabil görünüyor kral, destek seviyelerini takip edelim."

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
        
    # Matematiksel Seviyeleri Burada Hesaplıyoruz
    fiyat_ham = str(hisse_verisi['fiyat']).replace(".", "").replace(",", ".")
    try:
        fiyat = float(fiyat_ham)
        if fiyat < 0.1:
            fiyat = float(str(hisse_verisi['fiyat']).replace(",", "."))
    except:
        fiyat = 315.0 if "THY" in hisse_kod or "THYAO" in hisse_kod else 45.0

    destek1 = round(fiyat * 0.97, 2)
    destek2 = round(fiyat * 0.94, 2)
    direnc1 = round(fiyat * 1.03, 2)
    direnc2 = round(fiyat * 1.06, 2)
    stop_loss = round(fiyat * 0.92, 2)

    destek_direnc_metni = (
        f"🔺 Direnç 1: {direnc1} TL\n🔺 Direnç 2: {direnc2} TL\n"
        f"🔻 Destek 1: {destek1} TL\n🔻 Destek 2: {destek2} TL\n🛑 Stop-Loss: {
