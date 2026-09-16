import json
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

# Senin Telegram ID'n
ADMIN_IDS = [8520025523]


@app.route("/")
def home():
  return "Cpm1 Hesap Satis Botu Aktif ve Calisiyor! 🚀"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


# --- VERİTABANI YÖNETİMİ (JSON) ---
DB_FILE = "veritabani.json"


def veri_yukle():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {
          "users": {},
          "giveaway": {"active": False, "participants": []},
          "waitlist": [],
          "banned": [],
      }
  return {
      "users": {},
      "giveaway": {"active": False, "participants": []},
      "waitlist": [],
      "banned": [],
  }


def veri_kaydet():
  try:
    with open(DB_FILE, "w", encoding="utf-8") as f:
      json.dump(DB_DATA, f, ensure_ascii=False, indent=4)
  except Exception:
    pass


DB_DATA = veri_yukle()
if not isinstance(DB_DATA, dict) or "users" not in DB_DATA:
  DB_DATA = {
      "users": DB_DATA if isinstance(DB_DATA, dict) else {},
      "giveaway": {"active": False, "participants": []},
      "waitlist": [],
      "banned": [],
  }

KULLANICILAR = DB_DATA["users"]


def stok_oku():
  if not os.path.exists("stok.txt"):
    with open("stok.txt", "w", encoding="utf-8") as f:
      f.write("")
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


def get_dynamic_price(base_price: int) -> int:
  stock = stok_oku()
  if len(stock) < 5:
    return int(base_price * 1.2)
  return base_price


