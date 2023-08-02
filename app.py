from flask import Flask, request, redirect, session, url_for, render_template
import requests
import pandas as pd
from dotenv import load_dotenv
import os
from urllib.parse import quote
import time
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
CURR_USER_PLAYLISTS = 'curr_user_playlists'

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
    #access_token = session.get('TOKEN_INFO')['access_token']
    return redirect(url_for("choose_playlist",_external = True))

    


@app.route("/choose_playlist")
def choose_playlist():
    
    ## BRING IN TOKEN INFO FROM SESSION
    token_info = session["TOKEN_INFO"]
    session.clear()
    
    ## HEADERS WITH TOKEN FOR ALL FURTHER API CALLS
    headers = {
    'Authorization': 'Bearer {token}'.format(token=token_info['access_token'])
    }
    
    ##GET CURRENT USER ID. THIS IS NECESSARY FOR FURTHER API CALLS
    curr_user_response =  requests.get('https://api.spotify.com/v1/me',headers=headers)
    session["CURRENT_USER_INFO"] = curr_user_response.json()
    USER_ID = session["CURRENT_USER_INFO"]['id']
    session.pop('CURRENT_USER_INFO')
    #curr_user_playlists_response = requests.get(f'https://api.spotify.com/v1/users/{session["USER_ID"]}/playlists?limit=50&offset={0}',headers = headers)
    #curr_user_playlists_json = curr_user_playlists_response.json()
    
    ## GET USER PLAYLISTS
    curr_user_playlists = {}
    iteration = 0
    while True:
        curr_user_playlists_response = requests.get(f'https://api.spotify.com/v1/me/playlists?limit=50&offset={iteration*50}',headers = headers)
        curr_user_playlists_json = curr_user_playlists_response.json()
        #session['CURR_USER_PLAYLISTS']=curr_user_playlists_json
        items = curr_user_playlists_json['items']

        iteration += 1
        all_playlists = []
        for playlist in items:
            all_playlists.append(playlist)
            playlist_is_owned_by_user = playlist['owner']['id'] == USER_ID
            is_collaborative = playlist["collaborative"]==True
            if playlist_is_owned_by_user or is_collaborative:
                curr_user_playlists[playlist['name']]=playlist['id']
        if(len(items)<50):
            break
    session['CURR_USER_PLAYLISTS'] = curr_user_playlists
    session['TOKEN_INFO'] = token_info
    
    return render_template("choose_playlist.html", playlists=curr_user_playlists.keys())

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



def get_artists_popularities(ids:list):
    
    ids = ','.join(ids)

    token_info = session["TOKEN_INFO"]
    headers = {
    'Authorization': 'Bearer {token}'.format(token=token_info['access_token'])
    }

    response = requests.get(f'https://api.spotify.com/v1/artists/?ids={ids}',headers = headers)
    response_json = response.json()
    artists = response_json['artists']
    popularities = []
    for artist in artists:
        popularity = artist["popularity"]
        popularities.append(popularity)
    return popularities


def get_recommendations(df: pd.DataFrame):
    
    # columns = ["track_name","track_id","track_popularity","artists_names","artist_id",
    #            "track_danceability","track_energy","track_key","track_loudness","track_mode",
    #            "track_speechiness","track_acousticness","track_instrumentalness","track_liveness",
    #            "track_valence","track_tempo","track_analysis_url",
    #            "track_duration_ms","track_time_signature"]
    



    pass



