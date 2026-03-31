import json, re, flet as ft, asyncio, requests, subprocess
from socket import socket, AF_INET, SOCK_STREAM
from pathlib import Path
from main import local
from pysubsonic import pySubsonic

def main(page: ft.Page):
    page.title = "Music App"

    settings_dir = "/home/mrgeo/Documents/Code/Music App/Client"
    default_settings = {
        'active_profile': 'default',
        'profiles': {}
    }
    
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
    profile_user = ft.TextField(label="Profile Name", value=settings.get('active_profile', 'default'))
    profile_url = ft.TextField(label="Profile Url", value='')
    profile_port = ft.TextField(label="Profile Port", value='')
    serverip_field = ft.TextField(label="Server IP", value='')
    username_field = ft.TextField(label="Username", value='')
    password_field = ft.TextField(label="Password", password=True, can_reveal_password=True)
    remember_me = ft.Checkbox(label="Remember me", value=False)
    login_error = ft.Text(value="", color=ft.Colors.RED)
    
    # If there's an active profile and it exists, populate the fields
    active_profile = settings.get('active_profile', 'default')
    if active_profile in settings.get('profiles', {}):
        profile = settings['profiles'][active_profile]
        profile_user.value = active_profile
        profile_url.value = profile.get('ip', '')
        profile_port.value = str(profile.get('port', ''))
        if 'server' in profile:
            serverip_field.value = profile['server'].get('url', '')
            username_field.value = profile['server'].get('user', '')
            remember_me.value = profile['server'].get('remember_me', False)
    
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
        
        profile_name = profile_user.value
        if not profile_name:
            login_error.value = "Please enter a profile name"
            page.update()
            return
        
        # Test connection
        client = local(profile_url.value, profile_port.value)
        result = client.server_status(url, username_field.value, password_field.value)
        
        if result == url:
            # Connection successful, save settings
            deprofile = {
                'ip': profile_url.value,
                'port': int(profile_port.value) if profile_port.value else 4533,
                'theme': 'dark',
                'server': {
                    'url': url,
                    'user': username_field.value,
                    'password': password_field.value,
                    'remember_me': remember_me.value
                }
            }
            
            # Update settings
            if 'profiles' not in settings:
                settings['profiles'] = {}
            
            settings['profiles'][profile_name] = deprofile
            settings['active_profile'] = profile_name
            
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
            controls=[profile_user, ft.Row(controls=[profile_url, profile_port]), 
                     serverip_field, username_field, password_field, remember_me, login_error],
            tight=True,
        ),
        actions=[
            ft.FilledButton(content="Login", on_click=do_login),
        ],
    )
    
    # Show login dialog if not remembered
    active_profile = settings.get('active_profile', 'default')
    show_login = True
    
    if active_profile in settings.get('profiles', {}):
        if settings['profiles'][active_profile].get('server', {}).get('remember_me', False):
            show_login = False
    
    if show_login:
        page.show_dialog(login_dialog)
    else:
        initialize_app(page, settings)

