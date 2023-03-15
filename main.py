import os
import time
import urllib.request
from selenium.webdriver import Chrome, ChromeOptions
from tkinter import *
from tkinter import filedialog
from tkinter import simpledialog
import requests
import shutil
from pytube import YouTube
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from spotipy import *
from spotipy.oauth2 import SpotifyOAuth
import re

load_dotenv(dotenv_path='.env')

# set up Spotify API credentials
# add this line to use the environment variable
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = os.getenv("REDIRECT_URL")
# create an instance of the SpotifyOAuth class
sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope="user-library-read playlist-read-private playlist-read-collaborative",
)

# use the SpotifyOAuth instance to get an access token
token_info = sp_oauth.get_cached_token()
if not token_info:
    auth_url = sp_oauth.get_authorize_url()
    print(f"Please go to this URL and authorize the app: {auth_url}")
    auth_code = input("Enter the authorization code: ")
    token_info = sp_oauth.get_access_token(auth_code)

access_token = token_info["access_token"]

playlists = {}

def get_auth_header(token):
    return {"Authorization": "Bearer " + token}


def get_user_playlists(token):
    headers = get_auth_header(token)
    response = requests.get(
        "https://api.spotify.com/v1/me/playlists", headers=headers)
    response_json = response.json()
    for item in response_json["items"]:
        playlist_label = Label(
            canvas, text=item["name"], font=('Arial', 0), fg='white')
        playlists[item["name"]] = item["id"]


def get_playlist_tracks(token, playlist_id):
    headers = get_auth_header(token)
    response = requests.get(
        f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks", headers=headers)
    response_json = response.json()
    tracks = []
    for item in response_json["items"]:
        track = item["track"]
        track_name = track["name"]
        artist_name = track["artists"][0]["name"]
        tracks.append((track_name, artist_name))
    return tracks


def save_tracks_to_file(tracks, filename):
    with open(filename, "a", encoding="utf-8") as f:  # Use "a" mode to append to the file
        for track in tracks:
            f.write(f"{track[0]},{track[1]}\n")



def select_path():
    global path_label
    # allows user to select the path from explorer
    path = filedialog.askdirectory()
    path_label = Label(canvas, text=path, font=('Arial', 12), fg='black')
    path_label.pack()



def download_songs(selected_playlist):
    global path_label 
    global playlists
    # get user path
    user_path = path_label.cget("text")

    # create new folder for downloaded songs
    download_folder = os.path.join(user_path, selected_playlist.replace(" ", "_"))
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # get playlist ID
    playlist_id = playlists[selected_playlist]

    tracks = get_playlist_tracks(access_token, playlist_id)
    for track in tracks:
        try:
            # search for song on YouTube using urllib and re
            search_query = f"{track[0]} {track[1]}"
            search_query = urllib.parse.quote(search_query)
            html = urllib.request.urlopen(
                f"https://www.youtube.com/results?search_query={search_query}")
            video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())

            # download video from youtube using pytube
            for video_id in video_ids:
                try:
                    video_url = f"https://youtube.com/watch?v={video_id}"
                    video_title = YouTube(video_url).title

                    temp_file = os.path.join(download_folder, "temp.mp4")
                    final_file = os.path.join(
                        download_folder, f"{track[1]} - {track[0]}.mp3")
                    YouTube(video_url).streams.filter(only_audio=True).first().download(
                        output_path=download_folder, filename="temp.mp4")
                    os.rename(temp_file, final_file)

                    print(f"Downloaded {final_file}")
                    break
                except:
                    continue
        except Exception as e:
            error_message = f"Error downloading {track} \n {e}"
            print(error_message)
            error_label = Label(
                canvas, text=error_message, font=('Arial', 12), fg='white', wraplength=800)
            error_label.pack()


def download():
    global playlists
    # get Spotify API access token
    # change this line to use the access token obtained from the OAuth flow
    token = access_token

    # get user playlists
    get_user_playlists(token)

    # let user select playlist to download
    selected_playlist = StringVar()
    selected_playlist.set("Select a playlist")  # default value
    global playlist_dropdown
    playlist_dropdown = OptionMenu(
        canvas, selected_playlist, *playlists.keys())
    playlist_dropdown.pack()
    download_button = Button(canvas, text="Download", font=('Arial', 12), bg='white',
                             fg='black', command=lambda: download_songs(selected_playlist.get()))
    download_button.pack()
        # add a note in the bottom corner
    credit = Label(canvas, text="by: NOKO", font=('Arial', 8), fg='white', background='#4A4A4A')
    credit.place(relx=1, rely=1, anchor='se')





# create the screen and canvas
screen = Tk()
title = screen.title('Spotify Downloader')
canvas = Canvas(screen, width=1400, height=800, background='#4A4A4A')
canvas.pack()

select_path()
download()

# start the GUI event loop
screen.mainloop()