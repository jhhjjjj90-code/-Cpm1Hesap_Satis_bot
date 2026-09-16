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

ADMIN_IDS = [8520025523]
BOT_USERNAME = "Cpm1hesap_bot"


@app.route("/")
def home():
    return "Cpm1 Hesap Satis Botu Aktif!"


def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


DB_FILE = "veritabani.json"


def veri_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}, "email_passwords": {}, "promo_codes": {}, "banned": []}


def veri_kaydet():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(DB_DATA, f, ensure_ascii=False, indent=4)
    except Exception:
        pass


DB_DATA = veri_yukle()
if not isinstance(DB_DATA, dict) or "users" not in DB_DATA:
    DB_DATA = {"users": {}, "email_passwords": {}, "promo_codes": {}, "banned": []}

if "email_passwords" not in DB_DATA:
    DB_DATA["email_passwords"] = {}

if "promo_codes" not in DB_DATA:
    DB_DATA["promo_codes"] = {}

KULLANICILAR = DB_DATA["users"]
EMAIL_PASSWORDS = DB_DATA["email_passwords"]
PROMO_CODES = DB_DATA["promo_codes"]


def stok_oku():
    if not os.path.exists("stok.txt"):
        with open("stok.txt", "w", encoding="utf-8") as f:
            f.write("")
        return []
    with open("stok.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip() and ":" in line]


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
    base_puan = secilen_adet * 15
    toplam_puan = get_dynamic_price(int(base_puan))

    yildiz_adet = user_data.get("yildiz_hesap_adet", 1) if user_data else 1
    toplam_yildiz = yildiz_adet * 15

    karaborsa_uyari = " (🔥 Karaborsa!)" if stok_adet < 5 and stok_adet > 0 else ""

    btn_text_1 = f"{secilen_adet} Adet Hesap"
    btn_text_2 = f"Seçilenleri carpipuan ile Al ({toplam_puan} Puan){karaborsa_uyari}"
    btn_text_3 = f"{yildiz_adet} Adet Hesap"
    btn_text_4 = f"Seçilenleri Yıldız ile Al ({toplam_yildiz} Yıldız)"

    keyboard = [
        [
            InlineKeyboardButton("➖", callback_data="h_az"),
            InlineKeyboardButton(btn_text_1, callback_data="bos_bilgi"),
            InlineKeyboardButton("➕", callback_data="h_art"),
        ],
        [InlineKeyboardButton(btn_text_2, callback_data="hp_al")],
        [
            InlineKeyboardButton("➖", callback_data="y_az"),
            InlineKeyboardButton(btn_text_3, callback_data="bos_bilgi"),
            InlineKeyboardButton("➕", callback_data="y_art"),
        ],
        [InlineKeyboardButton(btn_text_4, callback_data="y_al")],
        [
            InlineKeyboardButton(
                "📂 Es3 şifre oluştur", callback_data="es3_baslat"
            )
        ],
        [
            InlineKeyboardButton(
                "🎟️ Promo Kod Kullan", callback_data="promo_kullan"
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
                "🔐 Şifreyi Çöz & Ödülü Kap (3 Yıldız)",
                callback_data="sifre_baslat",
            )
        ],
        [
            InlineKeyboardButton(
                "🎁 Günlük Ödül Al (0.3 - 2 Puan)", callback_data="gunluk"
            )
        ],
        [InlineKeyboardButton("🏆 En İyiler (Liderlik)", callback_data="liderlik")],
        [
            InlineKeyboardButton(
                "👥 Arkadaşını Davet Et (+5 carpipuan)", callback_data="davet"
            )
        ],
        [InlineKeyboardButton("👤 Profilim & Bilgilerim", callback_data="profil")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_str = str(update.effective_user.id)
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
            "sifre_oyunu_kullanildi": False,
            "beklenen_sifre": None,
            "used_promos": [],
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
                                text="🎉 Tebrikler reis! Davet ettiğin kullanıcı botu başlattı ve hesabına +5 puan eklendi!",
                            )
                        except Exception:
                            pass
            except Exception:
                pass
        veri_kaydet()

    stok_adet = len(stok_oku())
    user_data = KULLANICILAR[user_id_str]
    mesaj = f"🚀 CPM1 Hesap Mağazasına Hoş Geldin!\n\n📦 Güncel Stok: {stok_adet} adet hesap\n🏆 carpipuanın: +{user_data['carpipuan']} carpipuan\n\nAşağıdaki menüden işlem seçebilirsin:"
    await update.message.reply_text(
        mesaj,
        reply_markup=get_ana_menu_keyboard(stok_adet, user_data),
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Yetkin yok reis!")
        return

    stok_adet = len(stok_oku())
    toplam_uye = len(KULLANICILAR)
    mesaj = f"👑 Admin Paneli\n\n👥 Toplam Üye: {toplam_uye}\n📦 Güncel Stok: {stok_adet}"
    await update.message.reply_text(
        mesaj,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Stok Bilgisi", callback_data="admin_stok")],
            [InlineKeyboardButton("🎟️ Promo Kod Oluştur", callback_data="admin_promo")],
            [InlineKeyboardButton("📢 Duyuru Gönder", callback_data="admin_duyuru")],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")],
        ]),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id_str = str(query.from_user.id)
    user_id = query.from_user.id

    if user_id_str in DB_DATA.get("banned", []):
        await query.answer("❌ Engellendiğin için işlem yapamazsın.", show_alert=True)
        return

    if user_id_str not in KULLANICILAR:
        KULLANICILAR[user_id_str] = {
            "carpipuan": 0.0,
            "son_gunluk": 0,
            "hesap_adet": 1,
            "yildiz_hesap_adet": 1,
            "sifre_oyunu_kullanildi": False,
            "beklenen_sifre": None,
            "used_promos": [],
        }
        veri_kaydet()

    user_data = KULLANICILAR[user_id_str]
    stok_adet = len(stok_oku())

    if query.data == "bos_bilgi":
        await query.answer()
        return

    elif query.data == "es3_baslat":
        await query.answer()
        context.user_data["beklenen_islem"] = "es3_dosya"
        keyboard = [[InlineKeyboardButton("🔙 İptal / Ana Menü", callback_data="ana_menu")]]
        mesaj = (
            "📁 Es3 Şifre Oluşturma Paneli\n\n"
            "1️⃣ Adım 1: Lütfen cihazınızdaki .es3 uzantılı dosyanızı belge/dosya olarak sohbete yükleyin:"
        )
        try:
            await query.edit_message_text(
                mesaj,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception:
            pass

    elif query.data == "promo_kullan":
        await query.answer()
        context.user_data["beklenen_islem"] = "promo_gir"
        keyboard = [[InlineKeyboardButton("🔙 İptal / Ana Menü", callback_data="ana_menu")]]
        await query.edit_message_text(
            "🎟️ Lütfen kullanmak istediğin Promo Kodu sohbete mesaj olarak yaz:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "admin_promo":
        if user_id not in ADMIN_IDS:
            await query.answer("Yetkin yok!", show_alert=True)
            return
        context.user_data["beklenen_admin_islem"] = "promo_olustur"
        await query.answer()
        await query.edit_message_text(
            "🎟️ Oluşturmak istediğin Promo Kod ve Puan Değerini yaz:\n\nÖrnek:\nHEDIYE50 50",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 İptal", callback_data="ana_menu")]]
            ),
        )

    elif query.data == "admin_stok":
        if user_id not in ADMIN_IDS:
            await query.answer("Yetkin yok!", show_alert=True)
            return
        await query.answer()
        mesaj = f"📦 Stokta toplam {stok_adet} hesap var. stok.txt üzerinden ekleme yapabilirsin."
        await query.edit_message_text(
            mesaj,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")]]
            ),
        )

    elif query.data == "admin_duyuru":
        if user_id not in ADMIN_IDS:
            await query.answer("Yetkin yok!", show_alert=True)
            return
        context.user_data["beklenen_admin_islem"] = "duyuru"
        await query.answer()
        await query.edit_message_text(
            "📢 Göndermek istediğin duyuru metnini sohbete yaz:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 İptal", callback_data="ana_menu")]]
            ),
        )

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
        base_puan = adet * 15.0
        gerekli_puan = get_dynamic_price(int(base_puan))

        if user_data["carpipuan"] < gerekli_puan:
            await query.answer(
                f"❌ Yetersiz puan! Lazım: {gerekli_puan}", show_alert=True
            )
            return

        if stok_adet < adet:
            await query.answer("❌ Stok kalmadı!", show_alert=True)
            return

        verilenler = stok_dusur_ve_ver(adet)
        if verilenler:
            await query.answer()
            cashback = int(gerekli_puan * 0.10)
            user_data["carpipuan"] = round(
                user_data["carpipuan"] - gerekli_puan + cashback, 1
            )
            veri_kaydet()

            hesaplar_metni = "\n".join(verilenler)
            keyboard = [[InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")]]
            try:
                mesaj = f"✅ VIP Hesaplar Verildi!\n\n🔑 Bilgiler:\n{hesaplar_metni}\n\n💰 Kalan Puan: +{user_data['carpipuan']}"
                await query.edit_message_text(
                    mesaj,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            except Exception:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ VIP Hesaplar Verildi:\n\n{hesaplar_metni}",
                )
        else:
            await query.answer("❌ Stok hatası!", show_alert=True)

    elif query.data == "sifre_baslat":
        await query.answer()
        if user_data.get("sifre_oyunu_kullanildi", False):
            await query.answer("❌ Hakkını zaten kullandın!", show_alert=True)
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
            title="🔐 Şifre Çözme Oyunu",
            description="3 Yıldız öde, şifreyi al ve sohbete yaz!",
            payload="sifre_oyunu_3_yildiz",
            currency="XTR",
            prices=[LabeledPrice("Sifre Hakki", 3)],
        )

    elif query.data == "y_al":
        await query.answer()
        adet = user_data.get("yildiz_hesap_adet", 1)
        toplam_fiyat = adet * 15
        if stok_adet < adet:
            await query.answer("❌ Stok yetersiz!", show_alert=True)
            return

        await context.bot.send_invoice(
            chat_id=user_id,
            title=f"{adet} Adet Hesap",
            description=f"{adet} Adet Hesap ({toplam_fiyat} Yildiz)",
            payload=f"hesap_coklu_{adet}",
            currency="XTR",
            prices=[LabeledPrice("VIP Hesap", toplam_fiyat)],
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
            [InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")],
        ]
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("p_yildiz_"):
        await query.answer()
        yildiz_miktari = int(query.data.split("_")[2])
        puan_tablosu = {50: 50, 100: 120, 500: 700}
        kazanilacak_puan = puan_tablosu.get(yildiz_miktari, 50)

        await context.bot.send_invoice(
            chat_id=user_id,
            title="⭐ carpipuan Yukleme",
            description=f"{yildiz_miktari} Yildiz karsiligi {kazanilacak_puan} Puan",
            payload=f"puan_yukle_{yildiz_miktari}_{kazanilacak_puan}",
            currency="XTR",
            prices=[LabeledPrice("Puan Paketi", yildiz_miktari)],
        )

    elif query.data == "gunluk":
        await query.answer()
        simdi = time.time()
        if simdi - user_data["son_gunluk"] < 86400:
            keyboard = [[InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")]]
            await query.edit_message_text(
                "⏳ Günlük ödülü zaten aldın!",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        user_data["son_gunluk"] = simdi
        kazanilan = round(random.uniform(0.3, 2.0), 1)
        user_data["carpipuan"] = round(user_data["carpipuan"] + kazanilan, 1)
        veri_kaydet()

        keyboard = [[InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")]]
        mesaj = f"🎁 Günlük Ödül: +{kazanilan} Puan"
        await query.edit_message_text(
            mesaj,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "davet":
        await query.answer()
        davet_linki = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
        davet_sayisi = user_data.get("davet_sayisi", 0)

        keyboard = [[InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")]]
        mesaj = f"👥 Davet Et Kazan!\n\nLinkin:\n{davet_linki}\n\nDavet Edilen: {davet_sayisi}"
        await query.edit_message_text(
            mesaj,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "liderlik":
        await query.answer()
        sirali = sorted(
            KULLANICILAR.items(), key=lambda x: x[1]["carpipuan"], reverse=True
        )[:10]
        metin = "🏆 Liderlik Tablosu\n\n"
        for sira, (uid, udata) in enumerate(sirali, 1):
            metin += f"{sira}. carpipuan: +{udata['carpipuan']}\n"

        keyboard = [[InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")]]
        await query.edit_message_text(
            metin, reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "profil":
        await query.answer()
        keyboard = [[InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")]]
        davet_sayisi = user_data.get("davet_sayisi", 0)
        mesaj = f"👤 Profilin:\n\nID: {user_id}\ncarpipuan: +{user_data['carpipuan']}\nDavet: {davet_sayisi}"
        await query.edit_message_text(
            mesaj,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "ana_menu":
        await query.answer()
        context.user_data["beklenen_islem"] = None
        context.user_data["beklenen_admin_islem"] = None
        try:
            mesaj = f"🚀 CPM1 Hesap Mağazasına Hoş Geldin!\n\n📦 Stok: {stok_adet}\ncarpipuanın: +{user_data['carpipuan']}"
            await query.edit_message_text(
                mesaj,
                reply_markup=get_ana_menu_keyboard(stok_adet, user_data),
            )
        except Exception:
            pass


async def pre_checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pa