@app.route("/generate_setlist", methods = ["POST","GET"])
def generate_setlist():
    
    # ====== RETRIEVE PLAYLIST SECTION ======

    token_info = session['TOKEN_INFO']
    headers = {
    'Authorization': 'Bearer {token}'.format(token=token_info['access_token'])
    }
    curr_user_playlists = session.get("CURR_USER_PLAYLISTS")
    
    SELECTED_PLAYLIST = request.form.get("playlist")
    SELECTED_PLAYLIST_ID = curr_user_playlists[SELECTED_PLAYLIST]
    response = requests.get(f'https://api.spotify.com/v1/playlists/{SELECTED_PLAYLIST_ID}',headers = headers)
    playlist_json = response.json()
    playlist = playlist_json["tracks"]["items"]

    # ====== FILTER OUT POPULAR SONGS SECTION ======

    valid_artist_ids = []
    valid_track_ids = []
    for track in playlist:
        
        curr_track = track["track"] 
        curr_track_popularity = curr_track["popularity"]
        curr_track_too_popular = curr_track_popularity > 50
        if curr_track_too_popular:
            continue
        else:
            curr_track_artists = curr_track['artists']
            curr_artists_ids = [curr_artist['id'] for curr_artist in curr_track_artists]
            curr_artists_popularities = get_artists_popularities(curr_artists_ids)
            curr_artists_too_popular = any(curr_artist_popularity>50 for curr_artist_popularity in curr_artists_popularities )
                
            if curr_artists_too_popular:
                continue
        
        curr_track_id = curr_track['id']
        valid_track_ids.append(curr_track_id)
    
    # ====== CREATE VALID SONG TABLE SECTION ======

    valid_playlist = [track["track"] for track in playlist if track['track']['id'] in valid_track_ids]

    df_tracks = pd.json_normalize(valid_playlist,record_prefix = 'artist_',record_path = 'artists',meta_prefix = 'track_',meta = ['name','id','popularity'])
    df_tracks["order"] = (df_tracks['track_name'] != df_tracks['track_name'].shift()).cumsum()
    df_tracks = df_tracks.set_index("track_name")
    df_tracks = df_tracks.groupby(by=['track_name','track_id','order','track_popularity']).agg({"artist_name": lambda x: list(x),"artist_id":lambda x:list(x)}).rename({"artist_name":"artists_names"},axis=1).reset_index()
    df_tracks = df_tracks.sort_values("order",ascending=True)

    valid_track_ids_str = ','.join(valid_track_ids)
    audio_features_response = requests.get(f'https://api.spotify.com/v1/audio-features?ids={valid_track_ids_str}',headers=headers) 
    audio_features_response_json = audio_features_response.json()
    df_audio_features = pd.DataFrame(data = audio_features_response_json["audio_features"]).drop(columns=["track_href", "type", "uri"]).add_prefix("track_")
    df_main = df_tracks.merge(df_audio_features,on="track_id").set_index("order")
    
    
    #### FIGURE OUT HOW TO ACCESS EACH ARTIST ID USING EXPLODE TO GET ADD EACH ARTIST POPULARITY TO AN ARRAY 
    #### TO ADD LIST AS COLUMN USING DF.INSERT(DF.COLUMNS.GET_LOC("COLUMN_NAME"),"INSERTED_COLUMN_NAME",LIST) TO MAIN_DF
    #### THIS DATAFRAME IS ONLY THE UNPOPULAR SONGS FROM THE GIVEN PLAYLIST. NEW PLAYLIST SHOULD BE INSPIRED BY THE ENTIRE PLAYLIST, NOT JUST THE UNPOPULAR SONGS
    ####

    ## artist_popularities = [] 
    # [artist_popularities.append(requests.get("https://api.spotify.com/v1/artists/{artist_id}?",headers=headers).json()["popularity"]) for popularity in pd
    ###### YOU ALREADY WROTE GET_ARTIST_POPULARTIES()
    
    # list1 = []
    # list1.append(requests.get("https://api.spotify.com/v1/artists/0UVthdD1eqqsoNLX9ek4Xb?",headers=headers).json()["popularity"])
    

    # ====== RECOMMENDATION SECTION ======
    

    return render_template('index.html', dataframe=df_main.to_html())


######## NEXT STEP IS TO ACCESS THE PLAYLIST'S TRACK IDS, ARTIST IDS, AND AUDIO FEATURES SO THAT I CAN ITERATIVELY FEED THEM TO THE RECOMMENDATION 
######## ENGINE SO THAT IT WILL SPIT OUT RECOMMENDATIONS BASED ON THAT
