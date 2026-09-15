import datetime
import os
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

app = Flask(__name__)


@app.route("/")
def home():
  return "Cpm1 Hesap Satis ve Odul Botu Aktif! 🚀"


def run_web():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


# Basit veri saklama (Kullanıcı verileri ve günlük ödüller için)
KULLANICILAR = {}  # {user_id: {"bakiye": 0.0, "yildiz": 0, "son_giris": None, "gun_serisi": 0}}


def stok_oku():
  if not os.path.exists("stok.txt"):
    return []
  with open("stok.txt", "r", encoding="utf-8") as f:
    return [
        line.strip()
        for line in f.readlines()
        if line.strip() and ":" in line
    ]


def stok_dusur_ve_ver():
  stoklar = stok_oku()
  if not stoklar:
    return None
  verilecek_hesap = stoklar[0]
  # Kalanları tekrar dosyaya yaz
  with open("stok.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(stoklar[1:]) + "\n")
  return verilecek_hesap


# --- BOT KOMUTLARI VE MENÜLER ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  if user_id not in KULLANICILAR:
    KULLANICILAR[user_id] = {
        "bakiye": 0.0,
        "yildiz": 0,
        "son_giris": None,
        "gun_serisi": 0,
    }

  keyboard = [
      [InlineKeyboardButton("📦 Hesap Satın Al", callback_data="hesap_al")],
      [InlineKeyboardButton("🎁 Günlük Ödül Al", callback_data="gunluk_odul")],
      [
          InlineKeyboardButton("💰 Bakiye / Puan Durumum", callback_data="profil"),
          InlineKeyboardButton("⭐ Bedava Yıldız", callback_data="bedava_yildiz"),
      ],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  await update.message.reply_text(
      "Selam reis! CPM1 Hesap Satış ve Ödül Botuna hoş geldin. 🎮\n"
      "Aşağıdaki menüden dilediğin gibi işlem yapabilirsin:",
      reply_markup=reply_markup,
  )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  user_id = query.from_user.id

  if user_id not in KULLANICILAR:
    KULLANICILAR[user_id] = {
        "bakiye": 0.0,
        "yildiz": 0,
        "son_giris": None,
        "gun_serisi": 0,
    }
  user_data = KULLANICILAR[user_id]

  # 1. HESAP SATIN ALMA
  if query.data == "hesap_al":
    stoklar = stok_oku()
    if not stoklar:
      await query.edit_message_text(
          "❌ Maalesef şu an stokta hiç hesap kalmamış reis. Lütfen daha sonra"
          " tekrar dene!"
      )
      return

    verilen = stok_dusur_ve_ver()
    if verilen:
      await query.edit_message_text(
          f"✅ Hesap başarıyla alındı!\n\n🔑 Bilgiler:\n`{verilen}`\n\nGüle"
          " güle kullan reis! 🎮",
          parse_mode="Markdown",
      )
    else:
      await query.edit_message_text("❌ Bir hata oluştu, stok bulunamadı.")

  # 2. GÜNLÜK ÖDÜL (0.3'ten başlayarak artan sistem)
  elif query.data == "gunluk_odul":
    bugun = datetime.date.today()
    son_giris = user_data["son_giris"]

    if son_giris == bugun:
      await query.edit_message_text(
          "⏳ Bugün zaten günlük ödülünü aldın reis! Yarın tekrar gel."
      )
      return

    # Seri kontrolü (Dün alındıysa seriyi artır, yoksa 1'e eşitle)
    if son_giris == bugun - datetime.timedelta(days=1):
      user_data["gun_serisi"] += 1
    else:
      user_data["gun_serisi"] = 1

    user_data["son_giris"] = bugun

    # 0.3'ten başlayan ve seriye göre artan ödül hesabı (Örn: 1. gün 0.3, 2. gün 0.6 vb.)
    kazanc = round(0.3 * user_data["gun_serisi"], 2)
    user_data["bakiye"] += kazanc

    await query.edit_message_text(
        f"🎁 Günlük Ödülün Yüklendi!\n\n"
        f"🔥 Seri: {user_data['gun_serisi']}. Gün\n"
        f"💰 Kazanılan Çarpan/Bakiye: +{kazanc}\n"
        f"💳 Toplam Bakiye: {round(user_data['bakiye'], 2)}"
    )

  # 3. PROFİLDESİ / BAKİYE
  elif query.data == "profil":
    await query.edit_message_text(
        f"📊 Profil Bilgilerin:\n\n"
        f"💰 Bakiye / Çarpan Puan: {round(user_data['bakiye'], 2)}\n"
        f"⭐ Yıldız Sayısı: {user_data['yildiz']}\n"
        f"🔥 Günlük Seri: {user_data['gun_serisi']} Gün"
    )

  # 4. BEDAVA YILDIZ
  elif query.data == "bedava_yildiz":
    user_data["yildiz"] += 1
    await query.edit_message_text(
        f"⭐ Tebrikler reis! Günlük bedava 1 yıldız hesabına eklendi.\n"
        f"Toplam Yıldızın: {user_data['yildiz']}"
    )


def main():
  BOT_TOKEN = os.environ.get("BOT_TOKEN", "BURAYA_BOT_TOKEN_YAZ")

  application = ApplicationBuilder().token(BOT_TOKEN).build()

  application.add_handler(CommandHandler("start", start))
  application.add_handler(CallbackQueryHandler(button_handler))

  print("Bot çalışmaya başladı...")
  application.run_polling()


if __name__ == "__main__":
  t = threading.Thread(target=run_web)
  t.daemon = True
  t.start()

  main()
        
