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

COLLECTAPI_AUTH = "apikey 6iQGP4wHtJei6Whu1uYlFo:2TPdl2Zd8ECbhz0p9slND8"

bot = Bot(token=TOKEN)
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Teshis Motoru Aktif"}

def clean_float(val_str):
    if not val_str:
        return 0.0
    val_str = str(val_str).strip()
    if "," in val_str and "." not in val_str:
        val_str = val_str.replace(",", ".")
    try:
        if "." in val_str:
            parts = val_str.split(".")
            kurus = parts[-1]
            tam_kisim = "".join(parts[:-1]).replace(",", "").replace("-", "")
            final_str = f"{tam_kisim}.{kurus}"
            return float(final_str)
        else:
            cleaned = re.sub(r'[^\d\-]', '', val_str)
            return float(cleaned) if cleaned else 0.0
    except:
        return 0.0

def get_bist_collectapi(hisse_kod):
    hisse_kod = hisse_kod.upper().strip()
    url = "https://api.collectapi.com/economy/hisseSenedi"
    
    req = urllib.request.Request(url)
    req.add_header("content-type", "application/json")
    req.add_header("authorization", COLLECTAPI_AUTH)
    req.add_header("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
            if res_data.get("success") and "result" in res_data:
                liste = res_data["result"]
                
                # TESHIS: API'den gelen ilk 3 hissenin kodunu loglamak icin saklayalim
                ornek_kodlar = [str(h.get("code")) for h in liste[:3]]
                
                for hisse in liste:
                    api_code = str(hisse.get("code")).upper().strip()
                    if api_code == hisse_kod or api_code == f"{hisse_kod}.IS" or hisse_kod in api_code:
                        fiyat = clean_float(hisse.get("price") or hisse.get("rate"))
                        oran = str(hisse.get("chg") or hisse.get("change") or "0.00")
                        hacim = clean_float(hisse.get("volume"))
                        
                        if fiyat == 0:
                            continue
                            
                        return {
                            "success": True,
                            "fiyat": fiyat,
                            "oran": oran,
                            "hacim": hacim,
                            "debug": False
                        }
                
                # Eslesme bulamazsa manyamak yerine canli gelen format bilgisini gonderiyoruz
                return {
                    "success": False, 
                    "msg": f"API baglantisi OK ama '{hisse_kod}' tam eslesmedi.\nAPI'deki ornek kodlama formatlari: {ornek_kodlar}"
                }
            return {"success": False, "msg": f"API success donmedi: {res_data.get('text', 'Bilinmeyen hata')}"}
    except Exception as e:
        return {"success": False, "msg": f"API baglanti hatasi: {str(e)}"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Teshis modu aktif kral.")

async def analiz_et(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hisse_kod = update.message.text.upper().strip()
    if hisse_kod.startswith("/"):
        return

    bekleniyor_mesajı = await update.message.reply_text(f"⚡ {hisse_kod} inceleniyor...")
    hisse_verisi = get_bist_collectapi(hisse_kod)
    
    # Eger eslesme saglanamadiysa canli logu Telegram ekraına basıyoruz
    if not hisse_verisi["success"]:
        await bekleniyor_mesajı.edit_text(f"🔍 *Teşhis Raporu Geldi Kral:*\n\n{hisse_verisi['msg']}")
        return

    fiyat = hisse_verisi['fiyat']
    destek1 = round(fiyat * 0.97, 2)
    direnc1 = round(fiyat * 1.03, 2)

    final_text = (
        f"📊 *{hisse_kod} Canlı Veri Başarılı!*\n\n"
        f"💰 *Fiyat:* {fiyat} TL\n"
        f"📈 *Değişim:* {hisse_verisi['oran']}\n"
        f"🎯 *Direnç 1:* {direnc1} TL\n"
        f"🔻 *Destek 1:* {destek1} TL\n"
    )
    await bekleniyor_mesajı.edit_text(final_text, parse_mode="Markdown")

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