def initialize_app(page: ft.Page, settings):
    """Initialize the main application after successful login"""
    
    settings_dir = "/home/mrgeo/Documents/Code/Music App/Client"
    
    # Apply theme
    active_profile = settings['active_profile']
    theme = settings["profiles"][active_profile].get("theme", "dark")
    page.theme_mode = ft.ThemeMode.DARK if theme == "dark" else ft.ThemeMode.LIGHT
    
    # Initialize client
    client = local(
        settings["profiles"][active_profile]['ip'], 
        settings["profiles"][active_profile]['port']
    )
    
    # Initialize pySubsonic
    server_settings = settings["profiles"][active_profile]['server']
    pysub = pySubsonic(
        url=server_settings["url"],
        username=server_settings["user"],
        password=server_settings["password"].encode(),
        api="787b3fb9cc71200540ee8a71c92ca1b6".encode(),
        secret="af3f6d01bba4385b253356380db01b1e".encode(),
        lfm_user="kyaiiro",
        lfm_password="ILoveCoco@13".encode()
    )
    
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
            song = pysub.getSong(song_id)
            cover = cache_image(song_id)
            song["cover"] = cover
            return song
        except Exception as e:
            print(f"Error fetching song details: {e}")
            return None
    
    def update_now_playing(song_id):
        print(f"Now playing song ID: {song_id}")
        song_details = get_song_details(song_id)
        
        if song_details:
            right_sidebar.content = ft.Container(
                content=ft.Column([
                    ft.Image(
                        src=song_details["cover"],
                        width=250,
                        height=250,
                        error_content=ft.Icon(ft.Icons.MUSIC_NOTE, size=50)
                    ),
                    ft.Text(value=song_details.get("title", "Unknown"), size=30, weight=ft.FontWeight.BOLD),
                    ft.Text(value=song_details.get("artist", "Unknown"), size=15),
                ]),
                width=250,
                padding=10,
            )
            output.value = f"Now playing: {song_details.get('title', 'Unknown')}"
            page.update()
    
    try:
        playlist_list = pysub.getPlaylists()["subsonic-response"]["playlists"]["playlist"]
    except:
        playlist_list = []
    
    def on_song_start(song_info):
        print(song_info)
        song_id = song_info.get('song_id') or song_info.get('id')
        if song_id:
            update_now_playing(song_id)
    
    client.set_callback(on_song_start)
    
    async def process_messages():
        while True:
            client.process_messages()
            await asyncio.sleep(0.3)
    
    page.run_task(process_messages)
    
    # UI Components
    output = ft.Text(value="Welcome to Music App", size=16)
    
    def update_settings():
        page.close_dialog()
        page.update()
    
    def toggle_theme(e):
        pro = settings['active_profile']
        current_theme = settings["profiles"][pro]["theme"]
        if current_theme == "dark":
            page.theme_mode = ft.ThemeMode.LIGHT
            settings["profiles"][pro]["theme"] = "light"
        else:
            page.theme_mode = ft.ThemeMode.DARK
            settings["profiles"][pro]["theme"] = "dark"
        
        # Save settings
        settings_file = Path(f"{settings_dir}/settings.json")
        with open(settings_file, 'w') as json_file:
            json.dump(settings, json_file, indent=4)
    
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
        page.update()
    
    def search(e):
        pass
    
    def play_song(song):
        client.playSong(song)

    def queue_song(song):
        client.queueSong(song)
    
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
            button = ft.FilledButton(
                content=playlist['name'], 
                on_click=lambda e, p=playlist['name']: display_playlist(p)
            )
            playlists_page.content.controls.append(button)
        
        main_content.content = ft.Column([playlists_page])
        page.update()
    
    def playlist_info(title, info):
        try:
            image = pysub.playlistdetails(title)
        except:
            image = "assets/NoCover.jpg"
        
        songs = []
        for playlist in playlist_list:
            if playlist['name'] == title:
                try:
                    songs = pysub.getSongsInPlaylist(playlist['id'])['subsonic-response']['playlist']['entry']
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
    
    input_field = ft.TextField(label="Playlist / Song", expand=True)
    
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
    
    settings_theme = ft.Switch(
        label="Theme", 
        value=(settings["profiles"][active_profile]["theme"] == "light"), 
        on_change=toggle_theme
    )
    settings_profiles = ft.TextField(
        label="Profile", 
        value=settings['profiles'][active_profile].get('ip', '')
    )
    
    settings_dialogue = ft.AlertDialog(
        modal=True,
        title=ft.Text("Settings"),
        content=ft.Column(
            controls=[settings_theme, settings_profiles],
            tight=True,
        ),
        actions=[
            ft.FilledButton(content="Cancel", on_click=lambda e: page.close_dialog()),
            ft.FilledButton(content="Save", on_click=update_settings),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )
    
    home_page = [
        output,
        ft.Row(controls=[input_field]),
    ]
    
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
    
    page.bottom_appbar = ft.BottomAppBar(content=controls_row, height=60, padding=0)
    main_content = ft.Container(
        content=ft.Column(home_page),
        padding=20,
        expand=True,
    )
    
    page.clean()  # Clear any existing content
    page.add(ft.Row([left_sidebar, main_content, right_sidebar], expand=True))
    
    # Check server connection status
    status = client.post_with_response("Connected To Server")
    print("-"*20, status)
    if status and status != "Connected, nothing playing" and status != "":
        update_now_playing(status)

ft.run(main)