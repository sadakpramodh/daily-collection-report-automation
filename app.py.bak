import os
import http.server
import socketserver
from threading import Thread
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, CallbackContext, filters
from telegram import Update
from collections import defaultdict
import requests
from bs4 import BeautifulSoup

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

def start_bot():
    # Retrieve the bot token from the environment
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set!")

    # Initialize the application
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

    # Start polling
    application.run_polling()

def start_server():
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Background worker is running.")

    port = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"Serving HTTP on port {port}")
        httpd.serve_forever()

if __name__ == "__main__":
    # Start the HTTP server in a separate thread
    Thread(target=start_server, daemon=True).start()

    # Start the Telegram bot
    start_bot()
