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
        curr_user_playlists_response = requests.get(f'https://api.spotify.com/v1/users/{USER_ID}/playlists?limit=50&offset={iteration*50}',headers = headers)
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






@app.route("/generate_setlist", methods = ["POST","GET"])
def generate_setlist():
    token_info = session['TOKEN_INFO']
    headers = {
    'Authorization': 'Bearer {token}'.format(token=token_info['access_token'])
    }
    curr_user_playlists = session.get("CURR_USER_PLAYLISTS")


    #if request.method == "POST":
    SELECTED_PLAYLIST = request.form.get("playlist")
    SELECTED_PLAYLIST_ID = curr_user_playlists[SELECTED_PLAYLIST]
    response = requests.get(f'https://api.spotify.com/v1/playlists/{SELECTED_PLAYLIST_ID}',headers = headers)
    playlist_json = response.json()
    # tracklist = playlist_json["tracks"]["items"]
    # track_artists = []
    # track_name = []
    # #track_popularity_score = []
    
    # track_ids = []
 
    # artist_ids = []
    # artist_popularities = []
    # # for track in tracklist:
    # #     track = track["track"]
    # #     artists = track['artists']
    # #     for artist in artists:
    # #         artist_id = artist['id']
    # #         artist_ids.append(artist_id)
    # #         artist_popularity = artist['popularity']
    # #         artist_popularities.append(artist_popularities)
    # #     track_id = track['id']
    # #     track_ids.append(track_id)
    #     #test_return.append(f"{track['artists'][0]['name']}'s artist ID is: {track['artists'][0]['id']}\n and their song {track['name']}'s song ID is {track['id']}")
    
    playlist = playlist_json["tracks"]["items"]
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
        
    return  valid_track_ids#f"artists ids:{artist_ids},\n song ids: {track_ids}" 
        # track = track["track"]
        # track_artists.append(track['artists'])
        # track_name.append(track['name'])
        # #track_popularity_score.append(track['popularity'])
        # track_url.append(str(track['external_urls']['spotify']))
        # artist_count.append(len(track['artists']))
        # track_id.append(track["id"])
        #return f"{tracklist[track]['track']['artists'][0]['name']}'s artist ID is: {tracklist[track]['track']['artists'][0]['id']}\n and their song {tracklist[track]['track']['name']}'s song ID is {tracklist[track]['track']['id']}"
        
    #return tracklist
    
    #f"{tracklist[0]['track']['artists'][0]['name']}'s artist ID is: {tracklist[0]['track']['artists'][0]['id']}\n and their song {tracklist[0]['track']['name']}'s song ID is {tracklist[0]['track']['id']}"
        
        #return "selected playlist: " + selected_playlist + "\n id = : "+selected_playlist_id#+"and it's id: " + selected_playlist_id
    # tracklist = session["USER_PLAYLISTS_NAME_AND_ID"]
    # track_artists = []
    # track_name = []
    # track_popularity_score = []
    # track_url = []
    # track_id = []
    # artist_name = []
    # artist_count = []
    # artist_ids = []
    # artist_popularity = []
    # for track in tracklist:
        
    #     track_artists.append(track['artists'])
    #     track_name.append(track['name'])
    #     track_popularity_score.append(track['popularity'])
    #     track_url.append(str(track['external_urls']['spotify']))
    #     artist_count.append(len(track['artists']))
    #     track_id.append(track["id"])
    
    #     # if len(track['artists'])<=1:
    #     #     artist_name.append(track['artists'][0]['name'])
    #     # else:
    #     artists = []
    #     ids = []
    #     popularities = []

    #     for artist in track['artists']:
    #         artists.append(artist['name'])
    #         id = artist['id']
    #         ids.append(id)
    #         artist_response = requests.get(f'https://api.spotify.com/v1/artists/{id}',headers=headers)
    #         artist_json_response=artist_response.json()
    #         popularities.append(artist_json_response['popularity'])
        
    #     artist_popularity.append(popularities)
    #     artist_name.append(artists)
    #     artist_ids.append(ids)
        
    #     if(len(track['artists'])>1):
    #         print('multiple artists for: '+ track['name'])


    # pd.DataFrame(list(zip(track_name,track_popularity_score,track_url,track_id,artist_name,artist_ids,artist_popularity,artist_count)),
    #             columns = ["track_name","track_popularity_score","track_url","track_ids","artist_names","artist_ids","artist_popularity","artist_count"])


    # df = pd.DataFrame()
    
    # return "selected playlist: " + selected_playlist,print("id = :"+ curr_user_playlists[selected_playlist]) #+"and it's id: " + selected_playlist_id#, render_template('table.html',,  tables=[df.to_html(classes='data')], titles=df.columns.values)



######## NEXT STEP IS TO ACCESS THE PLAYLIST'S TRACK IDS AND ARTIST IDS SO THAT I CAN ITERATIVELY FEED THEM TO THE RECOMMENDATION 
######## ENGINE SO THAT IT WILL SPIT OUT RECOMMENDATIONS BASED ON THAT