
import json, logging, random, time
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram import Update

from provider_client import OrkutProvider

CFG = json.load(open("config.json","r",encoding="utf-8"))

def clamp_months(m:int) -> int:
    try: m = int(m)
    except: m = 1
    return max(1, min(12, m))

def build_amount(price_per_month:int, months:int) -> int:
    months = clamp_months(months)
    uniq = random.randint(1, 999)
    return price_per_month * months + uniq

def kb(m: int) -> InlineKeyboardMarkup:
    m = clamp_months(m)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("−", callback_data=f"m:{m-1}"),
         InlineKeyboardButton(f"{m} bulan", callback_data="noop"),
         InlineKeyboardButton("+", callback_data=f"m:{m+1}")],
        [InlineKeyboardButton("Bayar", callback_data=f"pay:{m}")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_chat.send_message("OrderKuota — /order untuk mulai.")

async def order_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_chat.send_message("Pilih durasi (bulan), lalu tekan Bayar.", reply_markup=kb(1))

async def order_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import httpx
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("m:"):
        m = clamp_months(int(data.split(":")[1]))
        await q.edit_message_reply_markup(reply_markup=kb(m))
        return

    if data.startswith("pay:"):
        months = clamp_months(int(data.split(":")[1]))
        amount = build_amount(CFG["pricing"]["price_per_month"], months)
        pv = OrkutProvider(CFG)

        # 1) create order
        try:
            resp = pv.create_payment(amount=amount, note=f"VIP {months}m user {q.from_user.id}")
        except httpx.HTTPStatusError as e:
            await q.edit_message_text(f"Create payment gagal: HTTP {e.response.status_code}\n{e.response.text[:600]}")
            return
        except Exception as e:
            await q.edit_message_text(f"Create payment error: {e}")
            return

        key, qr = pv.extract_key_and_qr(resp)
        if not key:
            await q.edit_message_text(f"Create OK tapi key tidak ditemukan. Resp: {str(resp)[:800]}")
            return

        msg = f"Nominal unik: {amount}\nKey: {key}"
        if qr: msg += f"\nQR/URL: {qr}"
        await q.edit_message_text(msg)

        # 2) poll cekstatus
        window = int(CFG["order"]["window_sec"])
        interval = int(CFG["order"]["poll_interval_sec"])
        stop_at = time.time() + window

        async def poll(_ctx):
            try:
                status = pv.cek_status(key)
                if pv.is_paid(status):
                    # grant membership
                    vip_chat_id = CFG["telegram"]["vip_chat_id"]
                    invite_exp = datetime.utcnow() + timedelta(minutes=5)
                    link = await context.application.bot.create_chat_invite_link(
                        chat_id=vip_chat_id, expire_date=invite_exp, member_limit=1
                    )
                    await context.bot.send_message(q.message.chat_id, f"Pembayaran sukses. Invite: {link.invite_link}")
                    return
            except Exception as e:
                logging.warning("cek_status error: %s", e)

            if time.time() < stop_at:
                context.job_queue.run_once(lambda c: context.application.create_task(poll(c)), when=interval)

        context.job_queue.run_once(lambda c: context.application.create_task(poll(c)), when=0)

def main():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )
    app = Application.builder().token(CFG["telegram"]["bot_token"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("order", order_cmd))
    app.add_handler(CallbackQueryHandler(order_cb))
    logging.info("Bot started.")
    app.run_polling(allowed_updates=["message","callback_query","chat_join_request"])

if __name__ == "__main__":
    main()
