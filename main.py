import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests

# Flask ayarları
app = Flask(__name__)

# Logging ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Token ve API Tanımlamaları
TELEGRAM_TOKEN = "8295190923:AAFnBFgcKDsNxQ1N6k0wGgU_5eeFa9gloco"
COLLECTAPI_KEY = "2GxAMb1niIywZeLVxh0GJ0:7if8NdM3bamD0rYMme2ZW1" # Kendi CollectAPI anahtarını buraya çak reis

# Popüler BIST Hisseleri (Gruptakilerin en çok bakacağı canavarlar)
# Buraya istediğin BIST hissesini "KOD": "İsim" şeklinde ekleyip çıkarabilirsin kral
BIST_HISSELERI = {
    "THYAO": "Türk Hava Yolları",
    "EREGL": "Ereğli Demir Çelik",
    "SAHOL": "Sabancı Holding",
    "HEKTS": "Hektaş",
    "FRIGO": "Frigo Pak Montaj",
    "SKTAS": "Söktaş Tekstil",
    "ASELS": "Aselsan",
    "TUPRS": "Tüpraş",
    "KOZAL": "Koza Altın",
    "SASA": "Sasa Polyester"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutu geldiğinde Ana Menüyü ve Hisse Listesini gösterir"""
    klavye = []
    
    # Hisseleri ikişerli yan yana butonlar halinde dizelim, çok şık dursun
    hisse_kodlari = list(BIST_HISSELERI.keys())
    for i in range(0, len(hisse_kodlari), 2):
        satir_butonlari = []
        # İlk buton
        kod1 = hisse_kodlari[i]
        satir_butonlari.append(InlineKeyboardButton(f"📊 {kod1}", callback_data=f"analiz_{kod1}"))
        
        # Eğer bir sonraki eleman varsa yanına ikinci butonu ekle
        if i + 1 < len(hisse_kodlari):
            kod2 = hisse_kodlari[i + 1]
            satir_butonlari.append(InlineKeyboardButton(f"📊 {kod2}", callback_data=f"analiz_{kod2}"))
            
        klavye.append(satir_butonlari)
        
    reply_markup = InlineKeyboardMarkup(klavye)
    
    await update.message.reply_text(
        "Kral Borsa Analiz Botuna Hoş Geldin! 🚀\n\n"
        "Analizini görmek istediğin hisseye aşağıdaki butonlardan tıklayarak anında ulaşabilirsin:",
        reply_markup=reply_markup
    )

async def buton_tiklama_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı listedeki bir hisse butonuna bastığında çalışır"""
    query = update.callback_query
    await query.answer() # Butonun tıklama efektini tamamlar
    
    data = query.data
    
    if data.startswith("analiz_"):
        hisse_kodu = data.split("_")[1] # Butondan gelen hisse kodunu al (Örn: THYAO)
        
        # Ekran anlık olarak güncellensin
        await query.edit_message_text(text=f"🔄 {hisse_kodu} için canlı borsa verileri analiz ediliyor...")
        
        # Senin o meşhur, çalışan orijinal /liveBorsa fonksiyonunu çağırıyoruz
        analiz_sonucu = canlı_borsa_verisi_getir(hisse_kodu)
        
        # Kullanıcı analizden sonra listeden çıkmasın diye altına bir "Menüye Dön" butonu koyuyoruz
        geri_buton = [[InlineKeyboardButton("⬅️ Hisse Listesine Geri Dön", callback_data="listeye_don")]]
        
        await query.edit_message_text(text=analiz_sonucu, reply_markup=InlineKeyboardMarkup(geri_buton))
        
    elif data == "listeye_don":
        # Kullanıcı geri dönmek isterse ekranı tekrar ilk listeye çeviriyoruz
        klavye = []
        hisse_kodlari = list(BIST_HISSELERI.keys())
        for i in range(0, len(hisse_kodlari), 2):
            satir_butonlari = []
            kod1 = hisse_kodlari[i]
            satir_butonlari.append(InlineKeyboardButton(f"📊 {kod1}", callback_data=f"analiz_{kod1}"))
            if i + 1 < len(hisse_kodlari):
                kod2 = hisse_kodlari[i + 1]
                satir_butonlari.append(InlineKeyboardButton(f"📊 {kod2}", callback_data=f"analiz_{kod2}"))
            klavye.append(satir_butonlari)
            
        await query.edit_message_text(
            text="Analizini görmek istediğin hisseye aşağıdaki butonlardan tıklayarak anında ulaşabilirsin:",
            reply_markup=InlineKeyboardMarkup(klavye)
        )

def canlı_borsa_verisi_getir(hisse_kodu):
    """Senin o kesin çalışan orijinal /liveBorsa yapın reis"""
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
            # Listenin içinde dolanıp bizim tıkladığımız kodu arıyoruz
            for item in data["result"]:
                if item.get("name") == hisse_kodu or item.get("code") == hisse_kodu:
                    hisse_data = item
                    break
            
            if hisse_data:
                # Orijinal verileri çekiyoruz
                fiyat = hisse_data.get("price", "Veri Yok")
                degisim = hisse_data.get("rate", "0")
                
                # Sinyal algoritması
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
                return f"❌ {hisse_kodu} şu an aktif borsa listesinde bulunamadı reis."
        else:
            return "❌ Canlı borsa verisi alınamadı. CollectAPI paketini kontrol et reis."
            
    except Exception as e:
        logger.error(f"API Hatası: {e}")
        return "❌ Bağlantı hatası oluştu. Lütfen az sonra tekrar dene reis."

# Bot Kurulumu ve Handler Tanımlamaları
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(buton_tiklama_handler))

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        telegram_app.create_task(telegram_app.process_update(update))
    return "OK", 200

@app.route('/')
def index():
    return "BIST Akıllı Menü Botu Aktif!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
