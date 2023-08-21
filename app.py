from flask import Flask, request, redirect, session, url_for, render_template
import requests
import pandas as pd
from dotenv import load_dotenv
import os
from urllib.parse import quote
import time
import base64
import json

class Playlist:
    def __init__(self, playlist_data):
        self.data = playlist_data
        

    def get_song_ids(self):
        return [track["track"]["id"] for track in self.data["items"]]
    
    def get_name(self):
        return self.name
    
    def get_artist_ids(self):
        artist_ids = set()
        for track in self.data["items"]:
            for artist in track["track"]["artists"]:
                artist_ids.add(artist["id"])
        return list(artist_ids)
    
    def get_artist_popularities(self,artist_ids):
        token_info = session["TOKEN_INFO"]
        headers = {
        'Authorization': 'Bearer {token}'.format(token=token_info['access_token'])
        }
        ids_str = ','.join(artist_ids)

        iteration = 0
        artist_popularities = []

        while True:
            ids_str = ','.join(artist_ids[(iteration*50):(50+(iteration*50))])
            response = requests.get(f'https://api.spotify.com/v1/artists/?ids={ids_str}&limit=50&offset={iteration*50}',headers = headers)
            
            response_json = response.json()
            artists = response_json['artists']

            for artist in artists:
                popularity = artist["popularity"]
                artist_popularities.append(popularity)
            if(len(artists)<50):
                break
            iteration+=1

        return artist_popularities

    def get_song_popularities(self):
        track_popularities = []
        for track in self.data["items"]:
            track_popularities.append(track["track"]["popularity"])  
        return track_popularities

    # def get_genres(self):
    #     playlist_genres = []
    #     for track in self.data["items"]:
    #         playlist_genres += (track["album"]["genres"])
        
    
def get_playlist():
    
    token_info = session['TOKEN_INFO']
    headers = {
    'Authorization': 'Bearer {token}'.format(token=token_info['access_token'])
    }
    curr_user_playlists = session.get("CURR_USER_PLAYLISTS")
    
    SELECTED_PLAYLIST = request.form.get("playlist")
    SELECTED_PLAYLIST_ID = curr_user_playlists[SELECTED_PLAYLIST]
    fields = 'next,items(track(artists(id,href,name),popularity,id,name,href,album(genres),duration_ms))'
    playlist = {'items':[]}
    url = f'https://api.spotify.com/v1/playlists/{SELECTED_PLAYLIST_ID}/tracks?fields={fields}&limit=50'
    
    while url:
        response = requests.get(url, headers=headers)
        response_json = response.json()
        playlist_items = response_json["items"]
        for item in playlist_items:
            playlist["items"].append(item)
        url = response_json["next"]  # Fetch the next page URL from the response
        
    return Playlist(playlist)

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


def set_batch_limit(df:pd.DataFrame, airtime_ms: int, batch_size=5,):
    
    longest_5_duration = sum(df['track_duration_ms'].nlargest(5))
    num_full_seed_batches = len(df) // batch_size
    remainder_seed_batch = len(df) % batch_size
    remainder_indicator = 0
    
    if( remainder_seed_batch >0):
        remainder_indicator = 1
    if num_full_seed_batches == 0:
        batch_time_limit = airtime_ms/remainder_seed_batch
    else:
        batch_time_limit = airtime_ms/(num_full_seed_batches+remainder_indicator)

    if longest_5_duration>batch_time_limit:
        batch_time_limit = longest_5_duration

    return batch_time_limit

