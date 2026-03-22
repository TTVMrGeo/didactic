import optparse, json, subprocess, threading, queue, json
from pathlib import Path
from socket import socket, AF_INET, SOCK_STREAM

settings_dir = "/home/mrgeo/Documents/Code/Music App/Client"
default_settings = {
    'active_profile': 'pc',
    'profiles': {
        'pc': {
            'ip': '0.0.0.0',
            'port': 6969
        }
    },
    'server': {
        'url': '',
        'user': '',
        'password': ''
    }
}

class local:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.receive_thread = None
        self.running = False
        self.callback = None
        self.message_queue = queue.Queue()

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

    def post(self, command):
        """Send command to server"""
        if not self.connected:
            if not self.connect():
                return "Could not connect to server"
        
        try:
            self.socket.send(command.encode())
            return "Command sent"
        except Exception as e:
            print(f"Send error: {e}")
            self.connected = False
            return f"Error: {e}"

    def post_with_response(self, command):
        """Send command and wait for response"""
        if not self.connected:
            if not self.connect():
                return "Could not connect to server"
        
        try:
            self.socket.send(command.encode())
            self.socket.settimeout(5.0)
            response = self.socket.recv(1024).decode()
            return response
        except socket.timeout:
            return "Timeout waiting for response"
        except Exception as e:
            print(f"Send error: {e}")
            self.connected = False
            return f"Error: {e}"
        
    def getPlaylists(self):
        pass

    def shufflePlaylist(self, playlist):
        return self.post_with_response(f"shuffle {playlist}")

    def playPlaylist(self, playlist):
        return self.post_with_response(f"playlist {playlist}")

    def playSong(self, song):
        return self.post_with_response(f"play {song}")

    def toggle_pause(self):
        return self.post_with_response("toggle_pause")

    def skip(self):
        return self.post_with_response("skip")

    def rewind(self):
        return self.post_with_response("rewind")

    def get_current_song(self):
        """Get current playing song info"""
        response = self.post_with_response("status")
        try:
            return json.loads(response).get('current_song', {})
        except:
            return {}

    def scrobble(self):
        # Change position in current song
        pass

    def connect(self):
        """Connect to the server and start receiving thread"""
        try:
            self.socket = socket(AF_INET, SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receive_thread.start()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def _receive_messages(self):
        """Receive messages from server in background thread"""
        while self.running and self.connected:
            try:
                self.socket.settimeout(1.0)
                data = self.socket.recv(1024)
                if data:
                    message = data.decode().strip()
                    if message.startswith("NOW_PLAYING"):
                        song_info = json.loads(message[12:])
                        self.message_queue.put(song_info)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Receive error: {e}")
                self.connected = False
                break

    def set_callback(self, callback):
        """Set callback for receiving song info updates"""
        self.callback = callback

    def process_messages(self):
        """Process messages in queue (call this from main thread)"""
        while not self.message_queue.empty():
            message = self.message_queue.get_nowait()
            if isinstance(message, dict) and 'song_id' in message:
                if self.callback:
                    self.callback(message)

    def close(self):
        """Close connection"""
        self.running = False
        if self.socket:
            self.socket.close()
        self.connected = False

def get_arguments():
    parser = optparse.OptionParser()

    client = optparse.OptionGroup(parser, "Client Options", "Options for when starting a client")
    client.add_option("-c", "--client", dest="client", help="Connect to a server (ip:port default is 0.0.0.0:6969)")
    client.add_option("--shuffle", dest="shuffle", help=("Shuffle a playlist"))
    client.add_option("--play", dest="play", help=("Play a song or playlist"))

    parser.add_option_group(client)
    (options, arguments) = parser.parse_args()
    if not options.server:
        if not options.client:
            return("Missing args. -c or -s to set the instance as a client or server. Use --help")
        else:
            return options
    else:
        return "Server"
    
def dump_default(dSettings):
    with open(f"{settings_dir}/settings.json", 'w') as json_file:
        json.dump(dSettings, json_file, indent=4)

if Path(settings_dir).is_dir():
    if not Path(f"{settings_dir}/settings.json").is_file():
        dump_default(default_settings)
else:
    subprocess.run(["mkdir", "/home/mrgeo/.config/music"])
    dump_default(default_settings)

with open(f"{settings_dir}/settings.json", 'r') as file:
    settings = json.load(file)