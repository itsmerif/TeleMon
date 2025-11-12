from flask import Flask, render_template, request, jsonify
import sqlite3
from telethon.sync import TelegramClient
from telethon import events
#itsmeRiF
import asyncio
import threading
from datetime import datetime

app = Flask(__name__)

# Telegram API configurations
api_id = '' # insert your API_ID here as discussed in class
api_hash = '' # insert your api_hash here as discussed in class
phone_number = '+91XXXXXXXXXX' # insert your phone number associated with the Telegram account. If Indian number, use +91, else use the relevant country code of your number. For ex: For US/Canada-based mobile number, use +1

KEYWORDS_FILE = 'keywords.txt'
CHANNELS_FILE = 'channels.txt'

def get_db_connection():
    conn = sqlite3.connect('monitor.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload_keywords', methods=['POST'])
def upload_keywords():
    file = request.files['file']
    if file:
        lines = file.read().decode('utf-8').splitlines()
        conn = get_db_connection()
        cursor = conn.cursor()
        for line in lines:
            cursor.execute("INSERT INTO keywords (keyword) VALUES (?)", (line.strip(),))
        conn.commit()
        conn.close()
        return jsonify({"message": "Keywords uploaded successfully!"})

@app.route('/upload_channels', methods=['POST'])
def upload_channels():
    file = request.files['file']
    if file:
        lines = file.read().decode('utf-8').splitlines()
        conn = get_db_connection()
        cursor = conn.cursor()
        for line in lines:
            cursor.execute("INSERT INTO channels (channel) VALUES (?)", (line.strip(),))
        conn.commit()
        conn.close()
        return jsonify({"message": "Channels uploaded successfully!"})

@app.route('/get_matched_data', methods=['GET'])
def get_matched_data():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    urls_only = request.args.get('urls_only', 'false').lower() == 'true'
    no_urls = request.args.get('no_urls', 'false').lower() == 'true'

    offset = (page - 1) * limit

    query = "SELECT channel, message, date FROM matched_data WHERE 1=1"
    params = []

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if urls_only:
        query += " AND message LIKE '%http%'"
    if no_urls:
        query += " AND message NOT LIKE '%http%'"

    query += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    conn = sqlite3.connect('monitor.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    data = [{'channel': row[0], 'message': row[1], 'date': row[2]} for row in rows]
    return jsonify({'data': data})


    
    offset = (page - 1) * limit
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Base query
    query = "SELECT * FROM matched_data WHERE 1=1"

    # Add filters for date range
    if start_date and end_date:
        query += " AND date BETWEEN ? AND ?"
        cursor.execute(query, (start_date, end_date))
    else:
        cursor.execute(query)

    # Filter messages that contain URLs
    if urls_only:
        query += " AND message LIKE '%http%'"
        cursor.execute(query)
    
    # Apply pagination
    query += f" ORDER BY date DESC LIMIT ? OFFSET ?"
    cursor.execute(query, (limit, offset))

    matched_data = cursor.fetchall()

    # Get total count of matched data for pagination
    cursor.execute("SELECT COUNT(*) FROM matched_data")
    total_count = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        'data': [dict(row) for row in matched_data],
        'total_count': total_count
    })

# Helper functions to load keywords and channels from text files
def load_keywords():
    try:
        with open(KEYWORDS_FILE, 'r') as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        return []

def load_channels():
    try:
        with open(CHANNELS_FILE, 'r') as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        return []

# Telegram Monitoring
async def monitor_channels():
    # Initialize the Telegram client
    client = TelegramClient(phone_number, api_id, api_hash)
    await client.start()

    async def handler(event):
        # Get the message text and channel name
        if event.raw_text:
            message_text = event.raw_text
            channel_name = event.chat.title if event.chat else "Unknown Channel"
            
            # Check if the message contains any of the keywords
            keywords = load_keywords()
            if any(keyword.lower() in message_text.lower() for keyword in keywords):
                # Insert the matched message into the database
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO matched_data (channel, message, date) VALUES (?, ?, ?)",
                    (channel_name, message_text, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
                conn.close()
                print(f"Saved matched message: {message_text} from {channel_name}")
    
    # Fetching old messages from channels
    async def fetch_old_messages(channel):
        try:
            entity = await client.get_entity(channel)
            async for message in client.iter_messages(entity, limit=100):
                if message.text:
                    channel_name = entity.title if hasattr(entity, 'title') else "Unknown Channel"
                    keywords = load_keywords()
                    if any(keyword.lower() in message.text.lower() for keyword in keywords):
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO matched_data (channel, message, date) VALUES (?, ?, ?)",
                            (channel_name, message.text, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        )
                        conn.commit()
                        conn.close()
        except Exception as e:
            print(f"Error fetching messages from {channel}: {e}")

    # Load channels from the file
    channels = load_channels()

    # Process all channels
    for channel in channels:
        await fetch_old_messages(channel)

    # Add event handler for new messages
    client.add_event_handler(handler, events.NewMessage)
    print("Listening to messages...")
    await client.run_until_disconnected()

# Start Telegram monitor in a separate thread
def run_telegram_monitor():
    asyncio.run(monitor_channels())

if __name__ == '__main__':
    # Start the Telegram monitoring thread
    telegram_thread = threading.Thread(target=run_telegram_monitor)
    telegram_thread.start()

    # Start Flask in the main thread
    app.run(debug=True, use_reloader=False)
