import os
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

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
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Hi! Please send me a date in the format 'DD/MM/YYYY'.")
    return DATE

def handle_date(update: Update, context: CallbackContext) -> int:
    date = update.message.text.strip()
    try:
        data = fetch_data(date, date)
        if "error" in data:
            update.message.reply_text(f"Error: {data['error']}")
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
            update.message.reply_text(message)
        return ConversationHandler.END
    except Exception as e:
        update.message.reply_text(f"An error occurred: {e}")
        return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Operation cancelled. Type /start to begin again.")
    return ConversationHandler.END

def main():
    # Retrieve the bot token from the environment
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set!")

    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            DATE: [MessageHandler(Filters.text & ~Filters.command, handle_date)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
