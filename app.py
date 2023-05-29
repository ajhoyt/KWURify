from flask import Flask, request, redirect, session, url_for, render_template
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
USER_ID = "user_id"

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
    return redirect(url_for("choose_playlist",_external = True))

    


@app.route("/choose_playlist")
def choose_playlist():
    
    ## BRING IN TOKEN INFO FROM SESSION
    token_info = session["TOKEN_INFO"]
    
    
    ## HEADERS WITH TOKEN FOR ALL FURTHER API CALLS
    headers = {
    'Authorization': 'Bearer {token}'.format(token=token_info['access_token'])
}
    
    ##GET CURRENT USER ID. THIS IS NECESSARY FOR FURTHER API CALLS
    curr_user_response =  requests.get('https://api.spotify.com/v1/me',headers=headers)
    session["CURRENT_USER_INFO"] = curr_user_response.json()
    session["USER_ID"] = session["CURRENT_USER_INFO"]['id']

    #curr_user_playlists_response = requests.get(f'https://api.spotify.com/v1/users/{session["USER_ID"]}/playlists?limit=50&offset={0}',headers = headers)
    #curr_user_playlists_json = curr_user_playlists_response.json()
    
    ## GET USER PLAYLISTS
    curr_user_playlists = {}
    iteration = 0
    while True:
        curr_user_playlists_response = requests.get(f'https://api.spotify.com/v1/users/{session["USER_ID"]}/playlists?limit=50&offset={iteration*50}',headers = headers)
        curr_user_playlists_json = curr_user_playlists_response.json()

        items = curr_user_playlists_json['items']
        iteration += 1
        all_playlists = []
        for playlist in items:
            all_playlists.append(playlist)
            playlist_is_owned_by_user = playlist['owner']['id'] == session["USER_ID"]
            is_collaborative = playlist["collaborative"]==True
            if playlist_is_owned_by_user or is_collaborative:
                curr_user_playlists[playlist['name']]=playlist['id']
        if(len(items)<50):
            break
    
    ##
    session["USER_PLAYLISTS_NAME_AND_ID"] = curr_user_playlists
    return render_template("choose_playlist.html", playlists=curr_user_playlists)

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

@app.route("/generate_setlist", methods = ["POST"])
def generate_setlist():
    selected_playlist = request.form.get("playlist")
    selected_playlist_id = session["USER_PLAYLISTS_NAME_AND_ID"][selected_playlist]

    return "selected playlist: " + selected_playlist +"and it's id: " + selected_playlist_id