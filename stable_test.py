# stable_test.py
import os
import requests
import sys
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

def run_test():
    load_dotenv()
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    print(f"Using Client ID from .env file")

    if not client_id or not client_secret or "YOUR_CLIENT" in client_id:
        print("ERROR: Please set your credentials in the .env file.", file=sys.stderr)
        return

    try:
        print("Initializing Spotify client...")
        sp = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(client_id, client_secret)
        )

        track_name = "Kantara - Varaha Roopam"
        print(f"✅ Client initialized. Searching for '{track_name}'...")
        
        results = sp.search(q=track_name, type='track', limit=1)
        track_id = results['tracks']['items'][0]['id']
        print(f"✅ Search successful. Found track ID: {track_id}")

        print("Requesting audio features for this track...")
        token_info = sp.auth_manager.get_access_token(as_dict=True)
        access_token = token_info["access_token"]
        r = requests.get(
            "https://api.spotify.com/v1/audio-features",
            params={"ids": track_id},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        print(r.status_code, r.text)
        print("Token obtained with client credentials:", token_info is not None)
        features = sp.audio_features([track_id])
        print("Audio features response:", features)
        
        if features and features[0]:
            print("\n✅✅✅ SUCCESS! Audio features received successfully.")
            print(f"BPM: {features[0]['tempo']}")
        else:
            print("\n❌ FAILED: Received an empty response for audio features.")

    except Exception as e:
        print(f"\n❌ FAILED: An exception occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    run_test()
