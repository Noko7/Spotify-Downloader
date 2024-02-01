import os
import urllib.request
import requests
import re
import string
from tkinter import Tk, ttk, filedialog, StringVar
from pytube import YouTube
from dotenv import load_dotenv
from spotipy import SpotifyOAuth
from spotipy.oauth2 import SpotifyOauthError

# Load environment variables
load_dotenv(dotenv_path='.env')

# Setup Spotify API credentials
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = os.getenv("REDIRECT_URL")

# Create an instance of the SpotifyOAuth class
try:
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="user-library-read playlist-read-private playlist-read-collaborative",
    )
except SpotifyOauthError as e:
    print(f"Spotify OAuth setup error: {e}")
    exit(1)

# Get access token
token_info = sp_oauth.get_cached_token()
if not token_info:
    auth_url = sp_oauth.get_authorize_url()
    print("Please go to this URL and authorize the app:", auth_url)
    auth_code = input("Enter the authorization code: ")
    token_info = sp_oauth.get_access_token(auth_code)

access_token = token_info["access_token"]
playlists = {}

def get_auth_header(token):
    return {"Authorization": "Bearer " + token}

# Function to update the dropdown menu
def update_playlist_dropdown():
    playlist_names = list(playlists.keys())
    playlist_menu = playlist_dropdown["menu"]
    playlist_menu.delete(0, "end")
    for name in playlist_names:
        playlist_menu.add_command(label=name, 
                                  command=lambda value=name: selected_playlist.set(value))
    if playlist_names:
        selected_playlist.set(playlist_names[0])

# Function to fetch user playlists
def get_user_playlists(token):
    print("Retrieving user playlists...")
    headers = get_auth_header(token)
    response = requests.get("https://api.spotify.com/v1/me/playlists", headers=headers)
    response_json = response.json()
    for item in response_json["items"]:
        playlists[item["name"]] = item["id"]
    print("Playlists retrieved successfully.")
    update_playlist_dropdown()

def sanitize_filename(filename):
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    return ''.join(c for c in filename if c in valid_chars)


# Global variable to control the downloading process
is_downloading = True

def stop_downloading():
    global is_downloading
    is_downloading = False
    status_label.config(text="Downloading stopped.")

def get_playlist_tracks(token, playlist_id):
    print(f"Retrieving tracks for playlist ID: {playlist_id}")
    headers = get_auth_header(token)
    response = requests.get(f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks", headers=headers)
    response_json = response.json()
    tracks = []
    for item in response_json["items"]:
        track = item["track"]
        tracks.append((track["name"], track["artists"][0]["name"]))
    print("Tracks retrieved successfully.")
    return tracks

    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    return ''.join(c for c in filename if c in valid_chars)

def download_songs(selected_playlist):
    global is_downloading
    is_downloading = True
    status_label.config(text="Downloading...")

    user_path = path_label.cget("text")
    download_folder = os.path.join(user_path, sanitize_filename(selected_playlist).replace(" ", "_"))
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    playlist_id = playlists[selected_playlist]
    tracks = get_playlist_tracks(access_token, playlist_id)

    for track in tracks:
        if not is_downloading:
            print("Downloading stopped by user.")
            break

        sanitized_track_name = sanitize_filename(f"{track[1]} - {track[0]}")
        final_file = os.path.join(download_folder, f"{sanitized_track_name}.mp3")

        # Check if the file already exists
        if os.path.exists(final_file):
            print(f"Skipping, already downloaded: {final_file}")
            continue

        try:
            print(f"Processing {track[0]} by {track[1]}...")
            search_query = urllib.parse.quote(f"{track[0]} {track[1]}")
            html = urllib.request.urlopen(f"https://www.youtube.com/results?search_query={search_query}")
            video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
            for video_id in video_ids:
                try:
                    yt = YouTube(f"https://youtube.com/watch?v={video_id}")
                    temp_file = os.path.join(download_folder, "temp.mp4")
                    yt.streams.filter(only_audio=True).first().download(output_path=download_folder, filename="temp.mp4")
                    if os.path.exists(temp_file):
                        os.rename(temp_file, final_file)
                        print(f"Downloaded successfully: {final_file}")
                        break
                    else:
                        print(f"Temporary file not found: {temp_file}")
                except Exception as e:
                    print(f"Error downloading video: {e}")
                    continue
        except Exception as e:
            print(f"Error processing track {track}: {e}")

    status_label.config(text="Download completed.")
def select_path():
    global path_label
    path = filedialog.askdirectory()
    path_label.config(text=path)

# GUI setup
screen = Tk()
screen.title('Spotify Downloader')
screen.geometry("600x400")

# Styling
style = ttk.Style(screen)
style.theme_use('clam')

# Layout
frame = ttk.Frame(screen, padding="10")
frame.pack(fill='both', expand=True)

# Path selection
path_label = ttk.Label(frame, text="Select Download Path:")
path_label.pack()
select_path_button = ttk.Button(frame, text="Browse", command=select_path)
select_path_button.pack()

# Playlist dropdown
selected_playlist = StringVar()
playlist_dropdown = ttk.OptionMenu(frame, selected_playlist, "Loading playlists...")
playlist_dropdown.pack()

# Fetch playlists and update dropdown
get_user_playlists(access_token)

# Download button
download_button = ttk.Button(frame, text="Download", command=lambda: download_songs(selected_playlist.get()))
download_button.pack()

# Stop Downloading button
stop_button = ttk.Button(frame, text="Stop Downloading", command=stop_downloading)
stop_button.pack()

# Status label
status_label = ttk.Label(frame, text="")
status_label.pack()

# Start GUI
screen.mainloop()
