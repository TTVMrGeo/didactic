import flet as ft, requests, re, json
from pathlib import Path
from mpv import MPVPlayer as player

settings_dir = "/home/mrgeo/Documents/Code/New Music App"

class pysub():
    def playlists(): return requests.get("http://localhost:3000/api/playlists").json()
    def song(id): return requests.get(f"http://localhost:3000/api/song/{id}").json()
    def songs(id): return requests.get(f"http://localhost:3000/api/playlist/{id}/songs").json()
    def songCover(song): return requests.get(f"http://localhost:3000/api/playlist/{song}/cover").json()
    def albumCover(album): return requests.get(f"http://localhost:3000/api/album/{album}/cover").json()
    def songDetails(artist, song): return requests.get(f"http://localhost:3000/api/song-details?artist={artist}&title={song}").json()

class local():
    def server_status(self, url, user, password):
        import requests
        params = {
            'u': user,
            'p': password,
            'v': '1.16.1',
            'c': "Music",
            'f': "json"
        }

        try:
            response = requests.get(f"{url}/rest/ping.view", params=params, timeout=5).json()
        except requests.exceptions.ConnectionError:
            return "Could not reach server"
        except requests.exceptions.Timeout:
            return "Connection timed out"
        except Exception as e:
            return f"Error: {e}"

        if response["subsonic-response"]["status"] == "ok":
            return url
        else:
            return "Incorrect username or password" if response["subsonic-response"]["error"]["code"] in (40, 10) else "Login failed"

def main(page: ft.Page): #TODO Remake this whole app and make it async... use pysub api and navidrome rest. Play songs here with mpv
    page.title = "Music App"

    default_settings = {}
    
    # Ensure settings directory exists
    Path(settings_dir).mkdir(parents=True, exist_ok=True)
    settings_file = Path(f"{settings_dir}/settings.json")

    # Create default settings if file doesn't exist
    if not settings_file.is_file():
        with open(settings_file, 'w') as json_file:
            json.dump(default_settings, json_file, indent=4)
    
    # Load settings
    with open(settings_file, 'r') as file:
        settings = json.load(file)

    # Create login dialog fields
    serverip_field = ft.TextField(label="Server IP", value='')
    username_field = ft.TextField(label="Username", value='')
    password_field = ft.TextField(label="Password", password=True, can_reveal_password=True)
    remember_me = ft.Checkbox(label="Remember me", value=False)
    login_error = ft.Text(value="", color=ft.Colors.RED)
    
    # If there's an active profile and it exists, populate the fields
    if 'server' in settings:
        serverip_field.value = settings['server'].get('url', '')
        username_field.value = settings['server'].get('user', '')
        remember_me.value = settings['server'].get('remember_me', False)
    
    def do_login(e):
        url = serverip_field.value
        if url and "http" not in url:
            url = f"http://{url}"
        if url and not re.search(r':\d+', url):
            url = f"{url}:4533"
        
        if not url:
            login_error.value = "Please enter a server URL"
            page.update()
            return
        
        # Test connection
        client = local()
        result = client.server_status(url, username_field.value, password_field.value)
        
        if result == url:
            # Connection successful, save settings
            settings = {
                'theme': 'dark',
                'server': {
                    'url': url,
                    'user': username_field.value,
                    'password': password_field.value,
                    'remember_me': remember_me.value
                }
            }
            
            # Save to file
            with open(settings_file, 'w') as json_file:
                json.dump(settings, json_file, indent=4)
            
            # Close dialog and refresh UI
            page.pop_dialog()
            
            # Reinitialize the app with new settings
            initialize_app(page, settings)
        else:
            login_error.value = result if result else "Login failed"
            page.update()
    
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
    
    # Show login dialog if not remembered
    show_login = True
    
    if settings.get('remember_me', False):
        show_login = False
    
    if show_login:
        page.show_dialog(login_dialog)
    else:
        initialize_app(page, settings)

