from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import ssl
import json
import threading
from websocket import create_connection

app = Flask(__name__)
socketio = SocketIO(app)

# Function to connect to Bitfinex and listen to the order book
def connect_to_bitfinex():
    ssl_settings = ssl._create_unverified_context()

    try:
        ws = create_connection("wss://api-pub.bitfinex.com/ws/2", sslopt={"cert_reqs": ssl.CERT_NONE})
        ws.send(json.dumps({
            "event": "subscribe",
            "channel": "book",
            "symbol": "tETHBTC"
        }))
        print("Subscribed to BTC-ETH order book.")
        
        while True:
            result = ws.recv()
            data = json.loads(result)

            # Check if the message is a data update (a list) and not an event (a dictionary)
            if isinstance(data, list) and len(data) > 1:
                price_data = data[1]
                
                # Ensure the data is a list and has the correct length for [price, count, size]
                if isinstance(price_data, list) and len(price_data) >= 3:
                    price = price_data[0]  # The first item is the price
                    size = price_data[2]   # The third item is the size

                    # Ensure size is a number before processing
                    if isinstance(size, (int, float)):
                        # Emit bid and ask updates based on the size value
                        if size > 0:
                            socketio.emit('order_update', {'type': 'bid', 'price': price, 'size': size})
                        else:
                            socketio.emit('order_update', {'type': 'ask', 'price': price, 'size': abs(size)})

                        print(f"Received message from Bitfinex: Price: {price}, Size: {size}")

    except ssl.SSLError as e:
        print(f"SSL Error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

# Run the order book connection in a separate thread
@socketio.on('connect')
def handle_connect():
    print("Client connected")
    threading.Thread(target=connect_to_bitfinex).start()

if __name__ == '__main__':
    socketio.run(app, debug=True)