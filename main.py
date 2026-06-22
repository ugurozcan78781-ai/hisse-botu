import os
import requests
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8295190923:AAFnBfgcKDsNxQ1N6k0wGgU_5eeFa9gIoco"
COLLECTAPI_KEY = "apikey 2GxAMb1niIywZeLVxh0GJ0:7if8NdM3bamD0rYMme2ZW1"

bot = Bot(token=TOKEN)
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot calisiyor kral, sistem ayakta"}

# Hacim verisini okunabilir formata getiren fonksiyon
def format_hacim(hacim_str):
    try:
        hacim = float(str(hacim_str).replace(",", "."))
        if hacim >= 1_000_000_000:
            return f"{round(hacim / 1_000_000_000, 2)} Milyar TL"
        elif hacim >= 1_000_000:
            return f"{round(hacim / 1_000_000, 2)} Milyon TL"
        return f"{hacim} TL"
    except:
        return str(hacim_str)

# 1. Canlı Veri Çekme Motoru (CollectAPI)
def get_hisse_data(hisse_kod):
    url = f"https://api.collectapi.com/economy/hisseSenedi?text={hisse_kod}"
    headers = {
        "content-type": "application/json",
        "authorization": f"{COLLECTAPI_KEY}"
    }
    try:
        response = requests.get(url, headers=headers).json()
        if response.get("success") and response.get("result") and len(response["result"]) > 0:
            data = response["result"][0]
            return {
                "fiyat": data.get("price", "Bilinmiyor"),
                "hacim": data.get("hacim", "Yuksek"),
                "oran": data.get("rate", "0.00")
            }
    except Exception as e:
        print(f"Veri cekme hatasi: {e}")
    return None

# 2. Geliştirilmiş Analiz Motoru (Para Giriş/Çıkış & Grafik & Seviyeler Dahil)
def simule_ai_analiz(hisse_kod, data):
    # Fiyatı temizleme garantisi
    fiyat_ham = str(data['fiyat']).replace(".", "").replace(",", ".")
    try:
        fiyat = float(fiyat_ham)
        if fiyat < 0.1:
            fiyat = float(str(data['fiyat']).replace(",", "."))
            
        destek1 = round(fiyat * 0.96, 2)
        destek2 = round(fiyat * 0.93, 2)
        direnc1 = round(fiyat * 1.04, 2)
        direnc2 = round(fiyat * 1.08, 2)
        stop_loss = round(fiyat * 0.91, 2)
        fiyat_gosterim = f"{fiyat} TL"
    except:
        fiyat = 250.0 if "THY" in hisse_kod or "THYAO" in hisse_kod else 45.0
        destek1 = round(fiyat * 0.96, 2)
        destek2 = round(fiyat * 0.93, 2)
        direnc1 = round(fiyat * 1.04, 2)
        direnc2 = round(fiyat * 1.08, 2)
        stop_loss = round(fiyat * 0.91, 2)
        fiyat_gosterim = f"{data['fiyat']} TL"

    hacim_gosterim = format_hacim(data['hacim'])
    
    # Oran ve Para Giriş-Çıkış Hesaplama Alanı
    oran_str = str(data['oran']).replace(",", ".")
    try:
        oran_val = float(oran_str)
    except:
        oran_val = 0.0

    try:
        hacim_val = float(str(data['hacim']).replace(",", "."))
    except:
        hacim_val = 50_000_000.0  # Varsayılan hacim simülasyonu

    # Konuştuğumuz Para Giriş / Çıkış Mantığı (Hacim ve Orana Göre Dinamik Hesaplama)
    para_net = (hacim_val * (oran_val / 100)) * 0.15  # Kurumsal net giriş çarpanı
    para_net_milyon = round(abs(para_net) / 1_000_000, 2)

    if oran_val >= 0:
        para_durumu = f"🟢 +{para_net_milyon} Milyon TL (Net Para Girişi var)"
        yorum = f"Hissede şu an kurumsal alıcılar baskın, net para girişi yukarı yönlü hareketi destekliyor. Kısa vadeli yükseliş trendi korunuyor kral."
    else:
        para_durumu = f"🔴 -{para_net_milyon} Milyon TL (Net Para Çıkışı var)"
        yorum = f"Hissede kısa vadeli bir kar satışı ve kurumsal para çıkışı hakim. Destek seviyelerinin yakından takip edilmesi önem arz ediyor reis."

    # Canlı TradingView Grafik Linki
    grafik_url = f"https://tr.tradingview.com/symbols/BIST-{hisse_kod}/"

    text = (
        f"📊 *{hisse_kod} Teknik Analiz Raporu*\n\n"
        f"💰 *Canlı Fiyat:* {fiyat_gosterim}\n"
        f"📈 *Günlük Değişim:* %{data['oran']}\n"
        f"🔥 *Hacim Durumu:* {hacim_gosterim}\n"
        f"💸 *Para Giriş/Çıkış:* {para_durumu}\n\n"
        f"🧠 *Borsa Uzmanı Yorumu:*\n{yorum}\n\n"
        f"🎯 *Kritik Seviyeler:*\n"
        f"🔺 Direnç 1: {direnc1} TL\n"
        f"🔺 Direnç 2: {direnc2} TL\n"
        f"🔻 Destek 1: {destek1} TL\n"
        f"🔻 Destek 2: {destek2} TL\n"
        f"🛑 Stop-Loss: {stop_loss} TL\n\n"
        f"📈 *Canlı Grafik:* [TradingView'da Aç]({grafik_url})\n\n"
        f"⚠️ _Not: Analiz modeli tarafından otomatik üretilmiştir, yatırım tavsiyesi değildir._"
    )
    return text

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
        
    analiz_sonucu = simule_ai_analiz(hisse_kod, hisse_verisi)
    await bekleniyor_mesajı.edit_text(analiz_sonucu, parse_mode="Markdown", disable_web_page_preview=True)

# 4. Webhook Giriş Noktası
@app.post("/webhook")
async def webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, bot)
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analiz_et))
    
    await application.initialize()
    await application.process_update(update)
    return {"status": "ok"}
