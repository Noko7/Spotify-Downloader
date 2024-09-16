import os
import urllib.parse
import requests
import re
import string
from yt_dlp import YoutubeDL
from tkinter import Tk, ttk, filedialog, StringVar, messagebox
from dotenv import load_dotenv
from spotipy import SpotifyOAuth
from spotipy.oauth2 import SpotifyOauthError
import threading

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

# Sanitize filename to remove invalid characters for file saving
def sanitize_filename(filename):
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    return ''.join(c for c in filename if c in valid_chars)

# Global variable to control the downloading process
is_downloading = True

# Function to stop the download process
def stop_downloading():
    global is_downloading
    is_downloading = False
    status_label.config(text="Downloading stopped.")

# Fetch tracks from the selected playlist
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

# Download songs by searching YouTube and using yt-dlp
def download_songs(selected_playlist):
    global is_downloading
    is_downloading = True
    status_label.config(text="Downloading...")

    user_path = path_label.cget("text")
    
    # Error handling for invalid download path
    if user_path == "Select Download Path:":
        messagebox.showerror("Error", "Please select a valid download path.")
        return

    download_folder = os.path.join(user_path, sanitize_filename(selected_playlist).replace(" ", "_"))
    
    # Error handling for directory creation
    try:
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
    except OSError as e:
        messagebox.showerror("Error", f"Failed to create download directory: {e}")
        return

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
                    video_url = f"https://www.youtube.com/watch?v={video_id}"

                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': os.path.join(download_folder, f'{sanitized_track_name}.%(ext)s'),
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        'noplaylist': True
                    }

                    with YoutubeDL(ydl_opts) as ydl:
                        ydl.download([video_url])
                        print(f"Downloaded successfully: {final_file}")
                        break
                except Exception as e:
                    print(f"Error downloading video: {e}")
                    continue
        except Exception as e:
            print(f"Error processing track {track}: {e}")

    status_label.config(text="Download completed.")


def start_download():
    threading.Thread(target=lambda: download_songs(selected_playlist.get()), daemon=True).start()


def select_path():
    global path_label
    path = filedialog.askdirectory()
    if path:
        path_label.config(text=path)


screen = Tk()
screen.title('Spotify Downloader')
screen.geometry("600x400")


style = ttk.Style(screen)
style.theme_use('clam')


frame = ttk.Frame(screen, padding="20")
frame.pack(fill='both', expand=True)


path_label = ttk.Label(frame, text="Select Download Path:")
path_label.pack(pady=10)
select_path_button = ttk.Button(frame, text="Browse", command=select_path)
select_path_button.pack(pady=10)


selected_playlist = StringVar()
playlist_dropdown = ttk.OptionMenu(frame, selected_playlist, "Loading playlists...")
playlist_dropdown.pack(pady=10)


get_user_playlists(access_token)


download_button = ttk.Button(frame, text="Download", command=start_download)
download_button.pack(pady=10)


stop_button = ttk.Button(frame, text="Stop Downloading", command=stop_downloading)
stop_button.pack(pady=10)


status_label = ttk.Label(frame, text="")
status_label.pack(pady=10)

# Start GUI
screen.mainloop()