def get_recommendations(df: pd.DataFrame):
    token_info = session['TOKEN_INFO']
    headers = {
    'Authorization': 'Bearer {token}'.format(token=token_info['access_token'])
    }
    
    limit = 5
    market = 'US'
    iteration = 0
    offset = 5
    seed_track_offset = 0
    
    slider_value = int(request.form['range'])
    airtime_ms = int(request.form['airtime'])*60000
    
    recommendation_ids = []
    recommendation_duration = 0
    recommendation_names=[] 
    recommendation_popularities = []
    recommendation_uris = []
    
    
    BATCH_LIMIT = set_batch_limit(df = df, airtime_ms=airtime_ms)
    #batch_time_limit = BATCH_LIMIT
   
    df_recs = pd.DataFrame(data = {"recommendation_ids":[],"recommendation_uris":[],"recommendation_names":[],"recommendation_popularities":[],"recommendation_duration":[]})
    i = 1
    print(df["track_id"])

    while sum(df_recs["recommendation_duration"])<airtime_ms:    
        remaining_time = airtime_ms - sum(df_recs["recommendation_duration"])
        
        if remaining_time < BATCH_LIMIT:
            batch_time_limit = remaining_time
        else: batch_time_limit = BATCH_LIMIT
        print("current recommendation duration: ", sum(df_recs["recommendation_duration"])
)
        print("recommendation names: ", recommendation_names)
        batch_start_seed = seed_track_offset
        
        batch_end_seed = min(batch_start_seed + offset, len(df))
        print("indices: ", batch_start_seed, batch_end_seed)
        
        if batch_start_seed >= len(df['track_id']):
            seed_track_offset = 0
            continue
        
        if batch_end_seed == (len(df['track_id'])):
            seed_track_ids = df["track_id"].iloc[batch_start_seed:].tolist()
            batch_start_seed = seed_track_offset
            batch_end_seed == min(batch_start_seed + offset, len(df))
        else:
            seed_track_ids = df["track_id"].iloc[batch_start_seed:batch_end_seed].tolist()
        
        # Construct the seed_tracks string
        seed_tracks_str = ','.join(seed_track_ids)

        print("Constructed seed_tracks:", seed_tracks_str)
        

        url = f'https://api.spotify.com/v1/recommendations?limit={limit}&market={market}&seed_tracks={seed_tracks_str}&min_popularity=0&max_popularity={slider_value}&max_duration{airtime_ms-sum(df_recs["recommendation_duration"])}&fields=tracks(track(artists(id,href,name),popularity,id,name,href,uri,album(genres)))'
          
        response = requests.get(url,headers=headers)
        
        print("iteration_while: " + str(i) + '\n')
        print("iteration_seed: " + str(iteration) + '\n')
        i += 1
        print("seed tracks: "+seed_tracks_str)
        #print("duration remaining: "+ str(airtime_ms-recommendation_duration))
        print("current batch time remaining before next batch: "+ str(batch_time_limit))
        response_json = response.json()
        print(url)
        print(response_json)
        
        for track in response_json["tracks"]:

            track_duration_ms = int(track["duration_ms"])
            if track["id"] in df_recs["recommendation_ids"].values:
                continue
            
            if ((sum(df_recs["recommendation_duration"])) + track_duration_ms)>airtime_ms:
                #####end_while = True
                return df_recs
            
            elif remaining_time < BATCH_LIMIT:
                batch_time_limit = remaining_time
                
            elif (batch_time_limit - track_duration_ms) <= 0:
                iteration+=1
                batch_time_limit = set_batch_limit(df = df, airtime_ms= airtime_ms)
                break

            batch_time_limit -= track_duration_ms
            recommendation_ids.append(track["id"])
            recommendation_names.append(track["name"])
            recommendation_popularities.append(track["popularity"])
            recommendation_uris.append(track["uri"])
            
            new_row = {"recommendation_ids":track["id"],"recommendation_uris":track["uri"],"recommendation_names":track["name"],"recommendation_popularities":track["popularity"], "recommendation_duration":track_duration_ms}
            df_recs.loc[len(df_recs)] = new_row

            
            if True in df_recs.duplicated(subset = ["recommendation_ids","recommendation_names","recommendation_popularities"]).values:
                df = df.drop_duplicates(subset = ["recommendation_ids","recommendation_names"],ignore_index = True)
                continue
            print(track["name"] + " is added!")
            print("batch_time_limit : "+ str(batch_time_limit))
            print(f'new recommendation duration after adding {track["name"]} to the setlist: ', sum(df_recs["recommendation_duration"]))

        
            
        seed_track_offset = batch_end_seed
        
            
    return df_recs


