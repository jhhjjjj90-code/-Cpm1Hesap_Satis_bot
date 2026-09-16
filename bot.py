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
  toplam_puan = secilen_adet * 15

  yildiz_adet = user_data.get("yildiz_hesap_adet", 1) if user_data else 1
  toplam_yildiz = yildiz_adet * 15

  keyboard = [
      [
          InlineKeyboardButton("➖", callback_data="hesap_adet_azalt"),
          InlineKeyboardButton(
              f"📦 {secilen_adet} Adet Hesap ({toplam_puan} carpipuan)",
              callback_data="bos_bilgi",
          ),
          InlineKeyboardButton("➕", callback_data="hesap_adet_artir"),
      ],
      [
          InlineKeyboardButton(
              f"💳 Seçilenleri carpipuan ile Al ({toplam_puan} Puan)",
              callback_data="hesap_al_puan",
          )
      ],
      [
          InlineKeyboardButton("➖", callback_data="yildiz_adet_azalt"),
          InlineKeyboardButton(
              f"⭐ {yildiz_adet} Adet Hesap ({toplam_yildiz} Yıldız)",
              callback_data="bos_bilgi",
          ),
          InlineKeyboardButton("➕", callback_data="yildiz_adet_artir"),
      ],
      [
          InlineKeyboardButton(
              f"⭐ Seçilenleri Yıldız ile Al ({toplam_yildiz} Yıldız)",
              callback_data="yildiz_coklu_hesap_al",
          )
      ],
      [
          InlineKeyboardButton(
              "⭐ Yıldız ile carpipuan Al (Dengeli Paketler)",
              callback_data="yildiz_puan_menu",
          )
      ],
      [
          InlineKeyboardButton(
              "🎁 Promosyon Kodu Gir (0.3 - 5 Puan)",
              callback_data="promo_gir_menu",
          )
      ],
      [
          InlineKeyboardButton(
              "🎁 Günlük Ödül Al (0.3 - 2 Puan)", callback_data="gunluk_odul"
          )
      ],
      [
          InlineKeyboardButton(
              "🏆 En İyiler (Liderlik)", callback_data="liderlik"
          )
      ],
      [
          InlineKeyboardButton(
              "👥 Arkadaşını Davet Et (+5 carpipuan)",
              callback_data="davet_et",
          )
      ],
      [InlineKeyboardButton("👤 Profilim & Bilgilerim", callback_data="profil")],
  ]
  return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id

  if user_id not in KULLANICILAR:
    KULLANICILAR[user_id] = {
        "carpipuan": 0.0,
        "son_gunluk": 0,
        "davet_edildi": False,
        "hediye_kodu": None,
        "kod_tuketildi": False,
        "hesap_adet": 1,
        "yildiz_hesap_adet": 1,
    }

  stok_adet = len(stok_oku())
  user_data = KULLANICILAR[user_id]

  await update.message.reply_text(
      "🚀 CPM1 Hesap Mağazasına Hoş Geldin!\n\n"
      f"📦 Güncel Stok: {stok_adet} adet hesap\n"
      f"🏆 carpipuanın: +{user_data['carpipuan']} carpipuan\n\n"
      "Aşağıdaki menüden miktar seçip işlem yapabilirsin:",
      reply_markup=get_ana_menu_keyboard(stok_adet, user_data),
      parse_mode="Markdown",
  )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  user_id = query.from_user.id

  if user_id not in KULLANICILAR:
    KULLANICILAR[user_id] = {
        "carpipuan": 0.0,
        "son_gunluk": 0,
        "hesap_adet": 1,
        "yildiz_hesap_adet": 1,
    }
  user_data = KULLANICILAR[user_id]
  stok_adet = len(stok_oku())

  if query.data == "bos_bilgi":
    return

  elif query.data == "hesap_adet_artir":
    if user_data["hesap_adet"] < max(1, stok_adet):
      user_data["hesap_adet"] += 1
    try:
      await query.edit_message_reply_markup(
          reply_markup=get_ana_menu_keyboard(stok_adet, user_data)
      )
    except Exception:
      pass

  elif query.data == "hesap_adet_azalt":
    if user_data["hesap_adet"] > 1:
      user_data["hesap_adet"] -= 1
    try:
      await query.edit_message_reply_markup(
          reply_markup=get_ana_menu_keyboard(stok_adet, user_data)
      )
    except Exception:
      pass

  elif query.data == "yildiz_adet_artir":
    if user_data["yildiz_hesap_adet"] < max(1, stok_adet):
      user_data["yildiz_hesap_adet"] += 1
    try:
      await query.edit_message_reply_markup(
          reply_markup=get_ana_menu_keyboard(stok_adet, user_data)
      )
    except Exception:
      pass

  elif query.data == "yildiz_adet_azalt":
    if user_data["yildiz_hesap_adet"] > 1:
      user_data["yildiz_hesap_adet"] -= 1
    try:
      await query.edit_message_reply_markup(
          reply_markup=get_ana_menu_keyboard(stok_adet, user_data)
      )
    except Exception:
      pass

  elif query.data == "hesap_al_puan":
    adet = user_data.get("hesap_adet", 1)
    gerekli_puan = adet * 15.0

    if user_data["carpipuan"] < gerekli_puan:
      await query.answer(
          f"❌ Yetersiz carpipuan! {gerekli_puan} puan lazım.", show_alert=True
      )
      return
    if stok_adet < adet:
      await query.answer("❌ Stokta o kadar hesap yok reis!", show_alert=True)
      return

    verilenler = stok_dusur_ve_ver(adet)
    if verilenler:
      user_data["carpipuan"] = round(user_data["carpipuan"] - gerekli_puan, 1)
      hesaplar_metni = "\n".join([f"`{h}`" for h in verilenler])
      keyboard = [
          [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]
      ]
      await query.edit_message_text(
          f"✅ {adet} Adet Hesap Başarıyla Verildi! (-{gerekli_puan}"
          f" Puan)\n\n🔑 Bilgiler:\n{hesaplar_metni}\n\n💰 Kalan Puanın:"
          f" +{user_data['carpipuan']}",
          reply_markup=InlineKeyboardMarkup(keyboard),
          parse_mode="Markdown",
      )

  elif query.data == "yildiz_coklu_hesap_al":
    adet = user_data.get("yildiz_hesap_adet", 1)
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

  elif query.data == "yildiz_puan_menu":
    keyboard = [
        [
            InlineKeyboardButton(
                "⭐ 50 Yıldız ➔ 50 Puan", callback_data="p_yildiz_50"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ 100 Yıldız ➔ 120 Puan", callback_data="p_yildiz_100"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ 500 Yıldız ➔ 700 Puan", callback_data="p_yildiz_500"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ 1000 Yıldız ➔ 1.500 Puan", callback_data="p_yildiz_1000"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ 2500 Yıldız ➔ 4.000 Puan", callback_data="p_yildiz_2500"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ 10000 Yıldız ➔ 20.000 Puan", callback_data="p_yildiz_10000"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ 20000 Yıldız ➔ 40.000 Puan", callback_data="p_yildiz_20000"
            )
        ],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")],
    ]
    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

  elif query.data.startswith("p_yildiz_"):
    yildiz_miktari = int(query.data.split("_")[2])

    puan_tablosu = {
        50: 50,
        100: 120,
        500: 700,
        1000: 1500,
        2500: 4000,
        10000: 20000,
        20000: 40000,
    }
    kazanilacak_puan = puan_tablosu.get(yildiz_miktari, 50)

    await context.bot.send_invoice(
        chat_id=user_id,
        title=f"⭐ {yildiz_miktari} Yıldız ile {kazanilacak_puan} Puan Al",
        description=f"Ödenen {yildiz_miktari} Yıldız karşılığı {kazanilacak_puan} Carpipuan yüklemesi",
        payload=f"puan_yukle_{yildiz_miktari}_{kazanilacak_puan}",
        currency="XTR",
        prices=[LabeledPrice(f"{yildiz_miktari} Yıldız Paketi", yildiz_miktari)],
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
    kazanilan = round(random.uniform(0.3, 2.0), 1)
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
    try:
      await query.edit_message_text(
          "🚀 CPM1 Hesap Mağazasına Hoş Geldin!\n\n"
          f"📦 Güncel Stok: {stok_adet} adet hesap\n"
          f"🏆 carpipuanın: +{user_data['carpipuan']} carpipuan\n\n"
          "Aşağıdaki menüden işlem seçebilirsin:",
          reply_markup=get_ana_menu_keyboard(stok_adet, user_data),
          parse_mode="Markdown",
      )
    except Exception:
      pass


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
    KULLANICILAR[user_id] = {
        "carpipuan": 0.0,
        "son_gunluk": 0,
        "hesap_adet": 1,
        "yildiz_hesap_adet": 1,
    }
  user_data = KULLANICILAR[user_id]
  stok_adet = len(stok_oku())

  if payload.startswith("hesap_coklu_"):
    adet = int(payload.split("_")[2])
    if stok_adet < adet:
      await update.message.reply_text(
          "❌ Ödeme alındı fakat stokta o kadar hesap kalmış! Lütfen adminle"
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

  elif payload.startswith("puan_yukle_"):
    parcalar = payload.split("_")
    yuklenen_puan = int(parcalar[3])

    user_data["carpipuan"] = round(user_data["carpipuan"] + yuklenen_puan, 1)
    await update.message.reply_text(
        f"⭐ **Carpipuan Başarıyla Yüklendi!**\n\n✨ Hesabına **+{yuklenen_puan}"
        f" Puan** eklendi! 🚀\n💰 Güncel Puanın: +{user_data['carpipuan']}",
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