def initialize_app(page: ft.Page, settings):
    theme = settings.get("theme", "dark")
    page.theme_mode = ft.ThemeMode.DARK if theme == "dark" else ft.ThemeMode.LIGHT

    # Cache directory
    cache_dir = Path("img_cache")
    cache_dir.mkdir(exist_ok=True)

    def cache_image(song_id):
        image_path = cache_dir / f"{song_id}.png"
        if not image_path.is_file():
            try:
                response = requests.get(pysub.albumCover(song_id), stream=True)
                if response.status_code == 200:
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    return str(image_path)
                else:
                    return "assets/NoCover.jpg"
            except:
                return "assets/NoCover.jpg"
        else:
            return str(image_path)
        
    def get_song_details(song_id):
        try:
            song = pysub.song(song_id)
            cover = cache_image(song_id)
            song["cover"] = cover
            return song
        except Exception as e:
            print(f"Error fetching song details: {e}")
            return None
        
    def home(e):
        main_content.content = ft.Column(home_page)
        page.update()

    try:
        playlist_list = pysub.playlists()["subsonic-response"]["playlists"]["playlist"]
    except:
        playlist_list = []
        
    def playlists(e):
        playlists_page = ft.Container(
            content=ft.Column(),
            padding=20,
        )
        for playlist in playlist_list:
            button = ft.FilledButton(
                content=playlist['name'], 
                on_click=lambda e, p=playlist['name']: display_playlist(p)
            )
            playlists_page.content.controls.append(button)
        
        main_content.content = ft.Column([playlists_page])
        page.update()

    def play_playlist(playlist):
        pass

    def shuffle_playlist(playlist):
        pass

    def play_song(song):
        pass

    def queue_song(song):
        pass

    def search(e):
        pass

    def update_settings():
        page.pop_dialog()
        page.update()

    def open_settings(e):
        page.show_dialog(settings_dialogue)

    def toggle_theme(e):
        current_theme = settings["theme"]
        if current_theme == "dark":
            page.theme_mode = ft.ThemeMode.LIGHT
            settings["theme"] = "light"
        else:
            page.theme_mode = ft.ThemeMode.DARK
            settings["theme"] = "dark"
        
        # Save settings
        settings_file = Path(f"{settings_dir}/settings.json")
        with open(settings_file, 'w') as json_file:
            json.dump(settings, json_file, indent=4)

    def playlist_info(title, info):
        try:
            image = pysub.playlistdetails(title)
        except:
            image = "assets/NoCover.jpg"
        
        songs = []
        for playlist in playlist_list:
            if playlist['name'] == title:
                try:
                    songs = pysub.songs(playlist['id'])['subsonic-response']['playlist']['entry']
                except:
                    songs = []
        
        songs_container = ft.Container(content=ft.Column())
        
        main_column = ft.Column(
            controls=[
                ft.Row([
                    ft.Image(src=image, width=300, height=300),
                    ft.Column([
                        ft.Text(value=title, size=60),
                        ft.Text(value=info, size=15),
                        ft.Row([
                            ft.IconButton(
                                icon=ft.Icons.PLAY_ARROW,
                                icon_size=30,
                                tooltip="Play in order",
                                on_click=lambda e: play_playlist([song['id'] for song in songs]),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.SHUFFLE,
                                icon_size=30,
                                tooltip="Shuffle playlist",
                                on_click=lambda e: shuffle_playlist([song['id'] for song in songs]),
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
            item = ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.PLAY_ARROW_OUTLINED,
                        on_click=lambda e, id=song['id']: play_song(id),
                        padding=0.25
                        ),
                    ft.IconButton(
                        icon=ft.Icons.QUEUE,
                        on_click=lambda e, id=song['id']: queue_song(id),
                        padding=0.25
                        ),
                    ft.Text(value=song["title"])
                    ]
            )
            songs_container.content.controls.append(item)
        return main_column
    

    def display_playlist(name):
        for item in playlist_list:
            if item['name'] == name:
                duration_t = item['duration']
                duration_h = int(duration_t//3600)
                duration_m = int((duration_t-(duration_h*3600))//60)
                duration_s = int((duration_t-(duration_h*3600)-(duration_m*60)))
                duration = f"{duration_h:02d}h {duration_m:02d}m {duration_s:02d}s"
                main_content.content = ft.Column([playlist_info(item['name'], f"Song count: {item['songCount']} | Total Duration: {duration}")])
                page.update()

    output = ft.Text(value="Welcome to Music App", size=16)
    input_field = ft.TextField(label="Playlist / Song", expand=True)
    
    settings_theme = ft.Switch(
        label="Theme", 
        value=(settings["theme"] == "light"), 
        on_change=toggle_theme
    )
    settings_dialogue = ft.AlertDialog(
        modal=True,
        title=ft.Text("Settings"),
        content=ft.Column(
            controls=[settings_theme],
            tight=True,
        ),
        actions=[
            ft.FilledButton(content="Cancel", on_click=lambda e: page.pop_dialog()),
            ft.FilledButton(content="Save", on_click=update_settings),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    home_page = [
        output,
        ft.Row(controls=[input_field]),
    ]
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
        content=ft.Column(controls=[
            ft.Image(src="assets/NoCover.jpg", width=250, height=250),
            ft.Text(value="Nothing Playing", size=30),
            ft.Text(value="No artist ofc", size=15),
        ]),
        width=250,
        padding=0,
    )
    main_content = ft.Container(
        content=ft.Column(home_page),
        padding=20,
        expand=True,
    )
        
    page.clean()  # Clear any existing content
    page.add(ft.Row([left_sidebar, main_content, right_sidebar], expand=True))
ft.run(main)