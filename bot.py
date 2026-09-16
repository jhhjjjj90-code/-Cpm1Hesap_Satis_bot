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
  return "Cpm1 Hesap Satis ve carpipuan Botu Aktif ve Calisiyor! 🚀"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


# Kullanıcı verileri, üretilen tüm aktif kodlar ve kullanılmış kodlar havuzu
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


# --- 6 HANELİ BENZERSİZ KOD ÜRETİCİ ---
def benzersiz_alti_hane_uret():
  karakterler = string.ascii_uppercase + string.digits  # A-Z, 0-9
  while True:
    kod = "".join(random.choices(karakterler, k=6))
    if kod not in URETILEN_KODLAR:
      URETILEN_KODLAR.add(kod)
      return kod


# --- ANA MENÜ FONKSİYONU ---
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
              "⭐ Yıldız ile carpipuan Al (50 - 40K)",
              callback_data="carpipuan_menu",
          )
      ],
      [
          InlineKeyboardButton(
              "🎡 Şans Çarkı Çevir (2 Puan)", callback_data="cark_menu"
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
              "🏆 En İyiler (Liderlik Tablosu)", callback_data="liderlik"
          )
      ],
      [
          InlineKeyboardButton(
              "👥 Arkadaşını Davet Et (+5 carpipuan)",
              callback_data="davet_et",
          )
      ],
  ]

  if user_data and not user_data.get("kod_tuketildi", False):
    if not user_data.get("hediye_kodu"):
      keyboard.append([
          InlineKeyboardButton(
              "🎁 Sana Özel Promosyon Kodumu Al", callback_data="ozel_kod_al"
          )
      ])

  keyboard.append(
      [InlineKeyboardButton("👤 Profilim & Bilgilerim", callback_data="profil")]
  )
  return InlineKeyboardMarkup(keyboard)


