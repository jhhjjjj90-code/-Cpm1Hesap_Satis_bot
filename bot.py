import os
import random
import string
import threading
import time
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

app = Flask(__name__)


@app.route("/")
def home():
  return "Cpm1 Hesap Satis Botu Aktif ve Calisiyor! 🚀"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


KULLANICILAR = {}
URETILEN_KODLAR = set()
KULLANILAN_KODLAR = set()


def stok_oku():
  if not os.path.exists("stok.txt"):
    return []
  with open("stok.txt", "r", encoding="utf-8") as f:
    return [
        line.strip()
        for line in f.readlines()
        if line.strip() and ":" in line
    ]


def stok_dusur_ve_ver(adet=1):
  stoklar = stok_oku()
  if len(stoklar) < adet:
    return None
  verilecek_hesaplar = stoklar[:adet]
  with open("stok.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(stoklar[adet:]) + "\n")
  return verilecek_hesaplar


def benzersiz_alti_hane_uret():
  karakterler = string.ascii_uppercase + string.digits
  while True:
    kod = "".join(random.choices(karakterler, k=6))
    if kod not in URETILEN_KODLAR:
      URETILEN_KODLAR.add(kod)
      return kod


def get_ana_menu_keyboard(stok_adet, user_data=None):
  keyboard = [
      [
          InlineKeyboardButton(
              "📦 Hesap Satın Al (15 carpipuan)", callback_data="hesap_al_puan"
          )
      ],
      [
          InlineKeyboardButton(
              "⭐ Yıldız ile Hesap Al", callback_data="yildiz_hesap_menu_1"
          )
      ],
      [
          InlineKeyboardButton(
              "⭐ Yıldız ile carpipuan Al", callback_data="carpipuan_menu"
          )
      ],
      [
          InlineKeyboardButton(
              "🎡 Şans Çarkı Çevir (2 Puan)", callback_data="cark_menu"
          )
      ],
      [
          InlineKeyboardButton(
              "🎁 Promosyon Kodu Gir", callback_data="promo_gir_menu"
          )
      ],
      [
          InlineKeyboardButton(
              "🎁 Günlük Ödül Al", callback_data="gunluk_odul"
          )
      ],
      [
          InlineKeyboardButton(
              "🏆 En İyiler (Liderlik)", callback_data="liderlik"
          )
      ],
      [
          InlineKeyboardButton(
              "👥 Arkadaşını Davet Et (+5 Puan)", callback_data="davet_et"
          )
      ],
      [
          InlineKeyboardButton(
              "👑 Admine Özel: 5 Defa 980K Puan Yükle",
              callback_data="admin_980k_yukle",
          )
      ],
  ]

  if user_data and not user_data.get("kod_tuketildi", False):
    if not user_data.get("hediye_kodu"):
      keyboard.append([
          InlineKeyboardButton(
              "🎁 Sana Özel Kodumu Al", callback_data="ozel_kod_al"
          )
      ])

  keyboard.append(
      [InlineKeyboardButton("👤 Profilim & Bilgilerim", callback_data="profil")]
  )
  return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id

  if user_id not in KULLANICILAR:
    KULLANICILAR[user_id] = {
        "carpipuan": 1.0,
        "son_gunluk": 0,
        "davet_edildi": False,
        "hediye_kodu": None,
        "kod_tuketildi": False,
        "kod_bekleniyor": False,
    }

  stok_adet = len(stok_oku())
  user_data = KULLANICILAR[user_id]
  user_data["kod_bekleniyor"] = False

  await update.message.reply_text(
      "🚀 CPM1 Hesap Mağazasına Hoş Geldin!\n\n"
      f"📦 Güncel Stok: {stok_adet} adet hesap\n"
      f"🏆 carpipuanın: {user_data['carpipuan']} carpipuan\n\n"
      "Aşağıdaki menüden işlem seçebilirsin:",
      reply_markup=get_ana_menu_keyboard(stok_adet, user_data),
      parse_mode="Markdown",
  )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  user_id = query.from_user.id

  if user_id not in KULLANICILAR:
    KULLANICILAR[user_id] = {
        "carpipuan": 1.0,
        "son_gunluk": 0,
        "hediye_kodu": None,
        "kod_tuketildi": False,
        "kod_bekleniyor": False,
    }
  user_data = KULLANICILAR[user_id]
  stok_adet = len(stok_oku())
  user_data["kod_bekleniyor"] = False

  if query.data == "admin_980k_yukle":
    eklenen_toplam = 980000.0 * 5
    user_data["carpipuan"] = round(
        user_data["carpipuan"] + eklenen_toplam, 1
    )

    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")]
    ]
    await query.edit_message_text(
        "👑 **Admin Yüklemesi Başarılı!**\n\n"
        f"✨ Hesabına **{eklenen_toplam:,.1f}** Puan yüklendi! 🚀\n\n"
        f"💰 Güncel Puanın: **{user_data['carpipuan']:,.1f}**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return

  elif query.data == "hesap_al_puan":
    if user_data["carpipuan"] < 15.0:
      await query.edit_message_text(
          "❌ Yetersiz carpipuan! En az 15 puana ihtiyacın var."
      )
      return
    if stok_adet < 1:
      await query.edit_message_text("❌ Stokta hiç hesap kalmamış reis!")
      return

    verilenler = stok_dusur_ve_ver(1)
    if verilenler:
      user_data["carpipuan"] = round(user_data["carpipuan"] - 15.0, 1)
      await query.edit_message_text(
          f"✅ Hesap verildi!\n\n🔑 Bilgiler:\n`{verilenler[0]}`\n\nKalan"
          f" puanın: {user_data['carpipuan']}",
          parse_mode="Markdown",
      )

  elif query.data == "cark_menu":
    if user_data["carpipuan"] < 2.0:
      await query.edit_message_text("❌ Çark çevirmek için en az 2 puan lazım!")
      return

    user_data["carpipuan"] = round(user_data["carpipuan"] - 2.0, 1)
    kazanilan = random.choice([0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0])
    user_data["carpipuan"] = round(user_data["carpipuan"] + kazanilan, 1)

    keyboard = [
        [
            InlineKeyboardButton(
                "🎡 Tekrar Çevir", callback_data="cark_menu"
            )
        ],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")],
    ]
    await query.edit_message_text(
        "🎡 **Şans Çarkı Çevrildi!**\n\n"
        f"✨ Kazanılan: **+{kazanilan} Puan**\n💰 Güncel Puanın:"
        f" {user_data['carpipuan']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif query.data == "liderlik":
    sirali = sorted(
        KULLANICILAR.items(), key=lambda x: x[1]["carpipuan"], reverse=True
    )[:10]
    metin = "🏆 **En İyi 10 Liderlik Tablosu**\n\n"
    for sira, (uid, udata) in enumerate(sirali, 1):
      metin += f"{sira}. Kullanıcı: **{udata['carpipuan']}** Puan\n"

    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]
    ]
    await query.edit_message_text(
        metin, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )

  elif query.data == "gunluk_odul":
    simdi = time.time()
    if simdi - user_data["son_gunluk"] < 86400:
      await query.edit_message_text(
          "⏳ Günlük ödülünü zaten almışsın reis, yarın tekrar gel!"
      )
      return

    user_data["son_gunluk"] = simdi
    kazanilan = random.choice([0.5, 1.0, 1.5, 2.0])
    user_data["carpipuan"] = round(user_data["carpipuan"] + kazanilan, 1)

    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]
    ]
    await query.edit_message_text(
        f"🎁 Günlük Ödül: **+{kazanilan} Puan** eklendi!\n💰 Toplam:"
        f" {user_data['carpipuan']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif query.data == "profil":
    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]
    ]
    await query.edit_message_text(
        f"👤 **Profilin:**\n\n🆔 ID: {user_id}\n🏆 Puan:"
        f" {user_data['carpipuan']}\n📦 Stok: {stok_adet}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif query.data == "ana_menu":
    await query.edit_message_text(
        "🚀 CPM1 Hesap Mağazasına Hoş Geldin!\n\n"
        f"📦 Güncel Stok: {stok_adet} adet hesap\n"
        f"🏆 carpipuanın: {user_data['carpipuan']} carpipuan\n\n"
        "Aşağıdaki menüden işlem seçebilirsin:",
        reply_markup=get_ana_menu_keyboard(stok_adet, user_data),
        parse_mode="Markdown",
    )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "Bot aktif! İşlem yapmak için menüyü kullanabilirsin reis. 🎮"
  )


def main():
  BOT_TOKEN = "8962445060:AAEatnjtKUW66d--dFVdjgGnRqLMN_P7o44"
  application = ApplicationBuilder().token(BOT_TOKEN).build()

  application.add_handler(CommandHandler("start", start))
  application.add_handler(CallbackQueryHandler(button_handler))
  application.add_handler(
      MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
  )

  print("Bot Sorunsuz Başlatılıyor...")
  application.run_polling()


if __name__ == "__main__":
  t = threading.Thread(target=run_web)
  t.daemon = True
  t.start()
  main()
                          
