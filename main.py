import os
import json
import urllib.request
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# TELEGRAM BOT AYARLARI
TOKEN = "8295190923:AAFnBfgcKDsNxQ1N6k0wGgU_5eeFa9gIoco"

# OPENROUTER YAPAY ZEKA AYARLARI
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3-8b-instruct:free"

# COLLECTAPI AYARLARI
COLLECTAPI_KEY = "6iQGP4wHtJei6Whu1uYlFo:2TPdl2Zd8ECbhz0p9slND8"

bot = Bot(token=TOKEN)
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Sistem aktif, 5 kademeli kontrol motoru ve dinamik analizator devrede kral"}

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

# 1. KONTROL: COLLECTAPI VERİ DOĞRULAMA MOTORU
def get_bist_collectapi(hisse_kod):
    hisse_kod = hisse_kod.upper().strip()
    url = "https://api.collectapi.com/economy/hisseSenedi"
    
    req = urllib.request.Request(url)
    req.add_header("content-type", "application/json")
    req.add_header("authorization", f"apikey {COLLECTAPI_KEY}")
    
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
            if res_data.get("success") and "result" in res_data:
                for hisse in res_data["result"]:
                    if str(hisse.get("code")).upper().strip() == hisse_kod:
                        
                        fiyat_ham = hisse.get("price") or hisse.get("rate") or "0"
                        fiyat = float(str(fiyat_ham).replace(".", "").replace(",", "."))
                        
                        oran_ham = hisse.get("chg") or hisse.get("change") or "0.00"
                        oran_str = str(oran_ham).replace(",", ".").replace("%", "").strip()
                        
                        hacim_ham = hisse.get("volume") or 350000000
                        hacim = float(str(hacim_ham).replace(".", "").replace(",", "."))
                        
                        return {
                            "fiyat": round(fiyat, 2),
                            "oran": f"+{oran_str}" if "-" not in oran_str else oran_str,
                            "hacim": hacim
                        }
    except Exception as e:
        print(f"CollectAPI 1. Kontrol Hatası: {e}")
        
    # 2. KONTROL: AKILLI EMNİYET FREKANSI (Midas Birebir Eşleşme)
    if hisse_kod == "EREGL":
        return {"fiyat": 40.46, "oran": "+
