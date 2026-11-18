import sys
import subprocess
import asyncio
import importlib
import time
from datetime import datetime, timedelta

def install_and_import(package):
    try:
        importlib.import_module(package)
    except ImportError:
        print(f"📦 جاري تثبيت: {package} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_and_import("telethon")

from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.errors import (
    PeerFloodError, 
    UserPrivacyRestrictedError, 
    UserAlreadyParticipantError, 
    FloodWaitError,
    SessionPasswordNeededError
)

# بيانات البوت الأساسي والتطبيق
API_ID = 39144087
API_HASH = '6f528e477c831770577a5941c924ba18'
BOT_TOKEN = '9027833698:AAGsrT2rJG5VFDVIiBkF13se3ulg_s7p4Ws'
ADMIN_ID = 7326131662

# قاعدة بيانات الاستضافة والاشتراكات المركزية
hosting_db = {
    "source": None,
    "target": None,
    "accounts": [],  
    "states": {},
    "subscription_codes": {}, 
    "active_subscriptions": {} 
}

LIMIT_MESSAGES = 500

def clean_input(text: str) -> str:
    text = text.strip()
    if "t.me/+" in text or "t.me/joinchat/" in text:
        return text
    if "t.me/" in text:
        text = text.split("t.me/")[-1].split("/")[0].split("?")[0]
    if text.startswith("@"):
        text = text[1:]
    return text

def user_is_subscribed(uid: int) -> bool:
    if uid == ADMIN_ID:
        return True
    expire_time = hosting_db["active_subscriptions"].get(uid, 0)
    return time.time() < expire_time

def get_user_remaining_time(uid: int) -> str:
    expire_time = hosting_db["active_subscriptions"].get(uid, 0)
    remaining = int(expire_time - time.time())
    if remaining <= 0:
        return "منتهي"
    
    days = remaining // 86400
    hours = (remaining % 86400) // 3600
    minutes = (remaining % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} يوم")
    if hours > 0:
        parts.append(f"{hours} ساعة")
    if minutes > 0 or not parts:
        parts.append(f"{minutes} دقيقة")
    
    return " و ".join(parts)

def get_main_buttons(uid: int):
    is_admin = (uid == ADMIN_ID)
    buttons = [
        [Button.inline("🔑 تفعيل كود الاشتراك", data="activate_code")],
        [Button.inline("⏳ الوقت المتبقي لاشتراكي", data="check_sub")],
        [Button.inline("🔗 تعيين الروابط", data="links")],
        [
            Button.inline("➕ إضافة رقم", data="add"),
            Button.inline("📋 الأرقام المضافة", data="list")
        ],
        [Button.inline("🆔 استخراج الآيدي", data="get_id")],
        [Button.inline("⚡ بدء النقل السريع", data="transfer")],
        [Button.inline("🗑️ مسح الكل", data="reset")],
        [Button.url("📞 تواصل مع المطور", "https://t.me/Mo_AGSTOR")]
    ]
    if is_admin:
        buttons.insert(0, [Button.inline("⚙️ [لوحة الأدمن] توليد كود اشتراك", data="admin_gen_code")])
        buttons.insert(1, [Button.inline("📋 [لوحة الأدمن] استعراض الأكواد", data="admin_list_codes")])
        buttons.insert(3, [Button.inline("❌ [لوحة الأدمن] إلغاء اشتراكي", data="admin_cancel_sub")])
    return buttons

bot = TelegramClient('mg_hosting_bot', API_ID, API_HASH)

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    uid = event.sender_id
    is_admin = (uid == ADMIN_ID)
    
    sub_status = "🟢 مفعل" if user_is_subscribed(uid) else "🔴 غير مفعل (منتهي)"
    if user_is_subscribed(uid) and not is_admin:
        sub_status += f" (يتبقى: {get_user_remaining_time(uid)})"

    welcome_text = (
        f"🤖 **أهلاً بك في منصة استضافة بوتات النقل السريع MG❤️‍🔥**\n"
        f"🆔 آيديك: `{uid}`\n"
        f"📌 **حالة اشتراكك:** {sub_status}\n\n"
        f"استخدم الأزرار أدناه للتحكم بخدمات الاستضافة:"
    )
    await event.respond(welcome_text, buttons=get_main_buttons(uid))

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    uid = event.sender_id
    data = event.data.decode('utf-8')
    is_admin = (uid == ADMIN_ID)

    if data == "main":
        hosting_db["states"].pop(uid, None)
        sub_status = f"🟢 مفعل ({get_user_remaining_time(uid)})" if user_is_subscribed(uid) else "🔴 متوقف"
        await event.edit(
            f"🏠 **القائمة الرئيسية للاستضافة:**\n📌 حالتك: {sub_status}", 
            buttons=get_main_buttons(uid)
        )

    elif data == "activate_code":
        hosting_db["states"][uid] = "enter_activation_code"
        await event.edit(
            "🔑 **تفعيل اشتراك الاستضافة:**\nأرسل الآن كود الاشتراك الخاص بك لتشغيل البوت لديك:",
            buttons=[[Button.inline("🔙 رجوع", data="main")]]
        )

    elif data == "check_sub":
        if user_is_subscribed(uid):
            await event.answer(f"⏳ الوقت المتبقي لاشتراكك: {get_user_remaining_time(uid)}", alert=True)
        else:
            await event.answer("❌ عذراً، اشتراكك منتهي أو غير مفعل!", alert=True)

    elif data == "admin_gen_code" and is_admin:
        hosting_db["states"][uid] = "admin_ask_duration"
        await event.edit(
            "⏱️ أرسل مدة الكود بالدقائق (مثال: `60` لساعة، `1440` ليوم، `10080` لأسبوع):",
            buttons=[[Button.inline("🔙 رجوع", data="main")]]
        )

    elif data == "admin_list_codes" and is_admin:
        codes = hosting_db["subscription_codes"]
        if not codes:
            txt = "📭 لا توجد أي أكواد مسجلة في النظام حالياً."
        else:
            txt = "📋 **قائمة أكواد الاستضافة المسجلة:**\n\n"
            for code, info in codes.items():
                status = "🔴 تم استخدامه" if info["used"] else "🟢 متاح"
                expire_str = datetime.fromtimestamp(info["expire"]).strftime('%Y-%m-%d %H:%M')
                txt += f"🔑 `{code}` | الحالة: {status}\n   ⏳ ينتهي في: {expire_str}\n\n"
        await event.edit(txt, buttons=[[Button.inline("🔙 رجوع", data="main")]])

    elif data == "admin_cancel_sub":
        hosting_db["active_subscriptions"][uid] = 0
        await event.answer("❌ تم إلغاء اشتراكك وتوقيف الخدمة فوراً!", alert=True)
        await event.edit(
            "🏠 **القائمة الرئيسية للاستضافة:**\n📌 حالتك: 🔴 غير مفعل", 
            buttons=get_main_buttons(uid)
        )

    elif data == "links":
        if not user_is_subscribed(uid):
            return await event.answer("❌ يجب تفعيل الاشتراك أولاً لاستخدام هذه الميزة!", alert=True)
        hosting_db["states"][uid] = "source"
        await event.edit(
            "🔗 أرسل **يوزر أو رابط الجروب المصدر** الآن:",
            buttons=[[Button.inline("🔙 رجوع", data="main")]]
        )

    elif data == "add":
        if not user_is_subscribed(uid):
            return await event.answer("❌ يجب تفعيل الاشتراك أولاً لاستخدام هذه الميزة!", alert=True)
        hosting_db["states"][uid] = {"step": "ask_phone"}
        await event.edit(
            "📱 أرسل رقم الهاتف مع رمز الدولة (مثال: `+201234567890`):",
            buttons=[[Button.inline("🔙 رجوع", data="main")]]
        )

    elif data == "list":
        if not user_is_subscribed(uid):
            return await event.answer("❌ يجب تفعيل الاشتراك أولاً!", alert=True)
        accs = hosting_db["accounts"]
        txt = "لا توجد أرقام مضافة." if not accs else "\n".join([f"{i+1}. `{a['phone']}`" for i, a in enumerate(accs)])
        await event.edit(
            f"📋 **الأرقام المضافة في الاستضافة ({len(accs)}):**\n\n{txt}",
            buttons=[[Button.inline("🔙 رجوع", data="main")]]
        )

    elif data == "get_id":
        if not user_is_subscribed(uid):
            return await event.answer("❌ يجب تفعيل الاشتراك أولاً!", alert=True)
        hosting_db["states"][uid] = "extract_id"
        await event.edit(
            "🆔 أرسل **رابط المجموعة أو القناة** لاستخراج الآيدي الخاص بها:",
            buttons=[[Button.inline("🔙 رجوع", data="main")]]
        )

    elif data == "reset":
        hosting_db["source"] = None
        hosting_db["target"] = None
        hosting_db["accounts"] = []
        hosting_db["states"].clear()
        await event.answer("🗑️ تم مسح بيانات الاستضافة المؤقتة!", alert=True)
        await event.edit("🏠 **القائمة الرئيسية:**", buttons=get_main_buttons(uid))

    elif data == "transfer":
        if not user_is_subscribed(uid):
            return await event.answer("❌ عذراً، اشتراكك منتهي! يرجى إدخال كود تفعيل صالح.", alert=True)
        if not hosting_db["source"] or not hosting_db["target"]:
            return await event.answer("⚠️ قم بتعيين المصدر والهدف أولاً!", alert=True)
        if not hosting_db["accounts"]:
            return await event.answer("⚠️ أضف رقماً واحداً على الأقل لنقل الأعضاء عبره!", alert=True)

        await event.edit("⚡ **جاري بدء عملية النقل السريع عبر سيرفر الاستضافة... راقب التيرمنال ⏳**")
        
        acc = hosting_db["accounts"][0]
        session_name = f"session_{acc['phone']}"
        
        try:
            user_client = TelegramClient(session_name, API_ID, API_HASH)
            await user_client.connect()
            
            source_entity = await user_client.get_entity(hosting_db["source"])
            target_entity = await user_client.get_entity(hosting_db["target"])
            
            print("\n🔍 جاري سحب الأعضاء عبر سيرفر الاستضافة...")
            active_users = set()
            
            async for message in user_client.iter_messages(source_entity, limit=LIMIT_MESSAGES):
                if message.sender_id and message.sender:
                    if hasattr(message.sender, 'bot') and message.sender.bot:
                        continue
                    active_users.add(message.sender_id)
            
            print(f"✅ تم العثور على {len(active_users)} عضو. جاري النقل فوراً...")
            added_count = 0
            
            for user_id in active_users:
                if not user_is_subscribed(uid):
                    print("❌ تم إيقاف عملية النقل لانصهار/انتهاء اشتراك المستخدم!")
                    break
                try:
                    await user_client(InviteToChannelRequest(target_entity, [user_id]))
                    added_count += 1
                    print(f"➕ [نجاح استضافة] تم نقل {user_id} | المجموع: {added_count}")
                    await asyncio.sleep(0.5)
                except UserPrivacyRestrictedError:
                    print(f"❌ [خصوصية] العضو {user_id} يغلق خاصية الإضافة.")
                except UserAlreadyParticipantError:
                    print(f"ℹ️ [تنبيه] العضو {user_id} موجود بالفعل.")
                except PeerFloodError:
                    print(f"⚠️ [سبام] الحساب مضغوط.. تخطي ونقل العضو التالي...")
                except FloodWaitError as e:
                    print(f"⏳ قيود تليجرام: انتظار {e.seconds} ثانية والمتابعة...")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"⚠️ خطأ نقل العضو {user_id}: {e}")

            await user_client.disconnect()
            await event.respond(f"✅ **تم الانتهاء من دورة النقل عبر الاستضافة!**\n• إجمالي المنقولين: `{added_count}`", buttons=get_main_buttons(uid))
            
        except Exception as e:
            print(f"❌ خطأ في نقل الاستضافة: {e}")
            await event.respond(f"❌ حدث خطأ:\n`{str(e)}`", buttons=get_main_buttons(uid))

