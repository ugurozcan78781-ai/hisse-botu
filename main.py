import os
import logging
import asyncio
from fastapi import FastAPI, Request, Response
import uvicorn
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Logging ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Sistem ortam değişkenlerinden güvenli bir şekilde çekiyoruz
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8295190923:AAFnBfgcKDsNxQ1N6k0wGgU_5eeFa9gIoco")
COLLECTAPI_KEY = os.environ.get("COLLECTAPI_KEY", "2GxAMb1niIywZeLVxh0GJ0:7if8NdM3bamD0rYMme2ZW1")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6JT3P7bNGWn6KknUFlOb4ihlZw0yMwce1ZjyxKyL9ORuQ")

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

app = FastAPI()
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

def canlı_borsa_verisi_getir(hisse_kodu):
    """Fiyat ve değişim oranını çeken kök fonksiyon"""
    url = "https://api.collectapi.com/economy/liveBorsa"
    headers = {
        'content-type': "application/json",
        'authorization': f"apikey {COLLECTAPI_KEY}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if data.get("success") and data.get("result"):
            for item in data["result"]:
                if item.get("name") == hisse_kodu or item.get("code") == hisse_kodu:
                    return item
        return None
    except Exception as e:
        logger.error(f"API Hatası: {e}")
        return None

def gemini_ile_grafik_yorumu_yap(hisse_kodu, fiyat, degisim):
    """Gelen teknik verilere göre yapay zekaya haftalık/aylık analiz raporu hazırlatan fonksiyon"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = (
        f"Sen profesyonel bir borsa ve teknik analiz uzmanısın. {hisse_kodu} (BIST) hissesini inceliyorsun.\n"
        f"Güncel Fiyat: {fiyat} TL, Günlük Değişim: %{degisim}.\n\n"
        f"Lütfen bu verilere dayanarak şu 3 başlık altında kısa, net ve anlaşılır bir analiz raporu hazırla:\n"
        f"1) 📈 HAFTALIK VE AYLIK GÖRÜNÜM: (Kısa vadeli trend yönü, indikatörlerin tahmini durumu)\n"
        f"2) 📊 YILLIK BEKLENTİ: (Orta ve uzun vadede bu hisse için temel beklenti ne yöndedir?)\n"
        f"3) 🎯 HEDEF POTANSİYEL: (Yüzde olarak tahmini ne kadar bir yükseliş veya düzeltme beklenebilir, sinyal nedir?)\n\n"
        f"Yazım tarzın gruptaki yatırımcılara hitap edecek şekilde samimi, bilgilendirici ve profesyonel olsun. Yatırım tavsiyesi değildir notu ekle."
    )
    
     payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        res_data = response.json()
        if "candidates" in res_data:
            return res_data["candidates"][0]["content"]["parts"][0]["text"]
        return "⚠️ Yapay zeka raporu şu an oluşturulamadı reis, teknik verileri kendin yorumlayabilirsin."
    except Exception as e:
        logger.error(f"Gemini Hatası: {e}")
        return "⚠️ Yapay zeka motoruna şu an bağlanılamadı."

async def grafik_ve_analiz_gonder(update: Update, hisse_kodu: str):
    """TradingView'dan grafiği indiren, Gemini'den yorumu alan ve gruba tek parça fırlatan ana motor"""
    # TradingView BIST grafik widget resim linki (BIST hisseleri için ön ek BIST: olarak verilir)
    # Bu link sunucuyu yormadan doğrudan anlık grafik imajını üretir reis.
    grafik_url = f"https://s.tradingview.com/widgetembed/?frameElementId=tradingview_chart&symbol=BIST%3A{hisse_kodu}&interval=D&symboledit=0&saveimage=1&toolbarbg=f1f3f6&studies=%5B%5D&theme=dark&style=1&timezone=Europe%2FIstanbul&studies_overrides=%7B%7D&overrides=%7B%7D&enabled_features=%5B%5D&disabled_features=%5B%5D&locale=tr"
    
    # Kullanıcıya süreçle ilgili ilk mesajı atıyoruz
    bekleme_mesajı = await update.effective_message.reply_text(f"🚀 {hisse_kodu} için Akıllı Grafik Motoru çalıştırılıyor ve Yapay Zeka Analizi hazırlanıyor. Lütfen bekleyin reis...")
    
    hisse_data = canlı_borsa_verisi_getir(hisse_kodu)
    
    if hisse_data:
        fiyat = hisse_data.get("price", "Veri Yok")
        degisim = hisse_data.get("rate", "0")
        
        # Arka planda Gemini uzman raporunu hazırlatıyoruz
        loop = asyncio.get_event_loop()
        analiz_raporu = await loop.run_in_executor(None, gemini_ile_grafik_yorumu_yap, hisse_kodu, fiyat, degisim)
        
        tam_metin = (
            f"📊 **{hisse_kodu} ANLIK DURUM RAPORU**\n"
            f"💰 Güncel Fiyat: {fiyat} TL\n"
            f"📈 Günlük Değişim: %{degisim}\n\n"
            f"{analiz_raporu}"
        )
        
        try:
            # Grafik üretici adresten anlık görüntüyü çekiyoruz
            img_response = requests.get(grafik_url, timeout=10)
            
            # Gruptakilere şovumuzu yapıyoruz: Önce grafik fotoğrafı, altında yapay zeka analizi!
            await update.effective_message.reply_photo(
                photo=img_response.content,
                caption=tam_metin[:1024] # Telegram yazı sınırı koruması
            )
            # Eğer metin çok uzunsa kalanı normal mesaj olarak devam eder
            if len(tam_metin) > 1024:
                await update.effective_message.reply_text(tam_metin[1024:])
                
            await bekleme_mesajı.delete()
        except Exception as e:
            logger.error(f"Grafik gönderme hatası: {e}")
            await update.effective_message.reply_text(f"⚠️ Grafiği çekerken bir hata oluştu ama veriler şöyle reis:\n\n{tam_metin}")
            await bekleme_mesajı.delete()
    else:
        await update.effective_message.reply_text(f"❌ {hisse_kodu} için canlı borsa verisi çekilemedi. Kodun doğruluğunu kontrol et reis.")
        await bekleme_mesajı.delete()

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
        "Kral Yapay Zeka Destekli Grafik Botuna Hoş Geldin! 🚀\n\n"
        "Aşağıdaki butonlardan birine tıkla ya da klavyeden direkt hisse kodunu yaz (Örn: THYAO).\n"
        "Bot anlık canlı grafiği bulacak ve haftalık/aylık yapay zeka analizini önüne serecek!"
    )
    if update.message:
        await update.message.reply_text(mesaj_metni, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(mesaj_metni, reply_markup=reply_markup)

async def mesaj_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Klavyeden elle THYAO vs yazıldığında tetiklenen yer"""
    metin = update.message.text.upper().strip()
    if metin.startswith('/'): return
    await grafik_of_analiz_gonder(update, metin)

async def buton_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menüdeki butonlara tıklandığında tetiklenen yer"""
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("analiz_"):
        hisse_kodu = data.split("_")[1]
        await grafik_ve_analiz_gonder(update, hisse_kodu)

@app.on_event("startup")
async def startup_event():
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CallbackQueryHandler(buton_handler))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_handler))
    await telegram_app.initialize()

@app.post('/webhook')
async def webhook(request: Request):
    try:
        req_json = await request.json()
        update = Update.de_json(req_json, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook Hatası: {e}")
    return Response(content="OK", status_code=200)

@app.get('/')
def index():
    return {"status": "Yapay Zeka Grafik Motoru Aktif!"}

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
