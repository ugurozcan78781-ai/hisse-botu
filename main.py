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

# DOĞRULANMIŞ ANAHTARLARIN
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
            # Kod eşleştirmesini daha esnek yapıyoruz (Örn: FRIGO veya FRIGO.IS)
            temiz_kod = hisse_kodu.replace(".IS", "")
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
        f"Sen profesyonel bir borsa ve teknik analiz uzmanısın. Borsa İstanbul'da işlem gören {hisse_kodu} hissesini inceliyorsun.\n"
        f"Hissenin Güncel Fiyatı: {fiyat} TL, Günlük Değişim Oranı: %{degisim}.\n\n"
        f"Lütfen bu verilere dayanarak şu 3 başlık altında kısa, net ve anlaşılır bir analiz raporu hazırla:\n"
        f"1) 📈 HAFTALIK VE AYLIK GÖRÜNÜM: (Kısa vadeli trend yönü ve indikatörlerin tahmini durumu)\n"
        f"2) 📊 YILLIK BEKLENTİ: (Orta ve uzun vadede bu hisse için temel beklenti ne yöndedir?)\n"
        f"3) 🎯 HEDEF POTANSİYEL: (Yüzde olarak tahmini ne kadar bir yükseliş veya düzeltme beklenebilir?)\n\n"
        f"Yazım tarzın gruptaki yatırımcılara hitap edecek şekilde samimi ve profesyonel olsun. Sonuna 'Yatırım tavsiyesi değildir.' notu ekle."
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        res_data = response.json()
        if "candidates" in res_data and res_data["candidates"]:
            return res_data["candidates"][0]["content"]["parts"][0]["text"]
        
        # Eğer API anahtarı hatası dönerse gruptakilere çaktırmadan teknik özet yapalım:
        return (
            "⚠️ Yapay zeka motoru şu an yoğun veya anahtar doğrulanmadı.\n"
            f"Anlık teknik verilere göre hisse günü %{degisim} değişimle {fiyat} TL seviyesinde geçiriyor. "
            "Destek ve direnç seviyelerini grafikten takip edebilirsiniz reis."
        )
    except Exception as e:
        logger.error(f"Gemini Hatası: {e}")
        return "⚠️ Yapay zeka raporuna şu an ulaşılamadı, teknik analizi grafikten yorumlayabilirsiniz reis."

async def grafik_ve_analiz_gonder(update: Update, hisse_kodu: str):
    hisse_kodu = hisse_kodu.upper().strip()
    
    # Yahoo Finance üzerinden %100 gerçek PNG resim döndüren grafik motoru linki:
    grafik_url = f"https://chart.finance.yahoo.com/z?s={hisse_kodu}.IS&t=6m&q=c&l=on&z=l&p=m50,m200"
    
    bekleme_mesajı = await update.effective_message.reply_text(f"🚀 {hisse_kodu} için grafik çekiliyor ve yapay zeka analizi hazırlanıyor...")
    
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
            # Grafiği indiriyoruz
            img_response = requests.get(grafik_url, timeout=10)
            
            if img_response.status_code == 200 and len(img_response.content) > 1000:
                await update.effective_message.reply_photo(
                    photo=img_response.content,
                    caption=tam_metin[:1024]
                )
                if len(tam_metin) > 1024:
                    await update.effective_message.reply_text(tam_metin[1024:])
            else:
                # Eğer Yahoo grafik bulamazsa sadece verileri ve raporu gönderir
                await update.effective_message.reply_text(f"📊 {hisse_kodu} Grafiği şu an yüklenemedi ama analiz verileri hazır reis:\n\n{tam_metin}")
                
            await bekleme_mesajı.delete()
        except Exception as e:
            logger.error(f"Grafik gönderme hatası: {e}")
            await update.effective_message.reply_text(f"⚠️ Teknik bir aksaklık oldu ama verileriniz hazır reis:\n\n{tam_metin}")
            await bekleme_mesajı.delete()
    else:
        await update.effective_message.reply_text(f"❌ {hisse_kodu} için canlı borsa verisi çekilemedi. Kodun BIST'te kayıtlı olduğundan emin ol reis.")
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
        "Aşağıdaki butonlardan birine tıkla ya da klavyeden direkt hisse kodunu yaz (Örn: THYAO).\n"
        "Bot anlık canlı grafiği bulacak ve haftalık/aylık yapay zeka analizini önüne serecek!"
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

@app.post('/webhook')
async def webhook(request: Request):
    try:
        req_json = await request.json()
        update = Update.de_json(req_json, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook Güncelleme Hatası: {e}")
    return Response(content="OK", status_code=200)

@app.get('/')
def index():
    return {"status": "Yapay Zeka Grafik Motoru Aktif!"}

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
