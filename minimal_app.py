#!/usr/bin/env python3

from flask import Flask, session, redirect, url_for

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-secret-key'

@app.route('/recent_tab_roulette', methods=['GET', 'POST'])
def recent_tab_roulette():
    """Recent Tab Roulette - Progressive challenge system like extreme demon roulette"""
    print("DEBUG: recent_tab_roulette route called")
    return "Roulette route working!"

if __name__ == '__main__':
    app.run(debug=True, port=10002)