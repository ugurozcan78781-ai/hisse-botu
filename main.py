import os
import requests
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# 1. Render için uyanık kalma (Web Sunucusu) ayarı
app = Flask('')

@app.route('/')
def home():
    return "Bot 7/24 Aktif!"

def run():
    # Render portu otomatik ayarlar, yoksa 8080 kullanır
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. Borsa API ve Hisse Sorgulama Mantığı
def getir_hisse(hisse_adi):
    api_key = "2GxAMb1niIywZeLVxh0GJ0:7if8NdM3bamD0rYMme2ZW1"
    url = "https://api.collectapi.com/economy/hisseSenedi"
    headers = {'authorization': f"apikey {api_key}"}
    
    try:
        data = requests.get(url, headers=headers).json()
        hisse = hisse_adi.upper().strip()
        
        for h in data['result']:
            if h['code'].upper() == hisse:
                degisim = float(str(h['rate']).replace(',','.'))
                sinyal = "🚀 AL" if degisim > 0 else "📉 SAT"
                return f"📊 {h['code']} ANALİZİ\nFiyat: {h['lastprice']} TL\nDeğişim: %{h['rate']}\nSinyal: {sinyal}"
        return "❌ Hisse bulunamadı."
    except Exception as e:
        return f"Veri çekilemedi, hata: {str(e)}"

# 3. Telegram Mesaj Karşılama
async def mesaj_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        hisse_kodu = update.message.text
        cevap = getir_hisse(hisse_kodu)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=cevap)

# 4. Ana Çalıştırma Bloğu
if __name__ == '__main__':
    # Token'ı Render panelinden güvenli bir şekilde çekeceğiz
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    
    # Sunucuyu uyanık tutma fonksiyonunu başlat
    keep_alive()
    
    # Botu ayağa kaldır
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), mesaj_al))
    
    print("Bot sunucu üzerinde başlatıldı...")
    application.run_polling()
