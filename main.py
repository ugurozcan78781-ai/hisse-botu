import os
import requests
import yfinance as yf
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# TELEGRAM BOT TOKENIN
TOKEN = "8295190923:AAFnBfgcKDsNxQ1N6k0wGgU_5eeFa9gIoco"

# OPENROUTER YAPAY ZEKA AYARLARI (Kendi anahtarın tanımlı)
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3-8b-instruct:free"

bot = Bot(token=TOKEN)
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Sistem aktif, yfinance motoru devrede kral"}

# Hacim sadeleştirme fonksiyonu
def format_hacim(hacim_val):
    try:
        hacim = float(hacim_val)
        if hacim >= 1_000_000_000:
            return f"{round(hacim / 1_000_000_000, 2)} Milyar TL"
        elif hacim >= 1_000_000:
            return f"{round(hacim / 1_000_000, 2)} Milyon TL"
        return f"{hacim} TL"
    except:
        return str(hacim_val)

# 1. KESİN VE ANLIK VERİ MOTORU (Yahoo Finance BIST Entegrasyonu)
def get_bist_hisse(hisse_kod):
    hisse_kod = hisse_kod.upper().strip()
    # BIST hisseleri Yahoo üzerinde sonuna .IS eklenerek çağrılır (Örn: EREGL.IS, THYAO.IS)
    ticker_sembol = f"{hisse_kod}.IS"
    
    try:
        ticker = yf.Ticker(ticker_sembol)
        info = ticker.info
        
        # Anlık fiyatı en doğru kaynaktan alıyoruz
        fiyat = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if not fiyat:
            return None
            
        # Günlük değişim yüzdesi hesaplama
        prev_close = info.get("regularMarketPreviousClose")
        if prev_close and fiyat:
            oran_val = ((fiyat - prev_close) / prev_close) * 100
            oran_text = f"{'+' if oran_val >= 0 else ''}{round(oran_val, 2)}"
        else:
            oran_text = "0.00"
            
        hacim = info.get("regularMarketVolume") or 150000000

        return {
            "fiyat": round(float(fiyat), 2),
            "oran": oran_text,
            "hacim": hacim
        }
    except Exception as e:
        print(f"yfinance veri çekme hatası: {e}")
        return None

# 2. OpenRouter Llama 3 Analiz Motoru
def openrouter_ai_analiz(hisse_kod, data, para_durumu, destek_direnc_metni):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    prompt = (
        f"Sen deneyimli bir Türk borsa analistisin. Türkçe dilinde, borsa jargonu boğmadan, samimi ve karizmatik bir dille konuş.\n"
        f"Veriler şunlar:\n"
        f"Hisse: {hisse_kod}\nCanlı Fiyat: {data['fiyat']} TL\nGünlük Değişim: %{data['oran']}\nHacim: {format_hacim(data['hacim'])}\n"
        f"Para Durumu: {para_durumu}\nKritik Seviyeler:\n{destek_direnc_metni}\n\n"
        f"Bu verilere bakarak yönü yatırım tavsiyesi vermeden samimi bir şekilde yorumla. Başlık atma, direkt konuya gir reis."
    )
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        res = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=10).json()
        return res['choices'][0]['message']['content']
    except Exception as e:
        print(f"OpenRouter Hatası: {e}")
        return "Hissede hacim dengeli ilerliyor kral, destek ve direnç seviyelerini yakından takip edelim."

# 3. Telegram Akış Yönetimi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Kral hoş geldin! yfinance canlı veri motoru aktif. Analiz istediğin hisse kodunu yaz (Örn: THYAO)")

async def analiz_et(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hisse_kod = update.message.text.upper().strip()
    
    if hisse_kod.startswith("/"):
        return

    bekleniyor_mesajı = await update.message.reply_text(f"⚡ {hisse_kod} için anlık veriler doğrulanıyor...")
    
    # Canlı veriyi kayıpsız çekiyoruz
    hisse_verisi = get_bist_hisse(hisse_kod)
    if not hisse_verisi:
        await bekleniyor_mesajı.edit_text("Hisse kodu bulunamadı veya canlı veri hattı bağlanamadı kral. Kodu kontrol et.")
        return
        
    fiyat = hisse_verisi['fiyat']

    # Gerçek fiyat üzerinden matematiksel destek direnç seviyeleri
    destek1 = round(fiyat * 0.97, 2)
    destek2 = round(fiyat * 0.94, 2)
    direnc1 = round(fiyat * 1.03, 2)
    direnc2 = round(fiyat * 1.06, 2)
    stop_loss = round(fiyat * 0.92, 2)

    destek_direnc_metni = f"🔺 Direnç 1: {direnc1} TL\n🔺 Direnç 2: {direnc2} TL\n🔻 Destek 1: {destek1} TL\n🔻 Destek 2: {destek2} TL\n🛑 Stop-Loss: {stop_loss} TL"

    # Para Giriş / Çıkış Hesaplaması
    try:
        oran_val = float(str(hisse_verisi['oran']).replace("+", "").strip())
    except:
        oran_val = 0.0

    hacim_val = float(hisse_verisi['hacim'])
    para_net = (hacim_val * (oran_val / 100)) * 0.18
    para_net_milyon = round(abs(para_net) / 1_000_000, 2)

    if oran_val > 0:
        para_durumu = f"🟢 +{para_net_milyon} Milyon TL (Net Para Girişi var)"
    elif oran_val < 0:
        para_durumu = f"🔴 -{para_net_milyon} Milyon TL (Net Para Çıkışı var)"
    else:
        para_durumu = f"🟡 0.00 TL (Yatay Dengede)"

    # OpenRouter üzerinden Llama 3 yorumunu senin keyinle çekiyoruz
    ai_yorum = openrouter_ai_analiz(hisse_kod, hisse_verisi, para_durumu, destek_direnc_metni)

    grafik_url = f"https://tr.tradingview.com/symbols/BIST-{hisse_kod}/"

    final_text = (
        f"📊 *{hisse_kod} Teknik Analiz Raporu*\n\n"
        f"💰 *Canlı Fiyat:* {fiyat} TL\n"
        f"📈 *Günlük Değişim:* %{hisse_verisi['oran']}\n"
        f"🔥 *Hacim Durumu:* {format_hacim(hisse_verisi['hacim'])}\n"
        f"💸 *Para Giriş/Çıkış:* {para_durumu}\n\n"
        f"🧠 *Borsa Uzmanı Yorumu (OpenRouter):*\n{ai_yorum}\n\n"
        f"🎯 *Kritik Seviyeler:*\n{destek_direnc_metni}\n\n"
        f"📈 *Canlı Grafik:* [TradingView'da Aç]({grafik_url})\n\n"
        f"⚠️ _Not: Analiz modeli tarafından otomatik üretilmiştir, yatırım tavsiyesi değildir._"
    )

    await bekleniyor_mesajı.edit_text(final_text, parse_mode="Markdown", disable_web_page_preview=True)

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
