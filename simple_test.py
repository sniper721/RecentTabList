#!/usr/bin/env python3

from flask import Flask

app = Flask(__name__)

@app.route('/test')
def test():
    return "Test route working!"

@app.route('/recent_tab_roulette')
def recent_tab_roulette():
    return "Roulette route working!"

if __name__ == '__main__':
    app.run(debug=True, port=10001)