def create_playlist(df_recs: pd.DataFrame):
    token_info = session['TOKEN_INFO']
    headers = {
    'Authorization': 'Bearer {token}'.format(token=token_info['access_token'])
    }
    USER_ID = session["CURRENT_USER_INFO"]['id']
    url = f'https://api.spotify.com/v1/users/{USER_ID}/playlists'
    SELECTED_PLAYLIST = request.form.get("playlist")
    # data = f'{{"name": "Playlist inspired by: {SELECTED_PLAYLIST} " ,"description": "New playlist description","public": false}}'
    playlist_data = {
    "name": f"Playlist inspired by: {SELECTED_PLAYLIST}",
    "description": "New playlist description",
    "public": False
}
    response = requests.post(url = url, data = json.dumps(playlist_data), headers = headers)
    new_playlist = response.json()
    uris = df_recs["recommendation_uris"].tolist()
    playlist_iframes = []
    if len(uris)>100:
        # Spotify's API allows adding a maximum of 100 tracks per request
        batch_size = 100
        for batch_start in range(0, len(uris), batch_size):
            batch_end = batch_start + batch_size
            batch_uris = uris[batch_start:batch_end]    

            body = f'{{"uris":{json.dumps(batch_uris)}}}'   
            add_tracks_url = f'https://api.spotify.com/v1/playlists/{new_playlist["id"]}/tracks'
            add_tracks_response = requests.post(add_tracks_url, data=body, headers=headers)
            #finished_playlist = add_tracks_response.json()


            iframe_src = f"https://open.spotify.com/embed/playlist/{new_playlist['id']}?utm_source=generator"
            iframe_code = f'<iframe style="border-radius: 12px" src="{iframe_src}" width="50%" height="352" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>'
            playlist_iframes.append(iframe_code)
    else:
        body = f'{{"uris":{json.dumps(uris)}}}'
        add_tracks_url = f'https://api.spotify.com/v1/playlists/{new_playlist["id"]}/tracks'
        add_tracks_response = requests.post(add_tracks_url, data=body, headers=headers)
        #finished_playlist = add_tracks_response.json()


        iframe_src = f"https://open.spotify.com/embed/playlist/{new_playlist['id']}?utm_source=generator"
        iframe_code = f'<iframe style="border-radius: 12px" src="{iframe_src}" width="50%" height="352" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>'
        playlist_iframes.append(iframe_code)
    add_tracks_url = f'https://api.spotify.com/v1/playlists/{new_playlist["id"]}/tracks'
    add_tracks_response = requests.post(add_tracks_url, data=body, headers=headers)

    #finished_playlist = add_tracks_response.json()
    print(playlist_iframes)
    return render_template("playlist_embed.html", playlist_iframes=playlist_iframes) #body







load_dotenv()
app = Flask(__name__,template_folder="templates")

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
    #session.pop('CURRENT_USER_INFO')
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

@app.route("/generate_setlist", methods = ["POST","GET"])
def generate_setlist():
    token_info = session["TOKEN_INFO"]
    headers = {
    'Authorization': 'Bearer {token}'.format(token=token_info['access_token'])
    }
    # # ====== RETRIEVE PLAYLIST SECTION ======

    playlist = get_playlist()
    playlist_data = playlist.data
    artist_ids = playlist.get_artist_ids()
    # song_ids = playlist.get_song_ids()
    # artist_pops = playlist.get_artist_popularities(artist_ids)
    # song_popularities = playlist.get_song_popularities()

    playlist_tracks = [track["track"] for track in playlist_data["items"]]
    df = pd.json_normalize(playlist_tracks,record_prefix = 'artist_',record_path = 'artists',meta_prefix = 'track_',meta = ['name','id','popularity','duration_ms'])
    df["order"] = (df['track_name'] != df['track_name'].shift()).cumsum()
    df = df.set_index("track_name")
    df = df.groupby(by=['track_name','track_id','order','track_popularity','track_duration_ms']).agg({"artist_name": lambda x: list(x),"artist_id":lambda x:list(x)}).rename({"artist_name":"artists_names"},axis=1).reset_index()
    df = df.sort_values("order",ascending=True).set_index("order")
    df_recs = get_recommendations(df = df)
    duration_sum = df_recs["recommendation_duration"].sum()
   
    return create_playlist(df_recs=df_recs)#render_template('index.html', dataframe=df_recs.to_html(),duration_sum = duration_sum)

######## NEXT STEP IS TO ACCESS THE PLAYLIST'S TRACK IDS, ARTIST IDS, AND AUDIO FEATURES SO THAT I CAN ITERATIVELY FEED THEM TO THE RECOMMENDATION 
######## ENGINE SO THAT IT WILL SPIT OUT RECOMMENDATIONS BASED ON THAT
