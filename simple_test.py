from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "<h1>Test Server Working!</h1><p>If you see this, Flask is working correctly.</p>"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10001)