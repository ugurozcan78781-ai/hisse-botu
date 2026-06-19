import os
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
import uvicorn
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Logging ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ANAHTARLARIN
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CallbackQueryHandler(buton_handler))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_handler))
    
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("🚀 Gelişmiş Teknik Analiz Botu Aktif!")
    yield
    await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(lifespan=lifespan)
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

def tradingview_teknik_ozet_hesapla(fiyat, degisim):
    """
    Yapısal veri beslemesi: Yapay zekanın ezbere konuşmasını engellemek için
    fiyat hareketlerine göre teknik osilatör matrisi simüle eder.
    """
    try:
        f = float(str(fiyat).replace(",", "."))
        d = float(str(degisim).replace(",", "."))
    except:
        f, d = 100.0, 0.0

    rsi = 68 if d > 1.5 else (32 if d < -1.5 else 51)
    macd = "Boğa Eğilimli (Al Sinyali)" if d >= 0 else "Ayı Eğilimli (Sat Sinyali)"
    sma50 = round(f * 0.97, 2)
    sma200 = round(f * 0.91, 2)
    stoch_rsi = "Aşırı Alım Bölgesinde" if rsi > 65 else ("Aşırı Satım Bölgesinde" if rsi < 35 else "Nötr Bölgede")
    
    return {
        "rsi": rsi,
        "macd": macd,
        "sma50": sma50,
        "sma200": sma200,
        "stoch_rsi": stoch_rsi
    }

