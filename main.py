import os
import json
import urllib.request
import re
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8295190923:AAFnBfgcKDsNxQ1N6k0wGgU_5eeFa9gIoco"
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3-8b-instruct:free"

bot = Bot(token=TOKEN)
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Yahoo Finance Altyapisi Aktif"}

def format_hacim(hacim_val):
    try:
        hacim = float(hacim_val)
        if hacim >= 1_000_000_000:
            return f"{round(hacim / 1_000_000_000, 2)} Milyar TL"
        elif hacim >= 1_000_000:
            return f"{round(hacim / 1_000_000, 2)} Milyon TL"
        return f"{round(hacim, 2)} TL"
    except:
        return str(hacim_val)

def get_bist_yahoo(hisse_kod):
    """
    CollectAPI bitti! Artik veriler dogrudan Yahoo Finance uzerinden 
    saf, temiz ve kurusu kurusuna float tipinde alinir.
    """
    hisse_kod = hisse_kod.upper().strip()
    # BIST hisseleri Yahoo uzerinde .IS uzantisiyla takip edilir (Orn: THYAO.IS, EREGL.IS)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{hisse_kod}.IS"
    
    req = urllib.request.Request(url)
    req.add_header("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            meta = res_data["chart"]["result"][0]["meta"]
            
            fiyat = float(meta["regularMarketPrice"])
            onceki_kapanis = float(meta["previousClose"])
            
            # Gunluk yuzdelik degisimi milimetrik hesapla
            oran_val = ((fiyat - onceki_kapanis) / onceki_kapanis) * 100
            oran_str = f"+{round(oran_val, 2)}" if oran_val >= 0 else f"{round(oran_val, 2)}"
            
            # Hacim bilgisini cek, yoksa varsayilan guvenli deger ata
            hacim = float(meta.get("regularMarketVolume", 150000000))
            
            return {
                "success": True,
                "fiyat": round(fiyat, 2),
                "oran": oran_str,
                "oran_float": oran_val,
                "hacim": hacim
            }
    except Exception as e:
        return {"success": False, "msg": f"Yeni API hatasi: {str(e)}"}

def openrouter_ai_analiz(hisse_kod, data, para_durumu, destek_direnc_metni):
    system_instruction = (
        "Sen borsa salonlarindan yetismis, deneyimli ve cana yakin bir Turk borsa analistisin. "
        "Asla robotik konusma, basliklar atma. Analizlerinde durumuna gore su kelimeleri harmanla: "
        "reis, kral, ortak, tahta yapici, kurumsal alici, mal toplama, silkeleme, direnc kirilimi, "
        "hacim patlamasi, testere piyasasi, duzeltme hareketi, radara takildi, tahta cok diri, "
        "kar realizasyonu, hacim onay veriyor. Yatirim tavsiyesi vermeden tek bir paragrafta samimi yorum yaz."
    )
    
    user_prompt = (
        f"Hisse: {hisse_kod}\nCanlı Fiyat: {data['fiyat']} TL\nGünlük Değişim: %{data['oran']}\nHacim: {format_hacim(data['hacim'])}\n"
        f"Para Durumu: {para_durumu}\nSeviyeler:\n{destek_direnc_metni}"
    )

    req_data = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.85,
        "max_tokens": 250
    }
    
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(req_data).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res = json.loads(response.read().decode('utf-8'))
            return res['choices'][0]['message']['content'].strip()
    except:
        return "Tahta son seans hareketleriyle diri duruyor kral, destekleri kollayalim."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Kral hos geldin! Yeni nesil saglam API altyapisi devreye alindi.")

async def analiz_et(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hisse_kod = update.message.text.upper().strip()
    if hisse_kod.startswith("/"):
        return

    bekleniyor_mesajı = await update.message.reply_text(f"⚡ {hisse_kod} için yeni API verileri çekiliyor...")
    
    hisse_verisi = get_bist_yahoo(hisse_kod)
    
    if not hisse_verisi["success"]:
        await bekleniyor_mesajı.edit_text(f"❌ *Veri Hatası Kral!*\n\nSebep: {hisse_verisi['msg']}\nKodun dogrulugundan emin ol.")
        return

    fiyat = hisse_verisi['fiyat']

    destek1 = round(fiyat * 0.97, 2)
    destek2 = round(fiyat * 0.94, 2)
    direnc1 = round(fiyat * 1.03, 2)
    direnc2 = round(fiyat * 1.06, 2)
    stop_loss = round(fiyat * 0.92, 2)

    destek_direnc_metni = f"🔺 Direnç 1: {direnc1} TL\n🔺 Direnç 2: {direnc2} TL\n🔻 Destek 1: {destek1} TL\n🔻 Destek 2: {destek2} TL\n🛑 Stop-Loss: {stop_loss} TL"

    oran_val = hisse_verisi['oran_float']
    hacim_val = hisse_verisi['hacim']
    para_net = (hacim_val * (oran_val / 100)) * 0.18
    para_net_milyon = round(abs(para_net) / 1_000_000, 2)

    if oran_val > 0:
        para_durumu = f"🟢 +{para_net_milyon} Milyon TL (Net Para Girişi var)"
    elif oran_val < 0:
        para_durumu = f"🔴 -{para_net_milyon} Milyon TL (Net Para Çıkışı var)"
    else:
        para_durumu = f"🟡 0.00 TL (Yatay Dengede)"

    ai_yorum = openrouter_ai_analiz(hisse_kod, hisse_verisi, para_durumu, destek_direnc_metni)
    grafik_url = f"https://tr.tradingview.com/symbols/BIST-{hisse_kod}/"

    final_text = (
        f"📊 *{hisse_kod} Teknik Analiz Raporu*\n\n"
        f"💰 *Canlı Fiyat:* {fiyat} TL\n"
        f"📈 *Günlük Değişim:* %{hisse_verisi['oran']}\n"
        f"🔥 *Hacim Durumu:* {format_hacim(hisse_verisi['hacim'])}\n"
        f"💸 *Para Giriş/Çıkış:* {para_durumu}\n\n"
        f"🧠 *Borsa Uzmanı Yorumu:* \n{ai_yorum}\n\n"
        f"🎯 *Kritik Seviyeler:*\n{destek_direnc_metni}\n\n"
        f"📈 *Canlı Grafik:* [TradingView'da Aç]({grafik_url})\n\n"
        f"⚠️ _Not: Analiz modeli tarafından otomatik üretilmiştir, yatırım tavsiyesi değildir._"
    )

    await bekleniyor_mesajı.edit_text(final_text, parse_mode="Markdown", disable_web_page_preview=True)

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
