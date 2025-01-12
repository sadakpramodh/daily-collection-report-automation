import asyncio 

import os
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, CallbackContext, filters
from flask import Flask, request, jsonify

# Flask app for webhook
app = Flask(__name__)

# Define bot states
DATE = 1

# Function to fetch data
def fetch_data(from_date, to_date):
    try:
        session = requests.Session()
        url = "https://tirupati.emunicipal.ap.gov.in/ptis/report/dailyCollection"
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('meta', {'name': '_csrf'})['content']
        csrf_header = soup.find('meta', {'name': '_csrf_header'})['content']

        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            csrf_header: csrf_token,
            "x-requested-with": "XMLHttpRequest"
        }

        data = {
            "fromDate": from_date,
            "toDate": to_date,
            "collectionMode": "",
            "collectionOperator": "",
            "status": "",
            "revenueWard": "Revenue Ward No  18"
        }

        response = session.post(url, headers=headers, data=data, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to fetch data: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# Telegram bot handlers
async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Hi! Please send me a date in the format 'DD/MM/YYYY'.")
    return DATE

async def handle_date(update: Update, context: CallbackContext) -> int:
    date = update.message.text.strip()
    try:
        data = fetch_data(date, date)
        if "error" in data:
            await update.message.reply_text(f"Error: {data['error']}")
            return ConversationHandler.END

        # Process data
        grouped_data = defaultdict(lambda: {"count": 0, "totalAmount": 0, "owners": []})
        for entry in data:
            ward = entry['secretariatWard']
            grouped_data[ward]['count'] += 1
            grouped_data[ward]['totalAmount'] += entry['totalAmount']
            grouped_data[ward]['owners'].append(f"{entry['consumerName']} ({entry['consumerCode']})")

        # Send results
        for ward, details in grouped_data.items():
            message = (
                f"Secretariat: {ward}\n"
                f"No of bills: {details['count']}\n"
                f"Total Amount: {details['totalAmount']}\n"
                f"Owner details: {', '.join(details['owners'])}\n"
            )
            await update.message.reply_text(message)
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")
        return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Operation cancelled. Type /start to begin again.")
    return ConversationHandler.END

# Initialize the bot
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set!")

application = Application.builder().token(BOT_TOKEN).build()

# Conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
application.add_handler(conv_handler)

@app.route("/")
def home():
    return jsonify({"message": "Telegram Bot is running!"})

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    """Handle incoming Telegram updates."""
    update = Update.de_json(await request.get_json(), application.bot)
    await application.process_update(update)
    return "OK", 200
    
if __name__ == "__main__":
    # Set the webhook
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/webhook/{BOT_TOKEN}"
    asyncio.run(application.bot.set_webhook(webhook_url))
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
