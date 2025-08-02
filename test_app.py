from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello World! Flask is working!"

if __name__ == '__main__':
    print("Starting minimal Flask test...")
    app.run(debug=True, host='127.0.0.1', port=5000)