import requests
import urllib.parse
import json

from datetime import datetime
from flask import Flask, render_template, redirect, request, jsonify, session
from openai import OpenAI
import os

client = OpenAI()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:5001/callback"

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE_URL = "https://api.spotify.com/v1/"

port = int(os.environ.get('PORT', 5000))
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)


@app.route("/")
def index():
    scope = "user-read-private user-read-email user-top-read playlist-modify-public playlist-read-private"

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": scope,
        "redirect_uri": REDIRECT_URI,
        "show_dialog": True
    }

    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)


@app.route("/callback")
def callback():
    if "error" in request.args:
        return jsonify({"error": request.args["error"]})
    
    if "code" in request.args:
        body_params = {
            "code": request.args["code"],
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }

    response = requests.post(TOKEN_URL, data=body_params)
    token_info = response.json()

    session["access_token"] = token_info["access_token"]
    session["refresh_token"] = token_info["refresh_token"]
    session["expires_at"] = datetime.now().timestamp() + token_info["expires_in"]

    return render_template("index.html")


@app.route("/recommendations")
def get_recommendations():
    age = request.args.get("age")

    if "access_token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh-token")
    
    headers = {
        "Authorization": f"Bearer {session['access_token']}"
    }

    # Get user's top 5 tracks
    time_range = "medium_term"
    
    track_params = {
        "time_range": time_range,
        "limit": 5
    }

    response = requests.get(API_BASE_URL + "me/top/tracks", headers=headers, params=track_params)
    top_tracks = response.json()

    top_track_names = [track["name"] for track in top_tracks["items"]]
    top_track_uris = [track["uri"] for track in top_tracks["items"]]

    top_track_ids = [uri[14:] for uri in top_track_uris]

    # Get audio features for user's age
    query = f"What would the danceability, energy and valence values be of the songs that a typical {age} year-old user listens to? Give me the results (in JSON) to pass into Spotify's API to generate music recommendations for the user. I want only one set of values. Only return the audio features without the 'JSON' title and any text. Call the field 'audio_features' so I can reference it."

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a smart assistant, knowledgeable in the music tastes of people of all ages."},
            {"role": "user", "content": query}
        ]
    )

    response = completion.choices[0].message.content
    age_audio_features = json.loads(response)["audio_features"]

    danceability = age_audio_features["danceability"]
    energy = age_audio_features["energy"]
    valence = age_audio_features["valence"]

    # Get 25 recommended tracks based on seed tracks and age
    recommendation_params = {
        "seed_tracks": ",".join(top_track_ids),
        "limit": 25,
        "target_danceability": danceability,
        "target_energy": energy,
        "target_valence": valence
    }

    response = requests.get(API_BASE_URL + "recommendations", headers=headers, params=recommendation_params)
    recommendations = response.json()

    recommendation_track_names = [track["name"] for track in recommendations["tracks"]]
    recommendation_track_uris = [track["uri"] for track in recommendations["tracks"]]

    recommendation_track_ids = [uri[14:] for uri in recommendation_track_uris]

    # Get audio features of recommended tracks (for debugging purposes)
    feature_params = {
        "ids": ",".join(recommendation_track_ids)
    }

    response = requests.get(API_BASE_URL + "audio-features", headers=headers, params=feature_params)
    recommendation_audio_features = response.json()

    danceability_values = [track["danceability"] for track in recommendation_audio_features["audio_features"]]
    energy_values = [track["energy"] for track in recommendation_audio_features["audio_features"]]
    valence_values = [track["valence"] for track in recommendation_audio_features["audio_features"]]

    recommendation_features = {}
    result = [top_track_names, {age: [danceability, energy, valence]}, recommendation_features]
    
    for i in range(10):
        recommendation_features[recommendation_track_names[i]] = [danceability_values[i], energy_values[i], valence_values[i]]

    # Get user's id
    response = requests.get(API_BASE_URL + "me", headers=headers)
    user_id = response.json()["id"]

    # Create a playlist for the user
    new_playlist_headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "Content-Type": "application/json"
    }

    playlist_params = {
        "name": f"Age {age} recommendations",
        "description": "Made by Sidharth"
    }

    response = requests.post(API_BASE_URL + f"users/{user_id}/playlists", headers=new_playlist_headers, json=playlist_params)

    # Get user's playlists
    response = requests.get(API_BASE_URL + "me/playlists", headers=headers)
    playlists = response.json()["items"]

    possible_playlist_ids = []
    for playlist in playlists:
        if playlist["name"] == f"Age {age} recommendations":
            possible_playlist_ids.append(playlist["id"])         
    
    playlist_id = possible_playlist_ids[0]

    # Add recommended tracks to the created playlist
    add_track_params = {
        "uris": recommendation_track_uris
    }

    response = requests.post(API_BASE_URL + f"playlists/{playlist_id}/tracks", headers=new_playlist_headers, json=add_track_params)

    playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
    return redirect(playlist_url)
   

@app.route("/refresh-token")
def refresh_token():
    if "refresh_token" not in session:
        return redirect("/")
    
    body_params = {
        "grant_type": "refresh_token",
        "refresh_token": session["refresh_token"],
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    response = requests.post(TOKEN_URL, data=body_params)
    new_token_info = response.json()

    session["access_token"] = new_token_info["access_token"]
    session["expires_at"] = datetime.now().timestamp() + new_token_info["expires_in"]

    return redirect("/recommendations")


