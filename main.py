import optparse, json, subprocess, threading, queue, json
from pathlib import Path
import socket  # Import the entire socket module
from socket import socket as socket_class

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

    def post_with_response(self, command):
        """Send command and wait for response"""
        if not self.connected:
            if not self.connect():
                return "Could not connect to server"
        
        try:
            self.socket.send(command.encode())
            self.socket.settimeout(10.0)
            response = self.socket.recv(1024).decode()
            return response
        except (socket.timeout, TimeoutError):  # Changed from socket.timeout
            return "Timeout waiting for response"
        except Exception as e:
            print(f"Send error: {e}")
            self.connected = False
            return f"Error: {e}"
        
    
    def post_playlist(self, playlist, shuffle):
        """Send command and wait for response"""
        if not self.connected:
            if not self.connect():
                return "Could not connect to server"
        
        try:
            # Convert playlist to JSON string and encode to bytes
            playlist_data = json.dumps(playlist)

            self.socket.send((("shuffle=" if shuffle else "playlist=") + playlist_data).encode())

            self.socket.settimeout(10.0)
            
            # Keep reading until no more data
            response_data = b''
            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:  # Connection closed by server
                        break
                    response_data += chunk
                except (socket.timeout, TimeoutError):
                    # Timeout means no more data coming
                    break
            
            return response_data.decode()
        except (socket.timeout, TimeoutError):
            return "Timeout waiting for response"
        except Exception as e:
            print(f"Send error: {e}")
            self.connected = False
            return f"Error: {e}"

    def shufflePlaylist(self, playlist):
        return self.post_playlist(playlist, True)

    def playPlaylist(self, playlist):
        return self.post_playlist(playlist, False)

    def playSong(self, song):
        return self.post_with_response(f"play {song}")
    
    def queueSong(self, song):
        return self.post_with_response(f"queue {song}")

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
    
    def getQueue(self):
        return list(self.post_with_response("Gimmie da queue"))

    def scrobble(self):
        # Change position in current song
        pass

    def connect(self):
        """Connect to the server and start receiving thread"""
        try:
            self.socket = socket_class(socket.AF_INET, socket.SOCK_STREAM)
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
            except TimeoutError:  # Changed from socket.timeout
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