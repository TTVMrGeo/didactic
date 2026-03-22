import json, re, flet as ft, asyncio, requests
from pathlib import Path
from main import local, settings, settings_dir
from pysubsonic import pySubsonic

pysub = pySubsonic(
    url=settings["server"]["url"],
    username=settings["server"]["user"],
    password=settings["server"]["password"].encode(),
    api="787b3fb9cc71200540ee8a71c92ca1b6".encode(),
    secret="af3f6d01bba4385b253356380db01b1e".encode(),
    lfm_user="kyaiiro",
    lfm_password="ILoveCoco@13".encode()
)

playlist_list = pysub.getPlaylists()["subsonic-response"]["playlists"]["playlist"]

def main(page: ft.Page):
    
    page.title = "Music App"

    profile = settings["active_profile"]
    client = local(settings["profiles"][profile]['ip'], settings["profiles"][profile]['port'])

    def cache_image(song_id):
        if not Path("img_cache/{song_id}.png").is_file():
            response = requests.get(pysub.albumCover(song_id), stream=True)
            # Check if the request was successful
            if response.status_code == 200:
                # Open a local file with the custom name and write the image content
                with open(f"img_cache/{song_id}.png", 'wb') as f:
                    f.write(response.content)
                return f"img_cache/{song_id}.png"
            else:
                print("Failed to download image")
                return "assets/NoCover.jpg"
        else:
            return f"img_cache/{song_id}.png"
    
    # --- Function to fetch song details from Subsonic ---
    def get_song_details(song_id):
        """Fetch song details from Subsonic using pysubsonic"""
        try:
            # Try to get song details using pysubsonic
            # Assuming pysubsonic has a getSong method
            song = pysub.getSong(song_id)
            cover = cache_image(song_id)
            song["cover"] = cover
            return song
        except Exception as e:
            print(f"Error fetching song details: {e}")
    
    # --- Function to update the UI when a song starts ---
    def update_now_playing(song_id):
        """Update the UI with the currently playing song"""
        print(f"Now playing song ID: {song_id}")
        
        # Fetch song details from Subsonic
        song_details = get_song_details(song_id)
        
        # Update the right sidebar
        right_sidebar.content = ft.Container(
            content=ft.Column([
                ft.Image(
                    src=song_details["cover"],
                    width=250,
                    height=250,
                    error_content=ft.Icon(ft.Icons.MUSIC_NOTE, size=50)
                ),
                ft.Text(value=song_details["title"], size=30, weight=ft.FontWeight.BOLD),
                ft.Text(value=song_details["artist"], size=15),
            ]),
            width=250,
            padding=10,
        )
        
        # Update the output text
        output.value = f"Now playing: {song_details.get('title', 'Unknown')}"
        
        # Update the page
        page.update()
    
    # --- Set up callback for when a song starts ---
    def on_song_start(song_info):
        print(f"on_song_start called with: {song_info}")  # Debug print
        song_id = song_info.get('song_id') or song_info.get('id')
        if song_id:
            print(f"Got song_id: {song_id}")  # Debug print
            update_now_playing(song_id)
        else:
            print("No song_id found in message")  # Debug print
    
    # Set the callback on the client
    client.set_callback(on_song_start)
    print("Callback set on client")
    
    # --- Process messages from the server ---
    async def process_messages():
        """Process messages from the server's message queue"""
        while True:
            client.process_messages()
            await asyncio.sleep(0.3)
    
    # Start the message processing task
    page.run_task(process_messages)
    
    # --- Output text ---
    output = ft.Text(value="Welcome to Music App", size=16)

    # --- Login dialog ---
    serverip_field = ft.TextField(label="Server IP", value=settings['server'].get('url', ''))
    username_field = ft.TextField(label="Username", value=settings['server'].get('user', ''))
    password_field = ft.TextField(label="Password", password=True, can_reveal_password=True)
    remember_me = ft.Checkbox(label="Remember me", value=settings['server'].get('remember_me', False))
    login_error = ft.Text(value="", color=ft.Colors.RED)
    
    def do_login(e):
        url = serverip_field.value
        url = "{}{}{}".format(
                "http://" if "http" not in url else "",
                url,
                ":4533" if not re.search(r':\d+', url) else ""
                )
        if not url:
            login_error.value = "No server URL configured in settings.json"
            page.update()
            return

        result = client.server_status(url, username_field.value, password_field.value)
        if result == url:
            url = serverip_field.value
            settings["server"]["url"] = "{}{}{}".format(
                "http://" if "http" not in url else "",
                url,
                ":4533" if not re.search(r':\d+', url) else ""
                )
            settings['server']['user'] = username_field.value
            settings['server']['password'] = password_field.value
            settings['server']['remember_me'] = remember_me.value
            with open(f"{settings_dir}/settings.json", 'w') as f:
                json.dump(settings, f, indent=4)
            output.value = f"Logged in as {username_field.value}"
            page.pop_dialog()
        else:
            login_error.value = result if result else "Login failed"

        page.update()

    def update_settings():
        # Update the new settings
        page.pop_dialog()
        page.update()

    def toggle_theme(e):
        print("Idk bro change the theme ig")

    def do_rewind(e):
        client.rewind()
        pause_btn.selected = False
        page.update()

    def do_skip(e):
        client.skip()
        pause_btn.selected = False
        page.update()

    def open_settings(e):
        page.show_dialog(settings_dialogue)

    def home(e):
        main_content.content = ft.Column(home_page)

    def search(e):
        pass

    def play_song(song, title, artist):
        client.playSong(song)
        # Show temporary loading state while waiting for server response
        right_sidebar.content = ft.Container(
            content=ft.Column([
                ft.Image(src="assets/NoCover.jpg", width=250, height=250),
                ft.Text(value=title, size=30),
                ft.Text(value=artist, size=15),
                ft.ProgressRing(width=20, height=20),
            ]),
            width=250,
            padding=10,
        )
        page.update()

    def play_playlist(playlist):
        client.playPlaylist(playlist)

    def shuffle_playlist(playlist):
        client.shufflePlaylist(playlist)

    def playlists(e):
        playlists_page = ft.Container(
            content=ft.Column(),
            padding=20,
        )
        for playlist in playlist_list:
            button = ft.FilledButton(content=playlist['name'], on_click=lambda e, p=playlist['name']: display_playlist(p))
            playlists_page.content.controls.append(button)

        main_content.content = ft.Column(playlists_page)
        

    def playlist_info(title, info):
        try:
            image = pysub.playlistdetails(title)
        except:
            image = "assets/NoCover.jpg"
        for playlist in playlist_list:
            if playlist['name'] == title:
                songs = pysub.getSongsInPlaylist(playlist['id'])['subsonic-response']['playlist']['entry']

        ids = []
        for song in songs:
            ids.append(song['id'])

        songs_container = ft.Container(
                content=ft.Column()
            )
        
        main_column = ft.Column(
            controls=[
                ft.Row([
                    ft.Image(src=image, width=300, height=300),  # Playlist cover
                    ft.Column([
                        ft.Text(value=title, size=60),
                        ft.Text(value=info, size=15),
                        ft.Row([
                            ft.IconButton(
                            icon=ft.Icons.PLAY_ARROW,
                            icon_size=30,
                            tooltip="Play in order",
                            on_click=lambda e: play_playlist(ids),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.SHUFFLE,
                                icon_size=30,
                                tooltip="Shuffle playlist",
                                on_click=lambda e: shuffle_playlist(ids),
                            ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            spacing=20,
                        ),
                    ]),
                ]),
                ft.Row([], spacing=40),
                songs_container,
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            expand=True
        )
        
        for song in songs:
            button = ft.TextButton(content=song['title'], icon=ft.Icons.PLAY_ARROW, on_click=lambda e, id=song['id'], title=song['title'], artist=song['artist']: play_song(id, title, artist))
            songs_container.content.controls.append(button)
        return main_column

    def display_playlist(name):
        for item in playlist_list:
            if item['name'] == name:
                duration_t = item['duration']
                duration_h = int(duration_t//3600)
                duration_m = int((duration_t-(duration_h*3600))//60)
                duration_s = int((duration_t-(duration_h*3600)-(duration_m*60)))
                duration = f"{"0" if duration_h < 10 else ""}{duration_h}h {"0" if duration_m < 10 else ""}{duration_m}m {"0" if duration_s < 10 else ""}{duration_s}s"
                main_content.content = ft.Column(playlist_info(item['name'], f"Song count: {item['songCount']} | Total Duration: {duration}"))

    # --- Shuffle / Play ---
    input_field = ft.TextField(label="Playlist / Song", expand=True)

    # --- Music controls ---
    pause_btn = ft.IconButton(
        icon=ft.Icons.PAUSE,
        selected_icon=ft.Icons.PLAY_ARROW,
        icon_size=30,
        on_click=lambda e: (
            setattr(pause_btn, 'selected', not pause_btn.selected),
            client.toggle_pause(),
            page.update(),
        ),
    )

    settings_theme = ft.Switch(label="Theme", value=False, on_change=toggle_theme)
    settings_profiles = ft.TextField(label="Profile", value=settings['profiles'][settings['active_profile']].get('ip', ''))

    # -- Popups --
    login_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Login"),
        content=ft.Column(
            controls=[serverip_field, username_field, password_field, remember_me, login_error],
            tight=True,
        ),
        actions=[
            ft.FilledButton(content="Login", on_click=do_login),
        ],
    )
    settings_dialogue = ft.AlertDialog(
        modal=True,
        title=ft.Text("Settings"),
        content=ft.Column(
            controls=[settings_theme, settings_profiles],
            tight=True,
        ),
        actions=[
            ft.FilledButton(content="Cancel", on_click=page.pop_dialog),
            ft.FilledButton(content="Save", on_click=update_settings),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    # -- Pages --
    home_page = [
            output,
            ft.Row(controls=[
                input_field,
            ]),
        ]
    
    # -- Bars
    controls_row = ft.Row(
        controls=[
            ft.IconButton(icon=ft.Icons.SKIP_PREVIOUS, icon_size=30, on_click=do_rewind),
            pause_btn,
            ft.IconButton(icon=ft.Icons.SKIP_NEXT, icon_size=30, on_click=do_skip),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )
    left_sidebar = ft.Container(
        content=ft.Column([
            ft.IconButton(ft.Icons.HOME, on_click=home),
            ft.IconButton(ft.Icons.SEARCH, on_click=search),
            ft.IconButton(ft.Icons.LIBRARY_MUSIC, on_click=playlists),
            ft.IconButton(ft.Icons.QUEUE_MUSIC),
            ft.Container(expand=True),
            ft.IconButton(ft.Icons.SETTINGS, on_click=open_settings),
        ]),
        width=50,
        padding=10,
    )
    right_sidebar = ft.Container(
        content=ft.Column([
            ft.Image(src="assets/NoCover.jpg", width=250, height=250),
            ft.Text(value="Nothing Playing", size=30),
            ft.Text(value="No artist ofc", size=15),
        ]),
        width=250,
        padding=0,
    )

    # --- Page Layout ---
    page.bottom_appbar = ft.BottomAppBar(content=controls_row, height=60, padding=0)
    main_content = ft.Container(
        content=ft.Column(home_page),
        padding=20,
        expand=True,
    )
    page.add(
        ft.Row([left_sidebar, main_content, right_sidebar], expand=True)
    )

    # --- Show login dialog on startup if not remembered ---
    if not settings['server'].get('remember_me', False):
        page.show_dialog(login_dialog)
    else:
        output.value = f"Logged in as {settings['server'].get('user', '')}"
        page.update()


ft.run(main)