def get_ana_menu_keyboard(stok_adet, user_data=None):
  secilen_adet = user_data.get("hesap_adet", 1) if user_data else 1
  base_puan = secilen_adet * 50
  toplam_puan = get_dynamic_price(base_puan)

  yildiz_adet = user_data.get("yildiz_hesap_adet", 1) if user_data else 1
  toplam_yildiz = yildiz_adet * 50

  karaborsa_uyari = " (🔥 Karaborsa!)" if stok_adet < 5 and stok_adet > 0 else ""

  keyboard = [
      [
          InlineKeyboardButton("➖", callback_data="h_az"),
          InlineKeyboardButton(
              f"📦 {secilen_adet} Adet VIP FULL+FULL HESAP ({toplam_puan} Puan){karaborsa_uyari}",
              callback_data="bos_bilgi",
          ),
          InlineKeyboardButton("➕", callback_data="h_art"),
      ],
      [
          InlineKeyboardButton(
              f"💳 Seçilenleri carpipuan ile Al ({toplam_puan} Puan)",
              callback_data="hp_al",
          )
      ],
      [
          InlineKeyboardButton("➖", callback_data="y_az"),
          InlineKeyboardButton(
              f"⭐ {yildiz_adet} Adet VIP FULL+FULL HESAP ({toplam_yildiz} Yıldız)",
              callback_data="bos_bilgi",
          ),
          InlineKeyboardButton("➕", callback_data="y_art"),
      ],
      [
          InlineKeyboardButton(
              f"⭐ Seçilenleri Yıldız ile Al ({toplam_yildiz} Yıldız)",
              callback_data="y_al",
          )
      ],
      [
          InlineKeyboardButton(
              "⭐ Yıldız ile carpipuan Al (Dengeli Paketler)",
              callback_data="puan_menu",
          )
      ],
      [
          InlineKeyboardButton(
              "🎁 Otomatik Çekilişe Katıl", callback_data="join_giveaway"
          )
      ],
  ]

  if user_data and not user_data.get("sifre_oyunu_kullanildi", False):
    keyboard.append([
        InlineKeyboardButton(
            "🔐 Şifreyi Çöz & Ödülü Kap (3 Yıldız)", callback_data="sifre_baslat"
        )
    ])

  if user_data and not user_data.get("promo_alindi", False):
    keyboard.append([
        InlineKeyboardButton("🎁 Bana Özel Promo Kodu Üret", callback_data="promo")
    ])

  keyboard.extend([
      [InlineKeyboardButton("🎁 Günlük Ödül Al (0.3 - 2 Puan)", callback_data="gunluk")],
      [InlineKeyboardButton("🏆 En İyiler (Liderlik)", callback_data="liderlik")],
      [
          InlineKeyboardButton(
              "👥 Arkadaşını Davet Et (+5 carpipuan)", callback_data="davet"
          )
      ],
      [InlineKeyboardButton("👤 Profilim & Bilgilerim", callback_data="profil")],
  ])

  return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  user_id_str = str(user_id)

  if user_id_str in DB_DATA.get("banned", []):
    await update.message.reply_text("❌ Bu botu kullanmanız yasaklanmıştır.")
    return

  args = context.args

  if user_id_str not in KULLANICILAR:
    KULLANICILAR[user_id_str] = {
        "carpipuan": 0.0,
        "son_gunluk": 0,
        "davet_edildi": False,
        "davet_sayisi": 0,
        "hesap_adet": 1,
        "yildiz_hesap_adet": 1,
        "promo_alindi": False,
        "sifre_oyunu_kullanildi": False,
        "beklenen_sifre": None,
        "spent": 0,
    }
    if args and args[0].startswith("ref_"):
      try:
        ref_id_str = args[0].split("_")[1]
        if ref_id_str != user_id_str and ref_id_str in KULLANICILAR:
          if not KULLANICILAR[user_id_str].get("davet_edildi", False):
            KULLANICILAR[user_id_str]["davet_edildi"] = True
            KULLANICILAR[ref_id_str]["carpipuan"] = round(
                KULLANICILAR[ref_id_str]["carpipuan"] + 5.0, 1
            )
            KULLANICILAR[ref_id_str]["davet_sayisi"] = (
                KULLANICILAR[ref_id_str].get("davet_sayisi", 0) + 1
            )
            veri_kaydet()
            try:
              await context.bot.send_message(
                  chat_id=int(ref_id_str),
                  text=(
                      "🎉 Tebrikler reis! Davet ettiğin bir kullanıcı botu başlattı"
                      " ve hesabına **+5 carpipuan** eklendi! 🚀"
                  ),
                  parse_mode="Markdown",
              )
            except Exception:
              pass
      except Exception:
        pass
    veri_kaydet()

  stok_adet = len(stok_oku())
  user_data = KULLANICILAR[user_id_str]

  bot_info = await context.bot.get_me()
  context.bot_data["username"] = bot_info.username

  await update.message.reply_text(
      "🚀 CPM1 Hesap Mağazasına & Otomasyon İmparatorluğuna Hoş Geldin!\n\n"
      f"📦 Güncel Stok: {stok_adet} adet hesap\n"
      f"🏆 carpipuanın: +{user_data['carpipuan']} carpipuan\n\n"
      "Aşağıdaki menüden işlem seçebilirsin:",
      reply_markup=get_ana_menu_keyboard(stok_adet, user_data),
      parse_mode="Markdown",
  )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  if user_id not in ADMIN_IDS:
    await update.message.reply_text("❌ Bu komutu kullanmaya yetkin yok reis!")
    return

  stok_adet = len(stok_oku())
  toplam_uye = len(KULLANICILAR)

  keyboard = [
      [InlineKeyboardButton("📦 Stok Durumu & Bilgi", callback_data="admin_stok")],
      [InlineKeyboardButton("📢 Tüm Kullanıcılara Duyuru At", callback_data="admin_duyuru")],
      [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="ana_menu")],
  ]
  await update.message.reply_text(
      "👑 **Admin Paneline Hoş Geldin Reis!**\n\n"
      f"👥 Toplam Üye: `{toplam_uye}`\n"
      f"📦 Güncel Stok: `{stok_adet}`\n\n"
      "Yapmak istediğin işlemi seç:",
      reply_markup=InlineKeyboardMarkup(keyboard),
      parse_mode="Markdown",
  )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  user_id_str = str(query.from_user.id)
  user_id = query.from_user.id

  if user_id_str in DB_DATA.get("banned", []):
    await query.answer("❌ Engellendiğiniz için işlem yapamazsınız.", show_alert=True)
    return

  if user_id_str not in KULLANICILAR:
    KULLANICILAR[user_id_str] = {
        "carpipuan": 0.0,
        "son_gunluk": 0,
        "davet_edildi": False,
        "davet_sayisi": 0,
        "hesap_adet": 1,
        "yildiz_hesap_adet": 1,
        "promo_alindi": False,
        "sifre_oyunu_kullanildi": False,
        "beklenen_sifre": None,
        "spent": 0,
    }
    veri_kaydet()

  user_data = KULLANICILAR[user_id_str]
  stok_adet = len(stok_oku())

  if query.data == "bos_bilgi":
    await query.answer()
    return

  elif query.data == "admin_stok":
    if user_id not in ADMIN_IDS:
      await query.answer("Yetkin yok!", show_alert=True)
      return
    await query.answer()
    await query.edit_message_text(
        f"📦 **Stok Bilgisi:**\nŞu anda stokta toplam **{stok_adet}** adet hesap bulunmaktadır.\n\nStok eklemek için sunucuya `stok.txt` dosyası üzerinden alt alta `kadi:sifre` formatında ekleme yapabilirsin.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menü", callback_data="ana_menu")]]),
        parse_mode="Markdown",
    )

  elif query.data == "admin_duyuru":
    if user_id not in ADMIN_IDS:
      await query.answer("Yetkin yok!", show_alert=True)
      return
    context.user_data["beklenen_admin_islem"] = "duyuru"
    await query.answer()
    await query.edit_message_text(
        "📢 Lütfen kullanıcılara göndermek istediğiniz duyuru mesajını **sohbete yazı olarak gönderin:**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 İptal", callback_data="ana_menu")]]),
    )

  elif query.data == "join_giveaway":
    if DB_DATA["giveaway"].get("active", False):
      if user_id_str not in DB_DATA["giveaway"]["participants"]:
        DB_DATA["giveaway"]["participants"].append(user_id_str)
        veri_kaydet()
        await query.answer("✅ Çekilişe başarıyla katıldın!", show_alert=True)
      else:
        await query.answer("⚠️ Zaten bu çekilişe katılmış durumdasın.", show_alert=True)
    else:
      await query.answer("❌ Şu anda aktif bir çekiliş bulunmuyor.", show_alert=True)
    return

  elif query.data == "h_art":
    await query.answer()
    if user_data["hesap_adet"] < max(1, stok_adet if stok_adet > 0 else 1):
      user_data["hesap_adet"] += 1
      veri_kaydet()
    try:
      await query.edit_message_reply_markup(
          reply_markup=get_ana_menu_keyboard(stok_adet, user_data)
      )
    except Exception:
      pass

  elif query.data == "h_az":
    await query.answer()
    if user_data["hesap_adet"] > 1:
      user_data["hesap_adet"] -= 1
      veri_kaydet()
    try:
      await query.edit_message_reply_markup(
          reply_markup=get_ana_menu_keyboard(stok_adet, user_data)
      )
    except Exception:
      pass

  elif query.data == "y_art":
    await query.answer()
    if user_data["yildiz_hesap_adet"] < max(1, stok_adet if stok_adet > 0 else 1):
      user_data["yildiz_hesap_adet"] += 1
      veri_kaydet()
    try:
      await query.edit_message_reply_markup(
          reply_markup=get_ana_menu_keyboard(stok_adet, user_data)
      )
    except Exception:
      pass

  elif query.data == "y_az":
    await query.answer()
    if user_data["yildiz_hesap_adet"] > 1:
      user_data["yildiz_hesap_adet"] -= 1
      veri_kaydet()
    try:
      await query.edit_message_reply_markup(
          reply_markup=get_ana_menu_keyboard(stok_adet, user_data)
      )
    except Exception:
      pass

  elif query.data == "hp_al":
    adet = user_data.get("hesap_adet", 1)
    base_puan = adet * 50.0
    gerekli_puan = get_dynamic_price(int(base_puan))

    if user_data["carpipuan"] < gerekli_puan:
      await query.answer(
          f"❌ Yetersiz carpipuan! {gerekli_puan} puan lazım. (Mevcut: +{user_data['carpipuan']})",
          show_alert=True,
      )
      return

    if stok_adet < adet:
      if user_id_str not in DB_DATA["waitlist"]:
        DB_DATA["waitlist"].append(user_id_str)
        veri_kaydet()
      await query.answer(
          "⚠️ Stoklar tükenmiştir! Otomatik bekleme listesine (Waitlist) eklendin. Stok gelince haber verilecek.",
          show_alert=True,
      )
      return

    verilenler = stok_dusur_ve_ver(adet)
    if verilenler:
      await query.answer()
      cashback = int(gerekli_puan * 0.10)
      user_data["carpipuan"] = round(user_data["carpipuan"] - gerekli_puan + cashback, 1)
      user_data["spent"] = user_data.get("spent", 0) + int(gerekli_puan)
      veri_kaydet()
      
      hesaplar_metni = "\n".join([f"`{h}`" for h in verilenler])
      keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]]
      try:
        await query.edit_message_text(
            f"✅ {adet} Adet VIP FULL+FULL HESAP Başarıyla Verildi! (-{gerekli_puan} Puan)\n\n"
            f"✨ **Cashback İadesi:** +{cashback} Puan hesabına geri yüklendi!\n\n"
            f"🔑 Bilgiler:\n{hesaplar_metni}\n\n💰 Kalan Puanın: +{user_data['carpipuan']}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
      except Exception:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ {adet} Adet VIP FULL+FULL HESAP Başarıyla Verildi! (-{gerekli_puan} Puan)\n\n🔑 Bilgiler:\n{hesaplar_metni}\n\n💰 Kalan Puanın: +{user_data['carpipuan']}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
      await query.answer("❌ Stok hatası oluştu!", show_alert=True)

  elif query.data == "sifre_baslat":
    await query.answer()
    if user_data.get("sifre_oyunu_kullanildi", False):
      await query.answer(
          "❌ Bu şifre çözme hakkını zaten kullandın reis!", show_alert=True
      )
      return

    user_data["sifre_oyunu_kullanildi"] = True
    veri_kaydet()
    try:
      await query.edit_message_reply_markup(
          reply_markup=get_ana_menu_keyboard(stok_adet, user_data)
      )
    except Exception:
      pass

    await context.bot.send_invoice(
        chat_id=user_id,
        title="🔐 6 Haneli Şifre Çözme Oyunu",
        description="3 Yıldız öde, şifreyi al ve sohbete yazarak çöz!",
        payload="sifre_oyunu_3_yildiz",
        currency="XTR",
        prices=[LabeledPrice("Şifre Çözme Hakkı", 3)],
    )

  elif query.data == "promo":
    await query.answer()
    if not user_data["promo_alindi"]:
      rastgele_kod = "CPM-" + "".join(
          random.choices(string.ascii_uppercase + string.digits, k=6)
      )
      kazanilan_odul = round(random.uniform(1.0, 5.0), 1)

      user_data["promo_alindi"] = True
      user_data["carpipuan"] = round(user_data["carpipuan"] + kazanilan_odul, 1)
      veri_kaydet()

      keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]]
      await query.edit_message_text(
          f"🎁 Sana Özel Promo Kodu Üretildi!\n\n🔑 Kodun: `{rastgele_kod}`\n✨ Hediyen Hesaba Eklendi: **+{kazanilan_odul} Puan**\n💰 Toplam Puanın: +{user_data['carpipuan']}",
          reply_markup=InlineKeyboardMarkup(keyboard),
          parse_mode="Markdown",
      )
    else:
      await query.answer(
          "❌ Sen bu promosyon hakkını zaten kullandın reis!", show_alert=True
      )

  elif query.data == "y_al":
    await query.answer()
    adet = user_data.get("yildiz_hesap_adet", 1)
    toplam_fiyat = adet * 50
    if stok_adet < adet:
      await query.answer("❌ Stokta o kadar hesap yok reis!", show_alert=True)
      return

    await context.bot.send_invoice(
        chat_id=user_id,
        title=f"⭐ Yıldız ile {adet} Adet Hesap Al",
        description=f"{adet} Adet VIP FULL+FULL HESAP ({toplam_fiyat} Yıldız)",
        payload=f"hesap_coklu_{adet}",
        currency="XTR",
        prices=[LabeledPrice(f"{adet} Adet Hesap", toplam_fiyat)],
    )

  elif query.data == "puan_menu":
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("⭐ 50 Yıldız ➔ 50 Puan", callback_data="p_yildiz_50")],
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
    await query.answer()
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

  elif query.data == "gunluk":
    await query.answer()
    simdi = time.time()
    if simdi - user_data["son_gunluk"] < 86400:
      keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]]
      await query.edit_message_text(
          "⏳ Günlük ödülünü zaten almışsın reis, yarın tekrar gel!",
          reply_markup=InlineKeyboardMarkup(keyboard),
      )
      return

    user_data["son_gunluk"] = simdi
    kazanilan = round(random.uniform(0.3, 2.0), 1)
    user_data["carpipuan"] = round(user_data["carpipuan"] + kazanilan, 1)
    veri_kaydet()

    keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]]
    await query.edit_message_text(
        f"🎁 Günlük Ödül: **+{kazanilan} Puan** eklendi!\n💰 Toplam: +{user_data['carpipuan']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif query.data == "davet":
    await query.answer()
    bot_username = context.bot_data.get("username", "BotKullaniciAdin")
    davet_linki = f"https://t.me/{bot_username}?start=ref_{user_id}"
    davet_sayisi = user_data.get("davet_sayisi", 0)

    keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]]
    await query.edit_message_text(
        "👥 **Arkadaşını Davet Et Kazan!**\n\n"
        "Aşağıdaki sana özel davet linkini arkadaşlarınla paylaş. "
        "Linkinle gelen her arkadaşın başına **+5 carpipuan** kazanırsın! 🚀\n\n"
        f"🔗 **Senin Davet Linkin:**\n`{davet_linki}`\n\n"
        f"📊 Toplam Davet Ettiğin Kişi: **{davet_sayisi}**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif query.data == "liderlik":
    await query.answer()
    sirali = sorted(
        KULLANICILAR.items(), key=lambda x: x[1]["carpipuan"], reverse=True
    )[:10]
    metin = "🏆 **En İyi 10 Liderlik Tablosu**\n\n"
    for sira, (uid, udata) in enumerate(sirali, 1):
      metin += f"{sira}. Kullan