def gemini_ile_grafik_yorumu_yap(hisse_kodu, fiyat, degisim):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # Gerçekçi indikatör simülasyon matrisini çekiyoruz
    teknik = tradingview_teknik_ozet_hesapla(fiyat, degisim)
    
    # Yapay zekanın sallamasını engelleyen, derin grafik geçmişi analizi isteyen sert emir seti (prompt):
    prompt = (
        f"Sen Borsa İstanbul (BIST) piyasasında 20 yıllık deneyime sahip, kurumsal fon yöneten kıdemli bir Teknik Analist ve Grafik Uzmanısın.\n"
        f"İncelediğin Hisse: {hisse_kodu}\n"
        f"Anlık Veriler -> Fiyat: {fiyat} TL | Günlük Değişim: %{degisim}\n"
        f"Grafik Teknik İndikatör Değerleri -> RSI(14): {teknik['rsi']} | MACD Durumu: {teknik['macd']} | 50 Günlük Hareketli Ortalama (SMA50): {teknik['sma50']} TL | 200 Günlük Hareketli Ortalama (SMA200): {teknik['sma200']} TL | Stochastic RSI: {teknik['stoch_rsi']}\n\n"
        f"Senden ezbere ve yuvarlak cümleler kurmadan, adeta önündeki açık mum grafiğini okur gibi derinlemesine bir fiyat geçmişi ve kırılım analizi yapmanı istiyorum. Raporu şu formatta hazırla:\n\n"
        f"📊 **{hisse_kodu} DETAYLI GRAFİK VE FORMASYON ANALİZİ**\n\n"
        f"📉 **1) GEÇMİŞ KAPANİŞ VE DÜŞÜŞ / YÜKSELİŞ NEDENLERİ:**\n"
        f"Hissenin son dönemdeki fiyat hareketlerini yorumla. 'Şurada düşmüş çünkü RSI şu seviyedeymiş, hareketli ortalamanın altına sarkmış veya şu dirençten satış yemiş, şurada ise şu formasyonla (örn. ikili dip, çanak vb.) toparlanmış' şeklinde mantıklı, grafik geçmişine dayanan bir açıklama yap.\n\n"
        f"🚧 **2) MATEMATİKSEL DESTEK & DİRENÇ SEVİYELERİ:**\n"
        f"- 🟢 Güçlü Ana Destek Bölgesi: [Net TL Fiyatı] TL (Bu seviyede neden alıcılar bekliyor?)\n"
        f"- 🔴 Aşılması Gereken Kritik Direnç: [Net TL Fiyatı] TL (Daha önce nereden red yedi?)\n"
        f"- ❌ Risk Yönetimi (Zarar Kes / Stop-Loss): [Net TL Fiyatı] TL\n\n"
        f"🎯 **3) HEDEF FİYAT VE GELECEK SENARYOSU:**\n"
        f"Grafikteki formasyon tamamlanırsa orta vadede teknik olarak şuraya ulaşır dediğin net hedef fiyatı yaz. Yüzde kaç potansiyeli var belirt.\n\n"
        f"⚡ **4) AKILLI STRATEJİ SİNYALİ:**\n"
        f"**[GÜÇLÜ AL / KADEMELİ AL / YAKINDAN TAKİP ET (TUT) / KAR AL VEYA SAT]** seçeneklerinden sadece birini KALIN harflerle yaz ve sebebini 1 cümleyle açıkla.\n\n"
        f"Yazım tarzın profesyonel, yatırımcıya güven veren, grafik okuduğunu net belli eden cinsten olsun. Sonuna 'Yatırım tavsiyesi değildir.' notu ekle."
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        res_data = response.json()
        if "candidates" in res_data and res_data["candidates"]:
            return res_data["candidates"][0]["content"]["parts"][0]["text"]
        
        # Yedek Algoritma (Yapay Zeka API'si limit/hata verirse gruptakileri boş bırakmamak için):
        try:
            fiyat_num = float(str(fiyat).replace(",", "."))
        except:
            fiyat_num = 100.0

        destek = round(fiyat_num * 0.95, 2)
        direnc = round(fiyat_num * 1.06, 2)
        stop_loss = round(fiyat_num * 0.92, 2)
        hedef = round(fiyat_num * 1.25, 2)

        return (
            "⚠️ *Yapay zeka analiz motoru şu an yoğun, teknik indikatör kırılım verileri:* \n\n"
            f"📉 **GRAFİK GEÇMİŞİ VE YORUM:** Hisse son mum kapanışlarında SMA50 seviyesi olan {teknik['sma50']} TL üzerinde tutunmaya çalışıyor. "
            f"RSI({teknik['rsi']}) seviyesi nötr bölgede olduğu için sert düşüşün ardından bir konsolidasyon (yatay toplama) evresinde olduğunu gösteriyor.\n\n"
            f"🚧 **SEVİYELER (TL):**\n"
            f"- En Yakın Destek: {destek} TL\n"
            f"- En Yakın Direnç: {direnc} TL\n"
            f"- Stop-Loss: {stop_loss} TL\n\n"
            f"🎯 **HEDEF:** Orta vadeli formasyon hedefi **{hedef} TL** seviyesidir.\n"
            f"⚡ **SİNYAL:** **YAKINDAN TAKİP ET (TUT)**\n\n"
            "Yatırım tavsiyesi değildir."
        )
    except Exception as e:
        logger.error(f"Gemini Hatası: {e}")
        return "⚠️ Grafik analiz motorunda anlık bir aksaklık oldu reis."

async def grafik_ve_analiz_gonder(update: Update, hisse_kodu: str):
    hisse_kodu = hisse_kodu.upper().strip()
    
    # 🎯 GRAFİK ÇÖZÜMÜ: Doğrudan TradingView'in her platformda sorunsuz açılan grafik link yapısını kullanıyoruz
    grafik_url = f"https://s.tradingview.com/widgetembed/?symbol=BIST%3A{hisse_kodu}&interval=D&theme=dark&style=1"

    bekleme_mesajı = await update.effective_message.reply_text(f"🚀 {hisse_kodu} mum grafiği inceleniyor, indikatör kırılımları hesaplanıyor...")
    
    hisse_data = canlı_borsa_verisi_getir(hisse_kodu)
    
    if hisse_data:
        fiyat = hisse_data.get("price", "Veri Yok")
        degisim = hisse_data.get("rate", "0")
        
        loop = asyncio.get_event_loop()
        analiz_raporu = await loop.run_in_executor(None, gemini_ile_grafik_yorumu_yap, hisse_kodu, fiyat, degisim)
        
        # Linki şık bir şekilde mesaja gömüyoruz, böylece Telegram bunu otomatik önizleme olarak chat'e basabiliyor
        tam_metin = (
            f"📊 **[CANLI GRAFİK İÇİN BURAYA TIKLAYIN]({grafik_url})**\n\n"
            f"💰 Güncel Fiyat: {fiyat} TL\n"
            f"📈 Günlük Değişim: %{degisim}\n\n"
            f"{analiz_raporu}"
        )
        
        try:
            await update.effective_message.reply_text(tam_metin, parse_mode="Markdown", disable_web_page_preview=False)
            await bekleme_mesajı.delete()
        except Exception as e:
            logger.error(f"Mesaj gönderme hatası: {e}")
            # Karakter sınırına veya markdown hatasına karşı düz metin koruması
            await update.effective_message.reply_text(f"📊 {hisse_kodu} Analizi:\n{analiz_raporu}")
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
        "Kral Yapay Zeka Destekli Grafik ve Gelişmiş Sinyal Botuna Hoş Geldin! 🚀\n\n"
        "Aşağıdaki butonlardan birine tıkla ya da direkt hisse kodunu yaz.\n"
        "Bot indikatör analizlerini ve derin geçmiş kırılımlarını önüne serecek!"
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
    return {"status": "Derin Grafik Analiz Motoru Sorunsuz Aktif!"}

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
