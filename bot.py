import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from typing import Tuple, Optional
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from src.parser import parse_transaction
from src.database import (
    init_db,
    save_transaction,
    delete_transaction,
    get_rekap_data,
    get_paginated_transactions,
    MONTH_NAMES
)
from src.chart import generate_rekap_chart, generate_text_bars

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Mini web server responder for Render / cloud keep-alive."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot Telegram is Running 24/7!")

    def log_message(self, format, *args):
        pass  # Suppress HTTP spam logs

def run_health_server():
    """Runs a lightweight web server on the port provided by Render ($PORT)."""
    port = int(os.getenv("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        logger.info(f"🌐 Health-check web server aktif di port {port}")
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Health server error: {e}")

CATEGORY_EMOJIS = {
    'Makanan & Minuman': '🍔',
    'Transportasi': '🛵',
    'Top Up / E-Wallet': '📱',
    'Belanja': '🛍️',
    'Tagihan': '💡',
    'Hiburan': '🎮',
    'Pendapatan': '💵',
    'Lain-lain': '📦'
}

def get_rekap_keyboard(current_period: str = 'month') -> InlineKeyboardMarkup:
    """Navigation keyboard for different time periods."""
    buttons = [
        [
            InlineKeyboardButton("📅 Hari Ini", callback_data="rekap_today"),
            InlineKeyboardButton("🗓️ 7 Hari Terakhir", callback_data="rekap_week")
        ],
        [
            InlineKeyboardButton("📆 Bulan Ini", callback_data="rekap_month"),
            InlineKeyboardButton("⏪ Bulan Lalu", callback_data="rekap_last_month")
        ],
        [
            InlineKeyboardButton("🗓️ Pilih Bulan Lain...", callback_data="rekap_pick_month")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def get_month_picker_keyboard() -> InlineKeyboardMarkup:
    """Shows last 6 months as buttons for quick selection."""
    now = datetime.now()
    buttons = []
    row = []

    year = now.year
    month = now.month

    for _ in range(6):
        m_str = f"{month:02d}"
        y_str = f"{year}"
        val = f"{y_str}-{m_str}"
        m_name = MONTH_NAMES.get(m_str, m_str)
        row.append(InlineKeyboardButton(f"{m_name[:3]} '{y_str[2:]}", callback_data=f"rekap_custom_{val}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 Kembali ke Rekap", callback_data="rekap_month")])
    return InlineKeyboardMarkup(buttons)

async def render_and_send_rekap(user_id: int, period: str = 'month', custom_val: Optional[str] = None, 
                                query = None, message = None):
    """Fetches data, renders chart, and sends or edits message seamlessly."""
    cat_data, total_expense, total_income, period_label = get_rekap_data(user_id, period, custom_val)

    text_bars = generate_text_bars(cat_data, total_expense) if total_expense > 0 else "<i>Belum ada pengeluaran pada periode ini.</i>"

    caption = (
        f"📊 <b>REKAP PENGELUARAN ({period_label.upper()})</b>\n"
        f"💸 Total Keluar : <b>Rp {total_expense:,.0f}</b>\n"
        f"💰 Total Masuk  : <b>Rp {total_income:,.0f}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{text_bars}"
    ).replace(',', '.')

    keyboard = get_rekap_keyboard(period)
    chart_buf = generate_rekap_chart(cat_data, total_expense, title=f"Pengeluaran - {period_label}")

    if query:
        # User clicked an inline button: edit in-place
        try:
            await query.edit_message_media(
                media=InputMediaPhoto(media=chart_buf, caption=caption, parse_mode="HTML"),
                reply_markup=keyboard
            )
        except Exception as e:
            logger.warning(f"Fallback edit message: {e}")
            await query.message.reply_photo(photo=chart_buf, caption=caption, parse_mode="HTML", reply_markup=keyboard)
    elif message:
        # User typed 'rekap' in chat
        await message.reply_photo(photo=chart_buf, caption=caption, parse_mode="HTML", reply_markup=keyboard)

def build_riwayat_view(user_id: int, page: int = 1) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """Builds paginated transaction history view with navigation buttons."""
    items, total_count, total_pages = get_paginated_transactions(user_id, page=page, per_page=5)
    if total_count == 0:
        return "Belum ada riwayat transaksi.", None

    lines = [
        f"📜 <b>Riwayat Transaksi</b> (Hal {page}/{total_pages} • Total {total_count})",
        "━━━━━━━━━━━━━━━━━━━━"
    ]

    for idx, r in enumerate(items, start=(page - 1) * 5 + 1):
        icon = "💰 +" if r['type'] == 'INCOME' else "💸 -"
        amount_fmt = f"Rp {int(r['amount']):,.0f}".replace(',', '.')
        cat_icon = CATEGORY_EMOJIS.get(r['category'], '🔹')

        created = r.get('created_at', '')
        date_str = ""
        if created:
            try:
                dt = datetime.strptime(created.split('.')[0], "%Y-%m-%d %H:%M:%S")
                date_str = f" • {dt.strftime('%d/%m %H:%M')}"
            except Exception:
                date_str = f" • {created[:16]}"

        lines.append(f"{idx}. {cat_icon} <b>{r['category']}</b>: {icon}{amount_fmt}")
        lines.append(f"    └ <i>{r['description']}</i>{date_str}")

    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{page - 1}"))
    buttons.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="page_noop"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page + 1}"))

    keyboard = InlineKeyboardMarkup([buttons]) if total_pages > 1 else None
    return "\n".join(lines), keyboard

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple concise guide, zero fluff."""
    text = (
        "⚡ <b>Catat Cepat Keuangan</b>\n\n"
        "Ketik langsung tanpa ribet:\n"
        "• <code>nasi 20rb</code>\n"
        "• <code>duit bensin 40rb</code>\n"
        "• <code>topup gopay 25.5rb</code>\n"
        "• <code>duit dari Budi 50rb</code>\n\n"
        "📊 Ketik <b>rekap</b> untuk lihat grafik & pilih periode.\n"
        "📜 Ketik <b>riwayat</b> untuk daftar transaksi berhalaman."
    )
    await update.message.reply_html(text)

async def handle_rekap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /rekap command or chat 'rekap'."""
    user_id = update.effective_user.id
    await render_and_send_rekap(user_id=user_id, period='month', message=update.message)

async def handle_riwayat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show paginated transaction history."""
    user_id = update.effective_user.id
    text, keyboard = build_riwayat_view(user_id, page=1)
    await update.message.reply_html(text, reply_markup=keyboard)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parse text and save to database immediately."""
    text = update.message.text.strip()
    user = update.effective_user

    # Shortcut triggers for reports
    lower_text = text.lower()
    if lower_text in ['rekap', 'laporan', 'chart', 'grafik', '/rekap']:
        await handle_rekap(update, context)
        return
    if lower_text in ['riwayat', 'history', '/riwayat']:
        await handle_riwayat(update, context)
        return

    # Parse natural language input
    result = parse_transaction(text)
    if not result:
        return

    # Save to database
    tx_id = save_transaction(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        amount=result['amount'],
        category=result['category'],
        tx_type=result['type'],
        description=result['description']
    )

    amount_str = f"Rp {result['amount']:,.0f}".replace(',', '.')
    if result['type'] == 'INCOME':
        reply_text = f"💰 <b>+{amount_str}</b> | {result['category']} (<i>{result['description']}</i>)"
    else:
        reply_text = f"✅ <b>{amount_str}</b> | {result['category']} (<i>{result['description']}</i>)"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Batal", callback_data=f"cancel_{tx_id}")]
    ])

    await update.message.reply_html(reply_text, reply_markup=keyboard)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback buttons: undo, pagination, and period switching."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    if data == "page_noop":
        return

    # Riwayat pagination
    if data.startswith("page_"):
        page_num = int(data.replace("page_", ""))
        text, keyboard = build_riwayat_view(user_id, page=page_num)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        return

    # Cancel / Undo transaction
    if data.startswith("cancel_"):
        tx_id = data.replace("cancel_", "")
        deleted = delete_transaction(tx_id, user_id)
        if deleted:
            amount_str = f"Rp {int(deleted['amount']):,.0f}".replace(',', '.')
            await query.edit_message_text(
                f"🗑️ <b>Dibatalkan:</b> {amount_str} ({deleted['description']})",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text("⚠️ Transaksi sudah dibatalkan atau tidak ditemukan.")
        return

    # Period filters for Rekap
    if data in ["rekap_today", "rekap_week", "rekap_month", "rekap_last_month"]:
        period_map = {
            "rekap_today": "today",
            "rekap_week": "week",
            "rekap_month": "month",
            "rekap_last_month": "last_month"
        }
        await render_and_send_rekap(user_id=user_id, period=period_map[data], query=query)
        return

    if data == "rekap_pick_month":
        # Switch to month selection keyboard
        try:
            await query.edit_message_caption(
                caption="🗓️ <b>Pilih bulan yang ingin kamu lihat:</b>",
                parse_mode="HTML",
                reply_markup=get_month_picker_keyboard()
            )
        except Exception:
            pass
        return

    if data.startswith("rekap_custom_"):
        val = data.replace("rekap_custom_", "")  # e.g. '2026-08'
        await render_and_send_rekap(user_id=user_id, period="custom_month", custom_val=val, query=query)
        return

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("\n" + "=" * 60)
        print("❌ ERROR: TELEGRAM_BOT_TOKEN belum diset di file .env!")
        print("Salin .env.example menjadi .env lalu isi token bot dari @BotFather.")
        print("=" * 60 + "\n")
        return

    # Initialize Database
    init_db()
    print("Database siap (finance.db).")

    # Jalankan mini health-check server di background (wajib untuk Render 24/7)
    threading.Thread(target=run_health_server, daemon=True).start()

    # Build Telegram Bot Application
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("rekap", handle_rekap))
    app.add_handler(CommandHandler("riwayat", handle_riwayat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("🤖 Bot Telegram aktif & siap menerima pesan!")
    app.run_polling()

if __name__ == "__main__":
    main()
