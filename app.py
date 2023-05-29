from flask import Flask, request, redirect, session, url_for
import requests
import pandas as pd
from dotenv import load_dotenv
import os
from urllib.parse import quote
import time
import string
import random
import base64

load_dotenv()
app = Flask(__name__)



API_URL = 'https://accounts.spotify.com/api/token'
REDIRECT_URI = "http://localhost:5000/redirect"
AUTH_URL = 'https://accounts.spotify.com/authorize?'
RECOMMENDATIONS_URL = "https://api.spotify.com/v1/recommendations?"
PLAYLIST_URL = f"https://api.spotify.com/v1/users/{USER_ID}/playlists"
seed_artists = "3kzwYV3OCB010YfXMF0Avt,77mJc3M7ZT5oOVM7gNdXim" 
seed_artists = '3TVXtAsR1Inumwj472S9r4,1URnnhqYAYcrqrcwql10ft'
seed_tracks = []
limit = 100
min_popularity = 5
max_popularity = 22


app.secret_key = os.getenv('APP_SECRET')
app.config["SESSION_COOKIE_NAME"] = "My KWUR Cookies"
TOKEN_INFO = "token_info"
CURRENT_USER_INFO = "current_user_info"
USER_ID = session['CURRENT_USER_ID']

@app.route("/")
def login():
    query = f"{AUTH_URL}client_id={os.getenv('CLIENT_ID')}&response_type=code&redirect_uri={REDIRECT_URI}&scope={quote(os.getenv('SCOPE'))}"
    
    return redirect(query)

@app.route("/redirect")
def redirect_page():
    query = f"{AUTH_URL}client_id={os.getenv('CLIENT_ID')}&response_type=code&redirect_uri={REDIRECT_URI}&scope={quote(os.getenv('SCOPE'))}"
    oauth_code = requests.get(query)
    session.clear()
    code = request.args.get('code')
    headers = {
        'Authorization': 'Basic '+ base64.b64encode(f'{os.getenv("CLIENT_ID")}:{os.getenv("CLIENT_SECRET")}'.encode('utf-8')).decode('utf-8'),
        "Content-Type":  "application/x-www-form-urlencoded"
    }    
    response = requests.post(f'{API_URL}?client_id={os.getenv("CLIENT_ID")}&client_secret={os.getenv("CLIENT_SECRET")}&grant_type=authorization_code&code={code}&redirect_uri={REDIRECT_URI}',headers = headers)
    session["TOKEN_INFO"] = response.json()
    access_token = session.get('TOKEN_INFO')['access_token']
    return redirect(url_for("generate_setlist",_external = True))

    
def get_token():
    token_info = session.get("TOKEN_INFO",None)
    if not token_info:
        raise "exception"
    now = int(time.time())
    is_expired = token_info['expires_at']-now < 60
    if (is_expired):
        headers = {
            'Authorization': 'Basic '+ base64.b64encode(f'{os.getenv("CLIENT_ID")}:{os.getenv("CLIENT_SECRET")}'.encode('utf-8')).decode('utf-8'),
            "Content-Type":  "application/x-www-form-urlencoded"
        }    
        response = requests.post(f'{API_URL}&grant_type=refresh_token&refresh_token={token_info["refresh_token"]}',headers = headers)
        
    return response.text


@app.route("/generate_setlist")
def generate_setlist():
    token_info = session["TOKEN_INFO"]
    headers = {
    'Authorization': 'Bearer {token}'.format(token=token_info['access_token'])
}
    response =  requests.get('https://api.spotify.com/v1/me',headers=headers)
    session["CURRENT_USER_INFO"] = response.json()
    session["USER_ID"] = session["CURRENT_USER_INFO"]['id']

    return session["CURRENT_USER_INFO"]