import os
import random
import threading
import time
from flask import Flask
from telegram import LabeledPrice, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

app = FlaskName(__name__) if "__name__" == "__main__" else Flask(__name__)


@app.route("/")
def home():
  return "Cpm1 Hesap Satis ve carpipuan Botu Aktif ve Calisiyor! 🚀"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


# Kullanıcı verileri ve promosyon kodları havuzu
KULLANICILAR = {}
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


# --- BOT KOMUTLARI VE MENÜLER ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id

  if user_id not in KULLANICILAR:
    baslangic_secenekleri = [0.0, 0.5, 0.8, 1.0, 1.5, 2.0]
    rastgele_hediye = random.choice(baslangic_secenekleri)
    ozel_hediye_kodu = f"CPM-{user_id}-{random.randint(1000, 9999)}"

    KULLANICILAR[user_id] = {
        "carpipuan": rastgele_hediye,
        "son_gunluk": 0,
        "davet_edildi": False,
        "hediye_kodu": ozel_hediye_kodu,
        "kod_bekleniyor": False,
    }

  # Referans kontrolü
  if context.args:
    try:
      ref_id = int(context.args[0])
      if ref_id != user_id and ref_id in KULLANICILAR:
        if not KULLANICILAR[user_id]["davet_edildi"]:
          KULLANICILAR[user_id]["davet_edildi"] = True
          KULLANICILAR[ref_id]["carpipuan"] = min(
              40000.0, KULLANICILAR[ref_id]["carpipuan"] + 5.0
          )
          try:
            await context.bot.send_message(
                chat_id=ref_id,
                text=(
                    "🎉 Tebrikler reis! Davetin sayesinde hesabına +5"
                    " carpipuan eklendi!"
                ),
            )
          except:
            pass
    except ValueError:
      pass

  stok_adet = len(stok_oku())
  user_data = KULLANICILAR[user_id]
  user_data["kod_bekleniyor"] = False

  from telegram import InlineKeyboardButton, InlineKeyboardMarkup

  keyboard = [
      [
          InlineKeyboardButton(
              "📦 Hesap Satın Al (15 carpipuan)", callback_data="hesap_al_puan"
          )
      ],
      [
          InlineKeyboardButton(
              "⭐ Gerçek Yıldız ile Hesap Al (100 Yıldız)",
              callback_data="yildiz_hesap",
          )
      ],
      [
          InlineKeyboardButton(
              "⭐ Gerçek Yıldız ile carpipuan Al (50 - 40K)",
              callback_data="carpipuan_menu",
          )
      ],
      [
          InlineKeyboardButton(
              "🎁 Promosyon Kodu Gir (0.3 - 2 Puan)",
              callback_data="promo_gir_menu",
          )
      ],
      [
          InlineKeyboardButton(
              "🎁 Günlük Ödül Al (+10 carpipuan)", callback_data="gunluk_odul"
          )
      ],
      [
          InlineKeyboardButton(
              "👥 Arkadaşını Davet Et (+5 carpipuan)",
              callback_data="davet_et",
          )
      ],
      [
          InlineKeyboardButton(
              "👤 Profilim & Sana Özel Kodum", callback_data="profil"
          )
      ],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  await update.message.reply_text(
      "🚀 CPM1 Hesap Mağazasına Hoş Geldin!\n\n"
      f"📦 Güncel Stok: {stok_adet} adet hesap\n"
      f"🏆 carpipuanın: {user_data['carpipuan']} carpipuan\n"
      f"🎁 Size Özel Hediye Kodunuz: `{user_data['hediye_kodu']}`\n"
      "(15 carpipuan = 1 Ücretsiz Hesap)\n\n"
      "Aşağıdaki menüden işlem seçebilirsin:",
      reply_markup=reply_markup,
      parse_mode="Markdown",
  )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  user_id = query.from_user.id

  if user_id not in KULLANICILAR:
    KULLANICILAR[user_id] = {
        "carpipuan": random.choice([0.0, 0.5, 0.8, 1.0, 2.0]),
        "son_gunluk": 0,
        "hediye_kodu": f"CPM-{user_id}-{random.randint(1000, 9999)}",
        "kod_bekleniyor": False,
    }
  user_data = KULLANICILAR[user_id]
  stok_adet = len(stok_oku())
  user_data["kod_bekleniyor"] = False

  from telegram import InlineKeyboardButton, InlineKeyboardMarkup

  # 1. 15 CARPİPUAN İLE HESAP AL
  if query.data == "hesap_al_puan":
    if user_data["carpipuan"] < 15.0:
      await query.edit_message_text(
          "❌ Yetersiz carpipuan! Hesap almak için en az 15 puana ihtiyacın"
          f" var.\n\nMevcut carpipuanın: {user_data['carpipuan']}"
      )
      return

    if stok_adet < 1:
      await query.edit_message_text(
          "❌ Maalesef şu an stokta hiç hesap kalmamış reis!"
      )
      return

    verilenler = stok_dusur_ve_ver(1)
    if verilenler:
      user_data["carpipuan"] -= 15.0
      await query.edit_message_text(
          f"✅ 15 carpipuan harcandı ve hesap verildi!\n\n🔑 Bilgiler:\n`{verilenler[0]}`\n\n"
          f"Kalan carpipuanın: {user_data['carpipuan']}\nGüle güle kullan"
          " reis! 🎮",
          parse_mode="Markdown",
      )
    else:
      await query.edit_message_text("❌ Stok hatası oluştu.")

  # 2. GERÇEK YILDIZ İLE DOĞRUDAN HESAP SATIN AL (TELEGRAM STARS INVOICE)
  elif query.data == "yildiz_hesap":
    if stok_adet < 1:
      await query.edit_message_text("❌ Stokta hiç hesap kalmamış!")
      return

    title = "CPM1 Hesap Satın Alımı"
    description = "1 Adet CPM1 Oyuncu Hesabı (Gerçek Telegram Yıldızı ile)"
    payload = "hesap_satin_al_payload"
    currency = "XTR"  # Telegram Stars para birimi kodu
    prices = [LabeledPrice("CPM1 Hesap", 100)]  # 100 Yıldız

    await context.bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",  # Telegram Stars için boş bırakılır
        currency=currency,
        prices=prices,
    )
    await query.edit_message_text(
        "⭐ Gerçek Telegram Yıldızı ile ödeme faturası oluşturuldu!"
        " Lütfen yukarıdaki ödeme butonuna basarak 100 ⭐ ödemeyi"
        " tamamla."
    )

  # 3. CARPİPUAN PAKETLERİ MENÜSÜ
  elif query.data == "carpipuan_menu":
    keyboard = [
        [
            InlineKeyboardButton(
                "50 carpipuan (⭐ 45 Yıldız)", callback_data="paket_50"
            ),
            InlineKeyboardButton(
                "100 carpipuan (⭐ 80 Yıldız)", callback_data="paket_100"
            ),
        ],
        [
            InlineKeyboardButton(
                "400 carpipuan (⭐ 280 Yıldız)", callback_data="paket_400"
            ),
            InlineKeyboardButton(
                "500 carpipuan (⭐ 340 Yıldız)", callback_data="paket_500"
            ),
        ],
        [
            InlineKeyboardButton(
                "1,000 carpipuan (⭐ 600 Yıldız)", callback_data="paket_1000"
            ),
            InlineKeyboardButton(
                "5,000 carpipuan (⭐ 2,750 Yıldız)", callback_data="paket_5000"
            ),
        ],
        [
            InlineKeyboardButton(
                "10,000 carpipuan (⭐ 5,200 Yıldız)",
                callback_data="paket_10000",
            ),
            InlineKeyboardButton(
                "20,000 carpipuan (⭐ 11,000 Yıldız)",
                callback_data="paket_20000",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔥 40,000 carpipuan MAX (⭐ 21,500 Yıldız)",
                callback_data="paket_40000",
            )
        ],
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "⭐ **Gerçek Telegram Yıldızı ile carpıpuan Satın Al**\n\n"
        f"Mevcut carpipuanın: {user_data['carpipuan']} / 40,000\n\n"
        "İstediğin paket için gerçek yıldız faturası oluştur:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

  elif query.data.startswith("paket_"):
    puan_miktari = int(query.data.split("_")[1])
    maliyetler = {
        50: 45,
        100: 80,
        400: 280,
        500: 340,
        1000: 600,
        5000: 2750,
        10000: 5200,
        20000: 11000,
        40000: 21500,
    }
    gerekli_yildiz = maliyetler.get(puan_miktari, 50)

    if user_data["carpipuan"] >= 40000.0:
      await query.edit_message_text(
          "🔥 Zaten maksimum carpipuan sınırına (40.000) ulaştın reis!"
      )
      return

    title = f"{puan_miktari:,} carpipuan Paketi"
    description = (
        f"Hesabına {puan_miktari:,} carpipuan yüklemesi (Telegram Yıldızı ile)"
    )
    payload = f"puan_yukle_{puan_miktari}"
    currency = "XTR"
    prices = [LabeledPrice(f"{puan_miktari} Puan", gerekli_yildiz)]

    await context.bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",
        currency=currency,
        prices=prices,
    )
    await query.edit_message_text(
        f"⭐ {puan_miktari:,} carpipuan için {gerekli_yildiz:,} Yıldız"
        " faturası gönderildi! Lütfen yukarıdan ödemeyi gerçekleştir."
    )

  # 4. PROMOSYON KODU GİR MENÜSÜ
  elif query.data == "promo_gir_menu":
    user_data["kod_bekleniyor"] = True
    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🎁 **Promosyon Kodu Girişi**\n\n"
        "Lütfen sohbet penceresine **Promosyon Kodunu** yazarak gönder.\n\n"
        "✨ *Kod başarıyla girildiğinde sistem sana rastgele **0.3 ile 2.0"
        " arası** sürpriz carpipuan kazandıracak!*",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

  # 5. GÜNLÜK ÖDÜL AL
  elif query.data == "gunluk_odul":
    simdiki_zaman = time.time()
    gecen_sure = simdiki_zaman - user_data["son_gunluk"]

    if gecen_sure < 86400:
      kalan_dakika = int((86400 - gecen_sure) / 60)
      kalan_saat = kalan_dakika // 60
      kalan_dak = kalan_dakika % 60
      await query.edit_message_text(
          "⏳ Günlük ödülünü zaten almışsın reis!\n"
          f"Tekrar alabilmek için kalan süre: **{kalan_saat} saat {kalan_dak}"
          " dakika**",
          parse_mode="Markdown",
      )
      return

    user_data["son_gunluk"] = simdiki_zaman
    user_data["carpipuan"] = min(40000.0, user_data["carpipuan"] + 10.0)

    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🎁 Günlük Ödül Başarıyla Toplandı!\n\n"
        "Hesabına **+10 carpipuan** eklendi! 🚀\n\n"
        f"💰 Toplam carpipuanın: {user_data['carpipuan']}",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

  # 6. ARKADAŞINI DAVET ET
  elif query.data == "davet_et":
    bot_username = context.bot.username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "👥 Arkadaşını Davet Et & carpipuan Kazan!\n\n"
        "Davet ettiğin her arkadaşın başına hesabına **+5 carpipuan**"
        " eklenir.\n\n🔗 Kişisel Davet Linkin:\n`{ref_link}`",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

  # 7. PROFİL
  elif query.data == "profil":
    bot_username = context.bot.username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"👤 **Profil ve Sana Özel Bilgiler:**\n\n"
        f"🆔 ID: {user_id}\n"
        f"🎁 Size Özel Hediye Kodunuz:\n`{user_data['hediye_kodu']}`\n\n"
        f"🏆 carpipuan: {user_data['carpipuan']}\n"
        f"📦 Mağaza Stok: {stok_adet} adet\n\n"
        f"🔗 Davet Linkin:\n`{ref_link}`",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

  # 8. ANA MENÜ
  elif query.data == "ana_menu":
    keyboard = [
        [
            InlineKeyboardButton(
                "📦 Hesap Satın Al (15 carpipuan)", callback_data="hesap_al_puan"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ Gerçek Yıldız ile Hesap Al (100 Yıldız)",
                callback_data="yildiz_hesap",
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ Gerçek Yıldız ile carpipuan Al (50 - 40K)",
                callback_data="carpipuan_menu",
            )
        ],
        [
            InlineKeyboardButton(
                "🎁 Promosyon Kodu Gir (0.3 - 2 Puan)",
                callback_data="promo_gir_menu",
            )
        ],
        [
            InlineKeyboardButton(
                "🎁 Günlük Ödül Al (+10 carpipuan)", callback_data="gunluk_odul"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 Arkadaşını Davet Et (+5 carpipuan)",
                callback_data="davet_et",
            )
        ],
        [
            InlineKeyboardButton(
                "👤 Profilim & Sana Özel Kodum", callback_data="profil"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🚀 CPM1 Hesap Mağazasına Hoş Geldin!\n\n"
        f"📦 Güncel Stok: {stok_adet} adet hesap\n"
        f"🏆 carpipuanın: {user_data['carpipuan']} carpipuan\n"
        f"🎁 Size Özel Hediye Kodunuz: `{user_data['hediye_kodu']}`\n"
        "(15 carpipuan = 1 Ücretsiz Hesap)\n\n"
        "Aşağıdaki menüden işlem seçebilirsin:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


# --- TELEGRAM YILDIZI ÖDEME ONAY MEKANİZMASI (PRE-CHECKOUT) ---
async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.pre_checkout_query
  # Kullanıcı ödeme yapmaya bastığında Telegram onay sorar, hemen onay veriyoruz
  await query.answer(ok=True)


# --- ÖDEME BAŞARIYLA TAMAMLANDIKTAN SONRA ÜRÜN TESLİMİ ---
async def successful_payment_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  payment = update.message.successful_payment
  payload = payment.invoice_payload
  user_id = update.effective_user.id

  if user_id not in KULLANICILAR:
    KULLANICILAR[user_id] = {
        "carpipuan": 1.0,
        "son_gunluk": 0,
        "hediye_kodu": f"CPM-{user_id}-{random.randint(1000, 9999)}",
        "kod_bekleniyor": False,
    }

  user_data = KULLANICILAR[user_id]

  if payload == "hesap_satin_al_payload":
    verilenler = stok_dusur_ve_ver(1)
    if verilenler:
      await update.message.reply_text(
          "⭐ **Gerçek Telegram Yıldızı ile Ödeme Başarılı!**\n\n"
          f"🔑 Satın Aldığın Hesap Bilgileri:\n`{verilenler[0]}`\n\n"
          "Güle güle kullan reis! 🎮",
          parse_mode="Markdown",
      )
    else:
      await update.message.reply_text(
          "❌ Ödeme alındı fakat maalesef stok bitti! Lütfen yöneticiye"
          " bildir."
      )

  elif payload.startswith("puan_yukle_"):
    puan_miktari = int(payload.split("_")[2])
    user_data["carpipuan"] = min(
        40000.0, user_data["carpipuan"] + puan_miktari
    )
    await update.message.reply_text(
        "⭐ **Gerçek Telegram Yıldızı ile Ödeme Başarılı!**\n\n"
        f"🎉 Hesabına **+{puan_miktari:,} carpipuan** eklendi! 🚀\n"
        f"💰 Güncel carpipuanın: {user_data['carpipuan']} / 40,000",
        parse_mode="Markdown",
    )


# --- MESAJ YÖNETİCİSİ (PROMOSYON KODU KONTROLÜ) ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  text = update.message.text.strip()

  if user_id not in KULLANICILAR:
    KULLANICILAR[user_id] = {
        "carpipuan": 1.0,
        "son_gunluk": 0,
        "hediye_kodu": f"CPM-{user_id}-{random.randint(1000, 9999)}",
        "kod_bekleniyor": False,
    }

  user_data = KULLANICILAR[user_id]

  if user_data.get("kod_bekleniyor", False):
    user_data["kod_bekleniyor"] = False

    if text in KULLANILAN_KODLAR:
      await update.message.reply_text(
          "❌ Bu promosyon kodu daha önce kullanılmış veya geçersiz!"
      )
      return

    # 0.3'ten başlayıp maksimum 2.0'ye kadar rastgele ondalıklı carpipuan belirleme
    mumkun_puanlar = [0.3, 0.5, 0.7, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0]
    kazanilan_puan = random.choice(mumkun_puanlar)

    KULLANILAN_KODLAR.add(text)
    user_data["carpipuan"] = min(40000.0, user_data["carpipuan"] + kazanilan_puan)

    await update.message.reply_text(
        f"🎉 **Tebrikler Reis! Kod Başarıyla Onaylandı!**\n\n"
        f"🎁 Promosyon Ödülün: **+{kazanilan_puan} carpipuan** hesabına eklendi! 🚀\n"
        f"💰 Güncel carpipuanın: {user_data['carpipuan']}",
        parse_mode="Markdown",
    )
  else:
    await update.message.reply_text(
        "Botu kullanmak için /start komutunu gönderebilir veya menü"
        " butonlarını kullanabilirsin reis! 🎮"
    )


def main():
  BOT_TOKEN = os.environ.get(
      "BOT_TOKEN", "8962445060:AAEatnjtKUW66d--dFVdjgGnRqLMN_P7o44"
  )

  application = ApplicationBuilder().token(BOT_TOKEN).build()

  application.add_handler(CommandHandler("start", start))
  application.add_handler(CallbackQueryHandler(button_handler))
  application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
  application.add_handler(
      MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler)
  )
  application.add_handler(
      MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
  )

  print("Gerçek Telegram Yıldızı Ödeme Altyapılı Bot Çalışıyor...")
  application.run_polling()


if __name__ == "__main__":
  t = threading.Thread(target=run_web)
  t.daemon = True
  t.start()

  main()
    
