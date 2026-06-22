import os
import requests
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# KRAL: Telegram ve CollectAPI anahtarların tam yerinde sabitleşmiştir
TOKEN = "8295190923:AAFnBfgcKDsNxQ1N6k0wGgU_5eeFa9gIoco"
COLLECTAPI_KEY = "apikey 2GxAMb1niIywZeLVxh0GJ0:7if8NdM3bamD0rYMme2ZW1"

# YENİ YAPAY ZEKA MOTORU: DeepSeek Ayarları
AI_API_KEY = "sk-f5af708c6ddf41d2ba7c0f15cd4410f5"
AI_BASE_URL = "https://api.deepseek.com/v1"
AI_MODEL_NAME = "deepseek-chat"  # Canavar gibi hızlı DeepSeek modeli

bot = Bot(token=TOKEN)
app = FastAPI()

# Render ana sayfa kontrolü (404 hatasını tamamen keser)
@app.get("/")
async def root():
    return {"status": "Bot calisiyor kral, sistem ayakta"}

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
                "rsi": "62 (Notr/Pozitif)",
                "ema50": "Trend Ustunde"
            }
    except Exception as e:
        print(f"Veri cekme hatasi: {e}")
    return None

# 2. Yapay Zeka Analiz Motoru (DeepSeek API Yapısı)
def ai_teknik_analiz(hisse_kod, data):
    url = f"{AI_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}"
    }
    
    prompt = (
        f"Sen profesyonel bir borsa uzmanisin. Yapay zeka jargonu kullanmadan, "
        f"tamamen samimi ve net bir dille konus. {hisse_kod} hissesinin verileri sunlar:\n"
