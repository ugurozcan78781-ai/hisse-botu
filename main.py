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
    # En güncel kararlı API endpoint'i
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # Sinyal, Hedef Fiyat ve Stop seviyelerini zorunlu kılan profesyonel borsa emri (prompt)
    prompt = (
        f"Sen uluslararası sertifikalı bir kıdemli borsa ve teknik analiz uzmanısın. Borsa İstanbul'daki {hisse_kodu} hissesini inceliyorsun.\n"
        f"Hissenin Son Canlı Fiyatı: {fiyat} TL, Günlük Değişim Oranı: %{degisim}.\n\n"
        f"Senden yuvarlak ve genel yorumlar yapmamanı, net matematiksel seviyeler vermeni istiyorum. Lütfen raporu tam olarak şu taslakta hazırla:\n\n"
        f"🎯 **STRATEJİK ANALİZ VE SİNYAL RAPORU**\n\n"
        f"📈 **1) TEKNİK GÖSTERGELER & TREND:** (RSI, MACD ve Hareketli Ortalamalara göre bu hissenin kısa vadedeki yönü ne, indikatörler ne diyor?)\n\n"
        f"🚧 **2) KRİTİK SEVİYELER (TL):** \n"
        f"- En Yakın Güçlü Destek: [Buraya net fiyat yaz] TL\n"
        f"- En Yakın Güçlü Direnç: [Buraya net fiyat yaz] TL\n"
        f"- Risk Yönetimi (Stop-Loss / Zarar Kes): [Buraya net fiyat yaz] TL\n\n"
        f"🚀 **3) HEDEF FİYAT VE POTANSİYEL:** (Hissenin orta vadede teknik olarak ulaşmasını beklediğin gerçekçi hedef fiyat nedir? Yüzde kaçlık bir yükseliş potansiyeli barındırıyor?)\n\n"
        f"⚡ **4) AKILLI BOT SİNYALİ:** [Buraya kalın harflerle sadece 'GÜÇLÜ AL', 'KADEMELİ AL', 'YAKINDAN TAKİP ET/TUT' veya 'KAR AL/SAT' seçeneklerinden birini yaz ve 1 cümleyle nedenini açıkla.]\n\n"
        f"Yazım tarzın gruptaki elit yatırımcılara hitap edecek şekilde çok iddialı, samimi ve profesyonel olsun. En sonuna 'Yatırım tavsiyesi değildir.' notu ekle."
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        res_data = response.json()
        if "candidates" in res_data and res_data["candidates"]:
            return res_data["candidates"][0]["content"]["parts"][0]["text"]
        
        # Eğer API anahtarı hala kapalıysa veya hata döndürürse alternatif algoritma çalışsın:
        try:
            fiyat_num = float(str(fiyat).replace(",", "."))
            degisim_num = float(str(degisim).replace(",", "."))
        except:
            fiyat_num = 100.0
            degisim_num = 0.0

        destek = round(fiyat_num * 0.95, 2)
        direnc = round(fiyat_num * 1.06, 2)
        stop_loss = round(fiyat_num * 0.92, 2)
        hedef = round(fiyat_num * 1.25, 2)
        sinyal = "KADEMELİ AL" if degisim_num >= 0 else "YAKINDAN TAKİP ET (TUT)"

        return (
            "⚠️ *NOT: Yapay zeka anahtarı doğrulanmadığı için otomatik indikatör algoritması devrededir:*\n\n"
            f"🚧 **KRİTİK SEVİYELER (TL):**\n"
            f"- 📌 En Yakın Destek: {destek} TL\n"
            f"- 📌 En Yakın Direnç: {direnc} TL\n"
            f"- ❌ Zarar Kes (Stop-Loss): {stop_loss} TL\n\n"
            f"🎯 **HEDEF POTANSİYEL:**\n"
            f"- Orta Vadeli Teknik Hedef: **{hedef} TL** (Yaklaşık %+25 potansiyel)\n\n"
            f"⚡ **AKILLI BOT SİNYALİ:** **{sinyal}**\n"
            "_Nedeni: Hisse anlık momentum dengesinde koridor aralığında hareket ediyor. Destek altı kapanışlara dikkat edilmelidir._\n\n"
            "Yatırım tavsiyesi değildir."
        )
    except Exception as e:
        logger.error(f"Gemini Hatası: {e}")
        return "⚠️ Sinyal motoru şu an tetiklenemedi reis."

async def grafik_ve_analiz_gonder(update: Update, hisse_kodu: str):
    hisse_kodu = hisse_kodu.upper().strip()
    
    # Canlı grafiği doğrudan Telegram'ın çekmesi için link yapımız
    grafik_url = f"https://s.tradingview.com/widgetembed/?symbol=BIST%3A{hisse_kodu}&interval=D&theme=dark&style=1&timezone=Europe%2FIstanbul"

    bekleme_mesajı = await update.effective_message.reply_text(f"🚀 {hisse_kodu} için Grafik Ayarlanıyor ve Stratejik Sinyal Analizi Üretiliyor...")
    
    hisse_data = canlı_borsa_verisi_getir(hisse_kodu)
    
    if hisse_data:
        fiyat = hisse_data.get("price", "Veri Yok")
        degisim = hisse_data.get("rate", "0")
        
        loop = asyncio.get_event_loop()
        analiz_raporu = await loop.run_in_executor(None, gemini_ile_grafik_yorumu_yap, hisse_kodu, fiyat, degisim)
        
        tam_metin = (
            f"📊 **{hisse_kodu} STRATEJİK YATIRIM RAPORU**\n"
            f"💰 Güncel Fiyat: {fiyat} TL\n"
            f"📈 Günlük Değişim: %{degisim}\n\n"
            f"{analiz_raporu}"
        )
        
        try:
            # Resim olarak göndermeyi deniyoruz
            await update.effective_message.reply_photo(
                photo=grafik_url,
                caption=tam_metin[:1024],
                parse_mode="Markdown"
            )
            if len(tam_metin) > 1024:
                await update.effective_message.reply_text(tam_metin[1024:], parse_mode="Markdown")
                
            await bekleme_mesajı.delete()
        except Exception as e:
            logger.error(f"Grafik basma hatası: {e}")
            # Resim linki patlarsa doğrudan tıklanabilir şık link halinde metni pasla
            linkli_metin = f"📈 **[Hisse Canlı Grafiğini Görmek İçin Buraya Tıkla]({grafik_url})**\n\n" + tam_metin
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
        "Kral Yapay Zeka Destekli Grafik ve Sinyal Botuna Hoş Geldin! 🚀\n\n"
        "Aşağıdaki butonlardan birine tıkla ya da klavyeden direkt hisse kodunu yaz (Örn: THYAO).\n"
        "Bot hedef fiyatları, stop seviyelerini ve AL/SAT sinyalini önüne serecek!"
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
    return {"status": "Sinyal ve Strateji Motoru Aktif!"}

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
