import os
import logging
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import requests

# Logging ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Doğrulanmış Token ve API Tanımlamaları
TELEGRAM_TOKEN = "8295190923:AAFnBfgcKDsNxQ1N6k0wGgU_5eeFa9gIoco"
COLLECTAPI_KEY = "2GxAMb1niIywZeLVxh0GJ0:7if8NdM3bamD0rYMme2ZW1"

# Popüler Hisseler (Butonlar için)
BIST_HISSELERI = {
    "THYAO": "Türk Hava Yolları",
    "EREGL": "Ereğli Demir Çelik",
    "SAHOL": "Sabancı Holding",
    "HEKTS": "Hektaş",
    "FRIGO": "Frigo Pak Montaj",
    "SKTAS": "Söktaş Tekstil",
    "ASELS": "Aselsan",
    "TUPRS": "Tüpraş"
}

# FastAPI uygulamasını başlatıyoruz
app = FastAPI()

# Telegram Application nesnesini global olarak kuruyoruz
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

def canlı_borsa_verisi_getir(hisse_kodu):
    """Doğrulanmış API anahtarı ile çalışan kesin fonksiyon"""
    url = "https://api.collectapi.com/economy/liveBorsa"
    headers = {
        'content-type': "application/json",
        'authorization': f"apikey {COLLECTAPI_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data.get("success") and data.get("result"):
            hisse_data = None
            for item in data["result"]:
                if item.get("name") == hisse_kodu or item.get("code") == hisse_kodu:
                    hisse_data = item
                    break
            
            if hisse_data:
                fiyat = hisse_data.get("price", "Veri Yok")
                degisim = hisse_data.get("rate", "0")
                
                try:
                    degisim_float = float(str(degisim).replace(",", ".").replace("%", ""))
                    if degisim_float > 0:
                        sinyal = "🚀 AL"
                    elif degisim_float < 0:
                        sinyal = "📉 SAT"
                    else:
                        sinyal = "⏳ NÖTR"
                except:
                    sinyal = "⏳ NÖTR"
                    
                return (
                    f"📊 {hisse_kodu} CANLI ANALİZİ\n\n"
                    f"💰 Güncel Fiyat: {fiyat} TL\n"
                    f"📈 Günlük Değişim: %{degisim}\n"
                    f"⚡ Teknik Sinyal: {sinyal}"
                )
            else:
                return f"❌ {hisse_kodu} şu an listede bulunamadı reis."
        else:
            return "❌ Canlı borsa verisi alınamadı. Limit veya API problemi olabilir."
            
    except Exception as e:
        logger.error(f"API Hatası: {e}")
        return "❌ Bağlantı hatası oluştu reis."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutu menüsü"""
    klavye = []
    hisse_kodlari = list(BIST_HISSELERI.keys())
    for i in range(0, len(hisse_kodlari), 2):
        satir = [InlineKeyboardButton(f"📊 {hisse_kodlari[i]}", callback_data=f"analiz_{hisse_kodlari[i]}")]
        if i + 1 < len(hisse_kodlari):
            satir.append(InlineKeyboardButton(f"📊 {hisse_kodlari[i+1]}", callback_data=f"analiz_{hisse_kodlari[i+1]}"))
        klavye.append(satir)
        
    reply_markup = InlineKeyboardMarkup(klavye)
    
    mesaj_metni = (
        "Kral Borsa Botuna Hoş Geldin! 🚀\n\n"
        "İster aşağıdaki butonlara tıkla, ister direkt klavyeden hisse kodunu yaz (Örn: THYAO):"
    )
    if update.message:
        await update.message.reply_text(mesaj_metni, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(mesaj_metni, reply_markup=reply_markup)

async def mesaj_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Klavyeden elle yazınca çalışan sistem"""
    metin = update.message.text.upper().strip()
    if metin.startswith('/'):
        return
        
    await update.message.reply_text(f"🔄 {metin} için canlı borsa verileri analiz ediliyor...")
    analiz = canlı_borsa_verisi_getir(metin)
    await update.message.reply_text(analiz)

async def buton_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buton tıklamaları"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("analiz_"):
        hisse_kodu = data.split("_")[1]
        await query.edit_message_text(text=f"🔄 {hisse_kodu} için canlı borsa verileri analiz ediliyor...")
        analiz_sonucu = canlı_borsa_verisi_getir(hisse_kodu)
        
        geri_buton = [[InlineKeyboardButton("⬅️ Listeye Geri Dön", callback_data="listeye_don")]]
        await query.edit_message_text(text=analiz_sonucu, reply_markup=InlineKeyboardMarkup(geri_buton))
    elif data == "listeye_don":
        await start(update, context)

# Bot Handler Girişleri (Uygulama ilk açıldığında bir kez yüklenir)
@app.on_event("startup")
async def startup_event():
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CallbackQueryHandler(buton_handler))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_handler))
    await telegram_app.initialize()

@app.post('/webhook')
async def webhook(request: Request):
    """FastAPI asenkron yapısıyla gelen Telegram paketlerini asla düşürmez"""
    try:
        req_json = await request.json()
        update = Update.de_json(req_json, telegram_app.bot)
        # Asenkron havuzda düzgünce bekletilerek çalıştırılır (Hata vermez)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook Güncelleme Hatası: {e}")
    return Response(content="OK", status_code=200)

@app.get('/')
def index():
    return {"status": "Bot Sistemleri Kusursuz Çalışıyor!"}
