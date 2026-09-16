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


def get_ana_menu_keyboard(stok_adet, user_data=None):
  secilen_adet = user_data.get("hesap_adet", 1) if user_data else 1
  toplam_yildiz = secilen_adet * 15

  keyboard = [
      [
          InlineKeyboardButton(
              f"➖", callback_data="hesap_adet_azalt"
          ),
          InlineKeyboardButton(
              f"📦 {secilen_adet} Adet Hesap ({toplam_yildiz} Yıldız)",
              callback_data="bos_bilgi",
          ),
          InlineKeyboardButton(
              f"➕", callback_data="hesap_adet_artir"
          ),
      ],
      [
          InlineKeyboardButton(
              f"💳 Seçilen Hesapları Satın Al ({toplam_yildiz} Yıldız)",
              callback_data="yildiz_coklu_hesap_al",
          )
      ],
      [
          InlineKeyboardButton(
              "⭐ Yıldız ile carpipuan Al (5 Yıldız)",
              callback_data="yildiz_puan_al",
          )
      ],
      [
          InlineKeyboardButton(
              "🎡 Şans Çarkı Çevir (10 Yıldız)", callback_data="cark_yildiz_menu"
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
  ]

  if user_data and not user_data.get("admin_alindi", False):
    keyboard.append([
        InlineKeyboardButton(
            "👑 Admine Özel: 978580 Puan Al", callback_data="admin_özel_yukle"
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
        "admin_alindi": False,
        "hesap_adet": 1,
    }

  stok_adet = len(stok_oku())
  user_data = KULLANICILAR[user_id]

  await update.message.reply_text(
      "🚀 CPM1 Hesap Mağazasına Hoş Geldin!\n\n"
      f"📦 Güncel Stok: {stok_adet} adet hesap\n"
      f"🏆 carpipuanın: +{user_data['carpipuan']} carpipuan\n\n"
      "Aşağıdaki menüden hesap miktarını seçip yıldız ile alabilirsin:",
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
        "admin_alindi": False,
        "hesap_adet": 1,
    }
  user_data = KULLANICILAR[user_id]
  stok_adet = len(stok_oku())

  if query.data == "bos_bilgi":
    return

  elif query.data == "hesap_adet_artir":
    if user_data["hesap_adet"] < stok_adet:
      user_data["hesap_adet"] += 1
    await query.edit_message_reply_markup(
        reply_markup=get_ana_menu_keyboard(stok_adet, user_data)
    )

  elif query.data == "hesap_adet_azalt":
    if user_data["hesap_adet"] > 1:
      user_data["hesap_adet"] -= 1
    await query.edit_message_reply_markup(
        reply_markup=get_ana_menu_keyboard(stok_adet, user_data)
    )

  elif query.data == "admin_özel_yukle":
    if user_data.get("admin_alindi", False):
      await query.edit_message_text(
          "❌ Bu hakkı zaten kullandın reis!"
      )
      return

    user_data["admin_alindi"] = True
    user_data["carpipuan"] = round(user_data["carpipuan"] + 978580.0, 1)

    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")]
    ]
    await query.edit_message_text(
        "👑 **Admin Yüklemesi Başarılı!**\n\n"
        "✨ Hesabına **+978580** Puan eklendi! 🚀\n\n"
        f"💰 Güncel Puanın: **+{user_data['carpipuan']:,.1f}**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return

  elif query.data == "yildiz_coklu_hesap_al":
    adet = user_data.get("hesap_adet", 1)
    toplam_fiyat = adet * 15
    if stok_adet < adet:
      await query.answer("❌ Stokta o kadar hesap yok reis!", show_alert=True)
      return

    await context.bot.send_invoice(
        chat_id=user_id,
        title=f"⭐ Yıldız ile {adet} Adet Hesap Al",
        description=f"{adet} Adet CPM1 Hesabı ({toplam_fiyat} Yıldız)",
        payload=f"hesap_coklu_{adet}",
        currency="XTR",
        prices=[LabeledPrice(f"{adet} Adet Hesap", toplam_fiyat)],
    )

  elif query.data == "yildiz_puan_al":
    await context.bot.send_invoice(
        chat_id=user_id,
        title="⭐ Yıldız ile Carpipuan Al",
        description="+100 Carpipuan Yüklemesi (5 Yıldız)",
        payload="puan_yildiz_satin_al",
        currency="XTR",
        prices=[LabeledPrice("Carpipuan Yükle", 5)],
    )

  elif query.data == "cark_yildiz_menu":
    await context.bot.send_invoice(
        chat_id=user_id,
        title="🎡 Şans Çarkı Çevir",
        description="Şans Çarkı Çevirme Hakkı (10 Yıldız)",
        payload="cark_yildiz_cevir",
        currency="XTR",
        prices=[LabeledPrice("Çark Çevir", 10)],
    )

  elif query.data == "liderlik":
    sirali = sorted(
        KULLANICILAR.items(), key=lambda x: x[1]["carpipuan"], reverse=True
    )[:10]
    metin = "🏆 **En İyi 10 Liderlik Tablosu**\n\n"
    for sira, (uid, udata) in enumerate(sirali, 1):
      metin += f"{sira}. Kullanıcı: **+{udata['carpipuan']}** Puan\n"

    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]
    ]
    await query.edit_message_text(
        metin, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )

  elif query.data == "gunluk_odul":
    simdi = time.time()
    if simdi - user_data["son_gunluk"] < 86400:
      keyboard = [
          [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]
      ]
      await query.edit_message_text(
          "⏳ Günlük ödülünü zaten almışsın reis, yarın tekrar gel!",
          reply_markup=InlineKeyboardMarkup(keyboard),
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
        f" +{user_data['carpipuan']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif query.data == "profil":
    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]
    ]
    await query.edit_message_text(
        f"👤 **Profilin:**\n\n🆔 ID: {user_id}\n🏆 Puan:"
        f" +{user_data['carpipuan']}\n📦 Stok: {stok_adet}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif query.data == "ana_menu":
    await query.edit_message_text(
        "🚀 CPM1 Hesap Mağazasına Hoş Geldin!\n\n"
        f"📦 Güncel Stok: {stok_adet} adet hesap\n"
        f"🏆 carpipuanın: +{user_data['carpipuan']} carpipuan\n\n"
        "Aşağıdaki menüden işlem seçebilirsin:",
        reply_markup=get_ana_menu_keyboard(stok_adet, user_data),
        parse_mode="Markdown",
    )


async def pre_checkout_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  query = update.pre_checkout_query
  await query.answer(ok=True)


async def successful_payment_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  payment = update.message.successful_payment
  payload = payment.invoice_payload
  user_id = update.effective_user.id

  if user_id not in KULLANICILAR:
    KULLANICILAR[user_id] = {"carpipuan": 1.0, "son_gunluk": 0, "hesap_adet": 1}
  user_data = KULLANICILAR[user_id]
  stok_adet = len(stok_oku())

  if payload.startswith("hesap_coklu_"):
    adet = int(payload.split("_")[2])
    if stok_adet < adet:
      await update.message.reply_text(
          "❌ Ödeme alındı fakat stokta o kadar hesap kalmamış! Lütfen adminle"
          " iletişime geç."
      )
      return
    verilenler = stok_dusur_ve_ver(adet)
    if verilenler:
      hesaplar_metni = "\n".join([f"`{h}`" for h in verilenler])
      await update.message.reply_text(
          f"⭐ **Yıldız ile {adet} Adet Hesap Başarıyla Alındı!**\n\n🔑"
          f" Bilgiler:\n{hesaplar_metni}",
          parse_mode="Markdown",
      )

  elif payload == "puan_yildiz_satin_al":
    user_data["carpipuan"] = round(user_data["carpipuan"] + 100.0, 1)
    await update.message.reply_text(
        "⭐ **Yıldız ile Puan Yüklendi!**\n\n✨ Hesabına **+100 Puan**"
        f" eklendi.\n💰 Güncel Puanın: +{user_data['carpipuan']}",
        parse_mode="Markdown",
    )

  elif payload == "cark_yildiz_cevir":
    sans_orani = random.random()
    if sans_orani < 0.0000001 and stok_adet > 0:
      verilenler = stok_dusur_ve_ver(1)
      if verilenler:
        await update.message.reply_text(
            "🎉 **İNANILMAZ! MUCİZE GERÇEKLEŞTİ!** 🎉\n\n10 Yıldızlı Çarktan"
            " **ÜCRETSİZ HESAP** kazandın!\n\n🔑 Bilgiler:\n`{verilenler[0]}`",
            parse_mode="Markdown",
        )
        return

    kazanilan = random.choice([0.0, 0.0, 3.0, 5.0, 10.0])
    user_data["carpipuan"] = round(user_data["carpipuan"] + kazanilan, 1)
    await update.message.reply_text(
        "🎡 **10 Yıldızlı Şans Çarkı Çevrildi!**\n\n✨ Kazanılan Puan: **+"
        f" {kazanilan} Puan**\n💰 Güncel Puanın: +{user_data['carpipuan']}",
        parse_mode="Markdown",
    )


def main():
  BOT_TOKEN = "8962445060:AAEatnjtKUW66d--dFVdjgGnRqLMN_P7o44"
  application = ApplicationBuilder().token(BOT_TOKEN).build()

  application.add_handler(CommandHandler("start", start))
  application.add_handler(CallbackQueryHandler(button_handler))
  application.add_handler(PreCheckoutQueryHandler(pre_checkout_callback))
  application.add_handler(
      MessageHandler(
          filters.SUCCESSFUL_PAYMENT, successful_payment_callback
      )
  )

  print("Bot Sorunsuz Başlatılıyor...")
  application.run_polling()


if __name__ == "__main__":
  t = threading.Thread(target=run_web)
  t.daemon = True
  t.start()
  main()
    
