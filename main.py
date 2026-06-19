import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import requests

# Flask ayarları
app = Flask(__name__)

# Logging ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Token ve API Tanımlamaları
TELEGRAM_TOKEN = "8295190923:AAFnBfgcKDsNxQ1N6k0wGgU_5eeFa9gIoco"
COLLECTAPI_KEY = "2GxAMb1niIywZeLVxh0GJ0:7if8NdM3bamD0rYMme2ZW1" # Kendi CollectAPI anahtarını buraya koy reis

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

def canlı_borsa_verisi_getir(hisse_kodu):
    """Orijinal /liveBorsa endpoint'inden veri çeken fonksiyon"""
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
            return "❌ Canlı borsa verisi alınamadı. CollectAPI limitini kontrol et reis."
            
    except Exception as e:
        logger.error(f"API Hatası: {e}")
        return "❌ Bağlantı hatası oluştu reis."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutu geldiğinde çalışan ana menü"""
    klavye = []
    hisse_kodlari = list(BIST_HISSELERI.keys())
    for i in range(0, len(hisse_kodlari), 2):
        satir = [InlineKeyboardButton(f"📊 {hisse_kodlari[i]}", callback_data=f"analiz_{hisse_kodlari[i]}")]
        if i + 1 < len(hisse_kodlari):
            satir.append(InlineKeyboardButton(f"📊 {hisse_kodlari[i+1]}", callback_data=f"analiz_{hisse_kodlari[i+1]}"))
        klavye.append(satir)
        
    reply_markup = InlineKeyboardMarkup(klavye)
    
    # Güvenlik önlemi: Hem normal mesaj hem buton tıklaması için uyumlu yanıt
    mesaj_metni = (
        "Kral Borsa Botuna Hoş Geldin! 🚀\n\n"
        "İster aşağıdaki butonlara tıkla, ister direkt klavyeden hisse kodunu yaz (Örn: THYAO):"
    )
    if update.message:
        await update.message.reply_text(mesaj_metni, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(mesaj_metni, reply_markup=reply_markup)

async def mesaj_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı klavyeden elle THYAO vs. yazdığında devreye giren eski usul sistem"""
    metin = update.message.text.upper().strip()
    
    # Eğer kullanıcı yanlışlıkla komut yazdıysa işlem yapma
    if metin.startswith('/'):
        return
        
    await update.message.reply_text(f"🔄 {metin} için canlı borsa verileri analiz ediliyor...")
    analiz = canlı_borsa_verisi_getir(metin)
    await update.message.reply_text(analiz)

async def buton_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Butonlara tıklandığında devreye giren sistem"""
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

# Bot Kurulumu
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

# Handler'ları Sırasıyla Ekleme (Burası kritik)
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(buton_handler))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_handler))

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram'dan gelen her isteği alan ana havuz"""
    if request.method == "POST":
        try:
            # Gelen veriyi işle ve task sırasına koy
            update = Update.de_json(request.get_json(force=True), telegram_app.bot)
            telegram_app.create_task(telegram_app.process_update(update))
        except Exception as e:
            logger.error(f"Webhook Güncelleme Hatası: {e}")
    return "OK", 200

@app.route('/')
def index():
    return "Bot Sistemleri Kusursuz Çalışıyor!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
