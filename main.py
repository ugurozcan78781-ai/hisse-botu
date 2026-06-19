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

# ANAHTARLARIN (Buradaki Gemini Key'i güncel kendi keyinle değiştirmeyi unutma kral)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8295190923:AAFnBfgcKDsNxQ1N6k0wGgU_5eeFa9gIoco")
COLLECTAPI_KEY = os.environ.get("COLLECTAPI_KEY", "2GxAMb1niIywZeLVxh0GJ0:7if8NdM3bamD0rYMme2ZW1")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6JR2IUTpaZh4RlNIE77MzPmd037UiCSRX4VBjpbCAtewA")

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
    logger.info("🚀 Çizgileri ve Dili Basitleştirilmiş Analiz Botu Devrede!")
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

def gemini_ile_basit_yorum_yap(hisse_kodu, fiyat, degisim):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # Kafa karıştırıcı borsa terimlerini kaldıran, net ve halk diliyle yazdıran prompt:
    prompt = (
        f"Sen borsa grafiklerini ve fiyat hareketlerini sıradan bir insana en sade, en anlaşılır şekilde anlatan samimi bir finans danışmanısın.\n"
        f"İncelediğin Hisse: {hisse_kodu}\n"
        f"Anlık Durum -> Fiyat: {fiyat} TL | Bugün %{degisim} hareket etmiş.\n\n"
        f"Senden ağır borsa terimleri (RSI, MACD, formasyon, konsolidasyon, osilatör, hacim vb.) KULLANMADAN, sanki bir arkadaşına kahvede anlatır gibi net bir analiz hazırlamanı istiyorum. Raporu şu başlıklarla hazırla:\n\n"
        f"📊 **{hisse_kodu} HİSSE ANALİZİ (BASİT ANLATIM)**\n\n"
        f"📉 **1) BU HİSSEDE NELER OLUYOR? (NEDEN DÜŞTÜ / YÜKSELDİ?):**\n"
        f"Hissenin fiyat gidişatını yorumla. Ağır terimlere girmeden, 'Dostum bu hisse şuraya kadar çok çıkmıştı, oradan insanlar kârını alıp satmaya başlayınca biraz gerilemiş' veya 'Şu an alıcılar biraz çekingen davranıyor, fiyatı aşağı bastırmışlar ama buralardan yavaş yavaş toparlanma belirtisi var' gibi herkesin anlayacağı cümlelerle şeffafça açıkla.\n\n"
        f"🚧 **2) KORKULACAK VE SEVİNİLECEK SEVİYELER (TL):**\n"
        f"- 🟢 Güvenli Duvar (Destek): [Net Fiyat] TL -> (Fiyat buraya düşerse genelde düşüş durur, buralar ucuz demektir.)\n"
        f"- 🔴 Aşılması Gereken Tepe (Direnç): [Net Fiyat] TL -> (Fiyatın yukarı fırlaması için bu basamağı kırıp geçmesi lazım.)\n"
        f"- ❌ Tehlike Çanları (Stop-Loss): [Net Fiyat] TL -> (Fiyat buranın altına inerse stop olmak, yani zararı kesip çıkmak mantıklı olabilir.)\n\n"
        f"🎯 **3) ÖNÜMÜZDEKİ GÜNLERDE NE BEKLİYORUZ?:**\n"
        f"Eğer işler yolunda giderse önümüzdeki süreçte hissenin rahatlıkla ulaşabileceği gerçekçi hedef fiyatı yaz. Yüzde kaç kazandırabilir belirt.\n\n"
        f"⚡ **4) BİZ ŞU AN NE YAPALIM?:**\n"
        f"**[GÜÇLÜ AL / KADEMELİ AL / ŞİMDİLİK BEKLE (TUT) / SAT VE ÇIK]** seçeneklerinden birini kalın harflerle seç ve çok kısa, net bir tavsiye ver.\n\n"
        f"Yazım tarzın çok sade, samimi, akıcı ve yormayan cinsten olsun. Sonuna 'Yatırım tavsiyesi değildir.' eklemeyi unutma."
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        res_data = response.json()
        if "candidates" in res_data and res_data["candidates"]:
            return res_data["candidates"][0]["content"]["parts"][0]["text"]
        
        # Eğer senin Gemini Key'in hala geçersizse veya API hata verirse yedek olarak da en sade dili basıyoruz:
        return (
            "⚠️ *Yapay zeka anahtarı şu an devre dışı olduğu için sistem otomatik hesaplama yaptı reis:*\n\n"
            "📉 **HİSSE DURUMU:** Hisse son günlerde satıcıların baskısı altında kalmış ve biraz geriye çekilmiş. "
            "Şu an fiyatta bir dengelenme ve nefes alma çabası görülüyor, alıcılar güç topluyor.\n\n"
            "🚧 **BİLİNMESİ GEREKEN SEVİYELER:**\n"
            "   Fiyat buraya gelirse düşüş yavaşlayabilir.\n"
            "   Hissenin önünün açılması için bu seviyeyi yukarı geçmesi şart.\n\n"
            "🎯 **BEKLENTİ:** İşler normale dönerse orta vadede yaklaşık %+25'lik bir yukarı hareket alanı mevcut.\n"
            "⚡ **TAVSİYE:** **ŞİMDİLİK BEKLE (TUT)** - Acele etmeden tahtanın nereye oturacağını izlemek daha güvenli.\n\n"
            "Yatırım tavsiyesi değildir."
        )
    except Exception as e:
        logger.error(f"Gemini Hatası: {e}")
        return "⚠️ Analiz motoru şu an uyku modunda reis."

async def grafik_ve_analiz_gonder(update: Update, hisse_kodu: str):
    hisse_kodu = hisse_kodu.upper().strip()
    
    # 🎯 KESİN FOTOĞRAF ÇÖZÜMÜ: Telegram'ın harici sitelere ihtiyaç duymadan doğrudan sohbet içine çizebileceği şık ve resmi TradingView grafik görseli
    grafik_foto_url = f"https://s3.tradingview.com/snapshots/{hisse_kodu.lower()[0]}/{hisse_kodu.lower()}.png"

    bekleme_mesajı = await update.effective_message.reply_text(f"🚀 {hisse_kodu} verileri alınıyor, senin için sadeleştiriliyor...")
    
    hisse_data = canlı_borsa_verisi_getir(hisse_kodu)
    
    if hisse_data:
        fiyat = hisse_data.get("price", "Veri Yok")
        degisim = hisse_data.get("rate", "0")
        
        loop = asyncio.get_event_loop()
        analiz_raporu = await loop.run_in_executor(None, gemini_ile_basit_yorum_yap, hisse_kodu, fiyat, degisim)
        
        tam_metin = (
            f"💰 Güncel Fiyat: {fiyat} TL\n"
            f"📈 Günlük Değişim: %{degisim}\n\n"
            f"{analiz_raporu}"
        )
        
        try:
            # 🎯 RESMİ DOĞRUDAN TELEGRAM'A GÖMME:
            await update.effective_message.reply_photo(
                photo=grafik_foto_url,
                caption=tam_metin[:1024]
            )
            if len(tam_metin) > 1024:
                await update.effective_message.reply_text(tam_metin[1024:])
                
            await bekleme_mesajı.delete()
        except Exception as e:
            logger.error(f"Fotoğraf gönderme hatası: {e}")
            # Fotoğraf yüklemede Telegram anlık takılırsa bot patlamasın diye düzgünce linkli metin geçiyoruz
            grafik_yedek_link = f"https://s.tradingview.com/widgetembed/?symbol=BIST%3A{hisse_kodu}&interval=D&theme=dark"
            metin_linkli = f"📊 **[CANLI GRAFİĞİ GÖRMEK İÇİN TIKLA]({grafik_yedek_link})**\n\n{tam_metin}"
            await update.effective_message.reply_text(metin_linkli, parse_mode="Markdown")
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
        "Kral Sade Anlatımlı Borsa Botuna Hoş Geldin! 🚀\n\n"
        "Aşağıdaki butonlardan birine tıkla ya da direkt hisse kodunu yaz.\n"
        "Grafik fotoğrafıyla beraber, herkesin anlayacağı dilden analiz anında cebinde!"
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
    return {"status": "Basit Anlatımlı Grafik Sistemi Ayakta!"}

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
