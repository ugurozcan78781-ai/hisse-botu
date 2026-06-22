import os
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# TELEGRAM BOT TOKENIN
TOKEN = "8295190923:AAFnBfgcKDsNxQ1N6k0wGgU_5eeFa9gIoco"

# KRAL: Gönderdiğin OpenRouter Keyini Tam Buraya Çaktım!
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3-8b-instruct:free"

bot = Bot(token=TOKEN)
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Sistem ayakta, Bigpara + Kendi OpenRouter Keyin Aktif Kral"}

# Hacim sadeleştirme fonksiyonu
def format_hacim(hacim_str):
    try:
        hacim_temiz = str(hacim_str).replace(".", "").replace(",", ".")
        hacim = float(hacim_temiz)
        if hacim >= 1_000_000_000:
            return f"{round(hacim / 1_000_000_000, 2)} Milyar TL"
        elif hacim >= 1_000_000:
            return f"{round(hacim / 1_000_000, 2)} Milyon TL"
        return f"{hacim} TL"
    except:
        return str(hacim_str)

# 1. %100 Doğru BIST Motoru (Bigpara Canlı Kazıyıcı)
def get_bigpara_hisse(hisse_kod):
    hisse_kod = hisse_kod.upper().strip()
    url = f"https://bigpara.hurriyet.com.tr/borsa/hisse-fiyati/{hisse_kod}-detay/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return None
            
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Bigpara üzerinden anlık fiyatı çekiyoruz
        fiyat_element = soup.find("span", {"class": "lastPrice"}) or soup.find("span", {"id": "hisse_fiyat"})
        if not fiyat_element:
            return None
        fiyat_text = fiyat_element.text.strip()

        # Günlük değişim yüzdesini çekiyoruz
        degisim_element
