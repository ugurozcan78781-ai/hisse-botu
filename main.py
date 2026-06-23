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
    return {"status": "CollectAPI Guncel Seans Motoru Aktif"}

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
            if "-" in val_str:
                final_str = f"-{final_str}"
            return float(final_str)
        else:
            cleaned = re.sub(r'[^\d\-]', '', val_str)
            return float(cleaned) if cleaned else 0.0
    except:
        try:
            return float(val_str)
        except:
            return 0.0

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

def get_bist_collectapi(hisse_kod):
    hisse_kod = hisse_kod.upper().strip()
    url = "https://api.collectapi.com/economy/hisseSenedi"
    
    req = urllib.request.Request(url)
    req.add_header("content-type", "application/json")
    req.add_header("authorization", COLLECTAPI_AUTH)
    
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
            if res_data.get("success") and "result" in res_data:
                for hisse in res_data["result"]:
                    api_code = str(hisse.get("code")).upper().strip()
                    # Eslesme saglanirken hem ham kodu hem de .IS uzantisini kontrol ediyoruz
                    if api_code == hisse_kod or api_code == f"{hisse_kod}.IS":
                        fiyat_ham = hisse.get("price") or hisse.get("rate") or "0"
                        oran_ham = hisse.get("chg") or hisse.get("change") or "0.00"
                        hacim_ham = hisse.get("volume") or "0"
                        
                        fiyat = clean_float(fiyat_ham)
                        if fiyat > 100000:
                            fiyat = fiyat / 100.0
                            
                        oran_str = str(oran_ham).replace("%", "").strip()
                        hacim = clean_float(hacim_ham)
                        
                        return {
                            "success": True,
                            "fiyat": round(fiyat, 2),
                            "oran": f"+{oran_str}" if "-" not in oran_str else oran_str,
                            "hacim": hacim,
                            "msg": "Canli API Verisi"
                        }
                        
            # Eger success False ise veya liste bossa API hatasini yakalayalim
            return {"success": False, "msg": f"API baglantisi basarili ama {hisse_kod} listede bulunamadi."}
    except Exception as e:
        return {"success": False, "msg": f"CollectAPI baglanti hatasi olustu: {str(e)}"}

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
    except Exception as e:
        return "Tahtada hacim dengeli gidiyor kral, destek seviyelerini yakindan takip edelim."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Kral hos geldin! Canli seans verileriyle senkronize analiz motoru aktif.")

async def analiz_et(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hisse_kod = update.message.text.upper().strip()
    if hisse_kod.startswith("/"):
        return

    bekleniyor_mesajı = await update.message.reply_text(f"⚡ {hisse_kod} için seans verileri doğrulanıyor...")
    
    hisse_verisi = get_bist_collectapi(hisse_kod)
    
    # EGER API VERIYI CEKEMEDIYSE KULLANICIYA GIZLEMIYORUZ, DOĞRUDAN HATAYI BASIYORUZ
    if not hisse_verisi["success"]:
        await bekleniyor_mesajı.edit_text(f"❌ *Veri Alınamadı Kral!*\n\nSebep: {hisse_verisi['msg']}\n\nLütfen CollectAPI panelinden BIST paketinin aktif olup olmadigini kontrol et.")
        return

    fiyat = hisse_verisi['fiyat']

    destek1 = round(fiyat * 0.97, 2)
    destek2 = round(fiyat * 0.94, 2)
    direnc1 = round(fiyat * 1.03, 2)
    direnc2 = round(fiyat * 1.06, 2)
    stop_loss = round(fiyat * 0.92, 2)

    destek_direnc_metni = f"🔺 Direnç 1: {direnc1} TL\n🔺 Direnç 2: {direnc2} TL\n🔻 Destek 1: {destek1} TL\n🔻 Destek 2: {destek2} TL\n🛑 Stop-Loss: {stop_loss} TL"

    try:
        clean_oran = str(hisse_verisi['oran']).replace("+", "").replace("%", "").strip()
        oran_val = float(clean_