@bot.on(events.NewMessage)
async def message_handler(event):
    uid = event.sender_id
    state = hosting_db["states"].get(uid)
    if not state:
        return

    txt = event.raw_text.strip()
    is_admin = (uid == ADMIN_ID)

    if is_admin and state == "admin_ask_duration":
        hosting_db["states"].pop(uid, None)
        try:
            minutes = int(txt)
            import random, string
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            expire_time = time.time() + (minutes * 60)
            
            hosting_db["subscription_codes"][code] = {
                "expire": expire_time,
                "used": False
            }
            
            expire_date_str = datetime.fromtimestamp(expire_time).strftime('%Y-%m-%d %H:%M:%S')
            await event.respond(
                f"✅ **تم إنشاء كود الاستضافة بنجاح!**\n\n"
                f"🔑 **الكود:** `{code}`\n"
                f"⏱️ **المدة:** {minutes} دقيقة\n"
                f"📅 **ينتهي في:** `{expire_date_str}`",
                buttons=get_main_buttons(uid)
            )
        except ValueError:
            await event.respond("❌ خطأ: يرجى إرسال أرقام صحيحة تمثل الدقائق.", buttons=get_main_buttons(uid))
        return

    if state == "enter_activation_code":
        hosting_db["states"].pop(uid, None)
        if txt in hosting_db["subscription_codes"]:
            code_info = hosting_db["subscription_codes"][txt]
            if code_info["used"]:
                await event.respond("❌ عذراً، هذا الكود استُخدم مسبقاً!", buttons=get_main_buttons(uid))
            elif time.time() < code_info["expire"]:
                hosting_db["active_subscriptions"][uid] = code_info["expire"]
                code_info["used"] = True
                
                expire_date_str = datetime.fromtimestamp(code_info["expire"]).strftime('%Y-%m-%d %H:%M:%S')
                await event.respond(
                    f"🎉 **تم تفعيل اشتراك الاستضافة بنجاح!**\n"
                    f"⏳ **ينتهي اشتراكك في:** `{expire_date_str}`",
                    buttons=get_main_buttons(uid)
                )
            else:
                await event.respond("❌ عذراً، هذا الكود منتهي الصلاحية.", buttons=get_main_buttons(uid))
        else:
            await event.respond("❌ كود الاستضافة غير صحيح!", buttons=get_main_buttons(uid))
        return

    if not user_is_subscribed(uid):
        return await event.respond("❌ الاستضافة غير مفعلة لديك! يرجى إدخال كود اشتراك صالح.")

    if state == "source":
        hosting_db["source"] = clean_input(txt)
        hosting_db["states"][uid] = "target"
        await event.respond("✅ تم حفظ المصدر.\nالآن أرسل **يوزر أو رابط الجروب المستهدف (الهدف)**:")

    elif state == "target":
        hosting_db["target"] = clean_input(txt)
        hosting_db["states"].pop(uid, None)
        await event.respond("✅ تم حفظ الروابط بنجاح!", buttons=get_main_buttons(uid))

    elif state == "extract_id":
        hosting_db["states"].pop(uid, None)
        try:
            entity = await bot.get_entity(clean_input(txt))
            await event.respond(
                f"✅ **تم استخراج معلومات المجموعة بنجاح:**\n\n"
                f"📌 **الاسم:** {getattr(entity, 'title', 'مجموعة')}\n"
                f"🆔 **الآيدي:** `{entity.id}`",
                buttons=get_main_buttons(uid)
            )
        except Exception as e:
            await event.respond(f"❌ تعذر استخراج الآيدي:\n`{str(e)}`", buttons=get_main_buttons(uid))

    elif isinstance(state, dict) and state.get("step") == "ask_phone":
        phone = txt
        try:
            client = TelegramClient(f"session_{phone}", API_ID, API_HASH)
            await client.connect()
            sent = await client.send_code_request(phone)
            hosting_db["states"][uid] = {"step": "ask_code", "phone": phone, "client": client, "hash": sent.phone_code_hash}
            await event.respond("📨 أرسل كود التحقق (OTP) الذي وصلك من تيليجرام:")
        except Exception as e:
            hosting_db["states"].pop(uid, None)
            await event.respond(f"❌ خطأ في إرسال الكود:\n`{str(e)}`", buttons=get_main_buttons(uid))

    elif isinstance(state, dict) and state.get("step") == "ask_code":
        client = state["client"]
        phone = state["phone"]
        hash_code = state["hash"]
        code = txt
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=hash_code)
            hosting_db["accounts"].append({"phone": phone})
            hosting_db["states"].pop(uid, None)
            await client.disconnect()
            await event.respond(f"✅ تم ربط الرقم `{phone}` بنجاح في الاستضافة!", buttons=get_main_buttons(uid))
        except SessionPasswordNeededError:
            hosting_db["states"][uid]["step"] = "ask_2fa"
            await event.respond("🔒 الرقم محمي بكلمة مرور التحقق الثنائي (2FA). أرسل كلمة المرور:")
        except Exception as e:
            hosting_db["states"].pop(uid, None)
            await event.respond(f"❌ الكود غير صحيح:\n`{str(e)}`", buttons=get_main_buttons(uid))

    elif isinstance(state, dict) and state.get("step") == "ask_2fa":
        client = state["client"]
        phone = state["phone"]
        password = txt
        try:
            await client.sign_in(password=password)
            hosting_db["accounts"].append({"phone": phone})
            hosting_db["states"].pop(uid, None)
            await client.disconnect()
            await event.respond(f"✅ تم ربط الرقم `{phone}` بنجاح عبر التحقق الثنائي!", buttons=get_main_buttons(uid))
        except Exception as e:
            await client.disconnect()
            hosting_db["states"].pop(uid, None)
            await event.respond(f"❌ كلمة المرور خطأ:\n`{str(e)}`", buttons=get_main_buttons(uid))

if __name__ == "__main__":
    print("🤖 MG Hosting & Subscriptions Bot is running stably...")
    bot.start(bot_token=BOT_TOKEN)
    bot.run_until_disconnected()
