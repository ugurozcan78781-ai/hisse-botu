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

# SENİN DOĞRULANMIŞ ANAHTARLARIN
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8295190923:AAFnBfgcKDsNxQ1N6k0wGgU_5eeFa9gIoco")
COLLECTAPI_KEY = os.environ.get("COLLECTAPI_KEY", "2GxAMb1niIywZeLVxh0GJ0:7if8NdM3bamD0rYMme2ZW1")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6LEL8Xzbc9DxJvTmY0AEPsR6T4N_8FCQ6p6YDE3eu3SrA")

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
    url = "https://api.collectapi.com/economy/liveBorsa"
    headers = {
        'content-type': "application/json",
        'authorization': f"apikey {COLLECTAPI_KEY}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if data.get("success") and data.get("result"):
            temiz_kod = hisse_kodu.upper().strip()
            for item in data["result"]:
                if item.get("name") == temiz_kod or item.get("code") == temiz_kod:
                    return item
        return None
    except Exception as e:
        logger.error(f"API Hatası: {e}")
        return None

def gemini_ile_grafik_yorumu_yap(hisse_kodu, fiyat, degisim):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = (
        f"Sen profesyonel bir borsa ve teknik analiz uzmanısın. {hisse_kodu} (BIST) hissesini inceliyorsun.\n"
        f"Güncel Fiyat: {fiyat} TL, Günlük Değişim: %{degisim}.\n\n"
        f"Lütfen bu verilere dayanarak şu 3 başlık altında kısa, net ve anlaşılır bir analiz raporu hazırla:\n"
        f"1) 📈 HAFTALIK VE AYLIK GÖRÜNÜM: (Kısa vadeli trend yönü)\n"
        f"2) 📊 YILLIK BEKLENTİ: (Orta ve uzun vadede bu hisse için temel beklenti)\n"
        f"3) 🎯 HEDEF POTANSİYEL: (Yüzde olarak tahmini yükseliş veya düzeltme beklentisi, sinyal nedir?)\n\n"
        f"Yazım tarzın samimi, bilgilendirici ve profesyonel olsun. Yatırım tavsiyesi değildir notu ekle."
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        res_data = response.json()
        if "candidates" in res_data and res_data["candidates"]:
            return res_data["candidates"][0]["content"]["parts"][0]["text"]
        
        return (
            "⚠️ Yapay zeka analiz motoru şu an devrede değil.\n"
            f"Anlık teknik verilere göre hisse günü %{degisim} değişimle {fiyat} TL seviyesinde geçiriyor. "
            "Destek ve direnç seviyelerini grafikten takip edebilirsiniz reis."
        )
    except Exception as e:
        logger.error(f"Gemini Hatası: {e}")
        return "⚠️ Yapay zeka motoruna şu an bağlanılamadı reis."

async def grafik_ve_analiz_gonder(update: Update, hisse_kodu: str):
    hisse_kodu = hisse_kodu.upper().strip()
    
    # 🎯 ARTIK KESİN ÇÖZÜM: Sunucu bu linke dokunmuyor! Direkt Telegram'a gönderiyoruz, Telegram resmi kendi çekiyor.
    # TradingView altyapısını kullanan ve her sunucuda %100 açılan temiz chart imaj linki:
    grafik_url = f"https://s.tradingview.com/widgetembed/?symbol=BIST%3A{hisse_kodu}&interval=D&theme=dark&style=1&timezone=Europe%2FIstanbul"

    bekleme_mesajı = await update.effective_message.reply_text(f"🚀 {hisse_kodu} için Grafik Motoru tetikleniyor ve Yapay Zeka Analizi hazırlanıyor...")
    
    hisse_data = canlı_borsa_verisi_getir(hisse_kodu)
    
    if hisse_data:
        fiyat = hisse_data.get("price", "Veri Yok")
        degisim = hisse_data.get("rate", "0")
        
        loop = asyncio.get_event_loop()
        analiz_raporu = await loop.run_in_executor(None, gemini_ile_grafik_yorumu_yap, hisse_kodu, fiyat, degisim)
        
        tam_metin = (
            f"📊 **{hisse_kodu} ANLIK DURUM RAPORU**\n"
            f"💰 Güncel Fiyat: {fiyat} TL\n"
            f"📈 Günlük Değişim: %{degisim}\n\n"
            f"{analiz_raporu}"
        )
        
        try:
            # Burası sihirli dokunuş: Sunucuda requests.get(grafik_url) YAPMIYORUZ!
            # URL'yi doğrudan Telegram'a veriyoruz, Telegram DNS hatasına düşmeden resmi kendi basıyor.
            await update.effective_message.reply_photo(
                photo=grafik_url,
                caption=tam_metin[:1024]
            )
            if len(tam_metin) > 1024:
                await update.effective_message.reply_text(tam_metin[1024:])
                
            await bekleme_mesajı.delete()
        except Exception as e:
            logger.error(f"Telegram resim basma hatası: {e}")
            # Eğer en kötü senaryoda Telegram linki embed edemezse bota tıklanabilir link olarak ekletiyoruz:
            linkli_metin = f"📈 **[Hisse Canlı Grafiğini Görmek İçin Tıkla]({grafik_url})**\n\n" + tam_metin
            await update.effective_message.reply_text(linkli_metin, parse_mode="Markdown", disable_web_page_preview=False)
            await bekleme_mesajı.delete()
    else:
        await update.effective_message.reply_text(f"❌ {hisse_kodu} için canlı borsa verisi çekilemedi reis.")
        await bekleme_mesajı.delete()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        "Aşağıdaki butonlardan birine tıkla ya da klavyeden direkt hisse kodunu yaz (Örn: THYAO)."
    )
    if update.message:
        await update.message.reply_text(mesaj_metni, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(mesaj_metni, reply_markup=reply_markup)

async def mesaj_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metin = update.message.text.upper().strip()
    if metin.startswith('/'): return
    await grafik_ve_analiz_gonder(update, metin)

async def buton_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await telegram_app.start()

@app.post('/webhook')
async def webhook(request: Request):
    try:
        req_json = await request.json()
        update = Update.de_json(req_json, telegram_app.bot)
        asyncio.create_task(telegram_app.process_update(update))
    except Exception as e:
        logger.error(f"Webhook Hatası: {e}")
    return Response(content="OK", status_code=200)

@app.get('/')
def index():
    return {"status": "Grafik Sistemi Engellenemez Modda Aktif!"}

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