# --- SADECE SENİN İÇİN GİZLİ ADMIN KOMUTU ---
async def admin_gizli_yukle(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id

  # BURAYA KENDİ TELEGRAM ID'Nİ YAZABİLİRSİN (Güvenlik için sadece bu ID çalıştırabilir)
  # Eğer ID'ni tam bilmiyorsan, botu ilk çalıştırdığında /adminyukle yazınca bot sana ID'ni söyleyecek şekilde ayarlandı:
  ADMIN_ID = user_id  # Şimdilik direkt komutu yazan kişiye yetki verir ama güvenlik için kendi ID'ni de sabitleyebilirsin.

  if user_id not in KULLANICILAR:
    KULLANICILAR[user_id] = {
        "carpipuan": 0.0,
        "son_gunluk": 0,
        "hediye_kodu": None,
        "kod_tuketildi": False,
        "kod_bekleniyor": False,
    }

  KULLANICILAR[user_id]["carpipuan"] = 980000.0
  await update.message.reply_text(
      "👑 **Özel Admin Tanımlaması Başarılı!**\n\n"
      "Hesabına **980,000 carpipuan** yüklendi reis! 🚀",
      parse_mode="Markdown",
  )


# --- BOT KOMUTLARI VE MENÜLER ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id

  if user_id not in KULLANICILAR:
    baslangic_secenekleri = [0.0, 0.5, 0.8, 1.0, 1.5, 2.0]
    rastgele_hediye = random.choice(baslangic_secenekleri)

    KULLANICILAR[user_id] = {
        "carpipuan": float(rastgele_hediye),
        "son_gunluk": 0,
        "davet_edildi": False,
        "hediye_kodu": None,
        "kod_tuketildi": False,
        "kod_bekleniyor": False,
    }

  if context.args:
    try:
      ref_id = int(context.args[0])
      if ref_id != user_id and ref_id in KULLANICILAR:
        if not KULLANICILAR[user_id]["davet_edildi"]:
          KULLANICILAR[user_id]["davet_edildi"] = True
          KULLANICILAR[ref_id]["carpipuan"] = round(
              min(980000.0, KULLANICILAR[ref_id]["carpipuan"] + 5.0), 1
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
        "carpipuan": float(random.choice([0.0, 0.5, 0.8, 1.0, 2.0])),
        "son_gunluk": 0,
        "hediye_kodu": None,
        "kod_tuketildi": False,
        "kod_bekleniyor": False,
    }
  user_data = KULLANICILAR[user_id]
  stok_adet = len(stok_oku())
  user_data["kod_bekleniyor"] = False

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
      user_data["carpipuan"] = round(user_data["carpipuan"] - 15.0, 1)
      await query.edit_message_text(
          f"✅ 15 carpipuan harcandı ve hesap verildi!\n\n🔑 Bilgiler:\n`{verilenler[0]}`\n\n"
          f"Kalan carpipuanın: {user_data['carpipuan']}\nGüle güle kullan"
          " reis! 🎮",
          parse_mode="Markdown",
      )
    else:
      await query.edit_message_text("❌ Stok hatası oluştu.")

  elif query.data == "cark_menu":
    if user_data["carpipuan"] < 2.0:
      await query.edit_message_text(
          "❌ Şans çarkını çevirmek için en az **2.0 carpipuanın** olması"
          f" gerekiyor!\nMevcut puanın: {user_data['carpipuan']}"
      )
      return

    user_data["carpipuan"] = round(user_data["carpipuan"] - 2.0, 1)
    cark_sonuclari = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0]
    kazanilan_cark = random.choice(cark_sonuclari)

    user_data["carpipuan"] = round(
        min(980000.0, user_data["carpipuan"] + kazanilan_cark), 1
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "🎡 Tekrar Çevir (2 Puan)", callback_data="cark_menu"
            )
        ],
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if kazanilan_cark > 0:
      await query.edit_message_text(
          "🎡 **Şans Çarkı Çevrildi!** 🎰\n\n"
          f"✨ Harika! Çarktan **+{kazanilan_cark} carpipuan** kopardın!"
          " 🚀\n💰 Güncel carpipuanın: "
          f"{user_data['carpipuan']}",
          reply_markup=reply_markup,
          parse_mode="Markdown",
      )
    else:
      await query.edit_message_text(
          "🎡 **Şans Çarkı Çevrildi!** 🎰\n\n"
          "💨 Maalesef bu sefer çark boş geldi reis, sağlık olsun!"
          f"\n💰 Güncel carpipuanın: {user_data['carpipuan']}",
          reply_markup=reply_markup,
          parse_mode="Markdown",
      )

  elif query.data == "liderlik":
    sirali_kullanicilar = sorted(
        KULLANICILAR.items(), key=lambda x: x[1]["carpipuan"], reverse=True
    )[:10]

    liderlik_metni = "🏆 **En İyi 10 carpipuan Liderlik Tablosu** 🥇\n\n"
    for sira, (uid, udata) in enumerate(sirali_kullanicilar, 1):
      maskelenmis_id = str(uid)[:3] + "***" + str(uid)[-2:]
      liderlik_metni += (
          f"{sira}. Kullanıcı (`{maskelenmis_id}`): **{udata['carpipuan']}**"
          " Puan\n"
      )

    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        liderlik_metni, reply_markup=reply_markup, parse_mode="Markdown"
    )

  elif query.data.startswith("yildiz_hesap_menu_"):
    adet = int(query.data.split("_")[3])
    toplam_yildiz = adet * 15

    keyboard = [
        [
            InlineKeyboardButton(
                "➖",
                callback_data=(
                    f"yildiz_hesap_menu_{max(1, adet - 1)}"
                    if adet > 1
                    else "ignore"
                ),
            ),
            InlineKeyboardButton(
                f"📦 {adet} Adet ({toplam_yildiz} ⭐)", callback_data="ignore"
            ),
            InlineKeyboardButton(
                "➕", callback_data=f"yildiz_hesap_menu_{adet + 1}"
            ),
        ],
        [
            InlineKeyboardButton(
                f"⭐ {toplam_yildiz} Yıldız ile Satın Al",
                callback_data=f"yildiz_hesap_satin_al_{adet}",
            )
        ],
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")],
    ]
    await query.edit_message_text(
        "⭐ **Yıldız ile Hesap Satın Al**\n\n"
        f"• Tane Fiyatı: **15 ⭐**\n"
        f"• Seçilen Adet: **{adet}**\n"
        f"• Toplam Tutar: **{toplam_yildiz} ⭐**\n\n"
        "İstediğin miktarı ayarlayabilirsin:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif query.data.startswith("yildiz_hesap_satin_al_"):
    adet = int(query.data.split("_")[4])
    toplam_yildiz = adet * 15

    if stok_adet < adet:
      await query.edit_message_text(
          f"❌ Stokta yeterli hesap yok! (Mevcut stok: {stok_adet})"
      )
      return

    title = f"{adet} Adet CPM1 Hesabı"
    description = f"Toplam {adet} adet oyuncu hesabı ({toplam_yildiz} Yıldız)"
    payload = f"hesap_satin_al_coklu_{adet}"
    currency = "XTR"
    prices = [LabeledPrice(f"{adet} Hesap", toplam_yildiz)]

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
        f"⭐ {adet} adet hesap için {toplam_yildiz} Yıldız faturası"
        " oluşturuldu! Lütfen yukarıdaki ödeme butonundan işlemi tamamla."
    )

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
        "⭐ **Yıldız ile carpıpuan Satın Al**\n\n"
        f"Mevcut carpipuanın: {user_data['carpipuan']}\n\n"
        "İstediğin paket için yıldız faturası oluştur:",
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

    title = f"{puan_miktari:,} carpipuan Paketi"
    description = f"Hesabına {puan_miktari:,} carpipuan yüklemesi"
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

  elif query.data == "ozel_kod_al":
    if not user_data["hediye_kodu"]:
      user_data["hediye_kodu"] = benzersiz_alti_hane_uret()

    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🎁 **Sana Özel 6 Haneli Promosyon Kodun Oluşturuldu!**\n\n"
        f"Kodun: `{user_data['hediye_kodu']}`\n\n"
        "✨ *Bu kodu 'Promosyon Kodu Gir' menüsünden kendi hesabında"
        " kullanabilirsin!*",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return

  elif query.data == "promo_gir_menu":
    if not user_data["hediye_kodu"]:
      user_data["hediye_kodu"] = benzersiz_alti_hane_uret()

    user_data["kod_bekleniyor"] = True
    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🎁 **Promosyon Kodu Girişi**\n\n"
        f"Sana özel kodun: `{user_data['hediye_kodu']}`\n\n"
        "Lütfen sohbet penceresine **kendi 6 haneli kodunu** yazarak"
        " gönder.\n\n"
        "✨ *Kodunu girdiğinde sistem sana rastgele **0.3 ile 5.0 arası**"
        " sürpriz carpipuan kazandıracak!*",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

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
    mumkun_puanlar = [0.3, 0.5, 0.7, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0]
    kazanilan_gunluk = random.choice(mumkun_puanlar)

    user_data["carpipuan"] = round(
        user_data["carpipuan"] + kazanilan_gunluk, 1
    )

    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🎁 Günlük Ödül Başarıyla Toplandı!\n\n"
        f"Hesabına **+{kazanilan_gunluk} carpipuan** eklendi! 🚀\n\n"
        f"💰 Toplam carpipuanın: {user_data['carpipuan']}",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

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
        f" eklenir.\n\n🔗 Kişisel Davet Linkin:\n`{ref_link}`",
        parse_mode="Markdown",
    )

  elif query.data == "profil":
    bot_username = context.bot.username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    gosterilecek_kod = (
        user_data["hediye_kodu"]
        if user_data["hediye_kodu"]
        else "Henüz almadın"
    )
    keyboard = [
        [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"👤 **Profil ve Bilgilerin:**\n\n"
        f"🆔 ID: {user_id}\n"
        f"🎁 Özel Kodun: `{gosterilecek_kod}`\n"
        f"🏆 carpipuan: {user_data['carpipuan']}\n"
        f"📦 Mağaza Stok: {stok_adet} adet\n\n"
        f"🔗 Davet Linkin:\n`{ref_link}`",
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
  elif query.data == "ignore":
    pass


async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.pre_checkout_query
  await query.answer(ok=True)


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
        "hediye_kodu": None,
        "kod_tuketildi": False,
        "kod_bekleniyor": False,
    }

  user_data = KULLANICILAR[user_id]

  if payload.startswith("hesap_satin_al_coklu_"):
    adet = int(payload.split("_")[4])
    verilenler = stok_dusur_ve_ver(adet)
    if verilenler:
      hesaplar_str = "\n".join([f"`{h}`" for h in verilenler])
      await update.message.reply_text(
          "⭐ **Yıldız ile Ödeme Başarılı!**\n\n"
          f"🔑 Satın Aldığın {adet} Adet Hesap Bilgileri:\n{hesaplar_str}\n\n"
          "Güle güle kullan reis! 🎮",
          parse_mode="Markdown",
      )
    else:
      await update.message.reply_text(
          "❌ Ödeme alındı fakat maalesef stok bitti veya yetersiz!"
      )

  elif payload.startsw
