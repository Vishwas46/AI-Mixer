# test_spotify.py
import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# This is the exact same setup code from your script
def get_spotify_client():
    load_dotenv()
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    
    print(f"Loaded Client ID: {client_id}")
    if client_secret:
        print(f"Loaded Client Secret: ...{client_secret[-4:]}")
    else:
        print("Client Secret was NOT loaded!")

    if not client_id or not client_secret:
        raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env file")

    client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# --- Main test ---
try:
    print("Attempting to initialize Spotify client...")
    spotify = get_spotify_client()
    print("Client initialized successfully. Now searching for a track...")
    results = spotify.search(q='artist:queen', type='artist')
    print("Search successful!")
    print(results)
except Exception as e:
    print("\n--- TEST FAILED ---")
    print(f"An error occurred: {e}")