#!/usr/bin/python
import optparse, uuid, hashlib, requests, tempfile, os, asyncio, json, logging, mpv, random
from asyncio import StreamReader, StreamWriter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MPVPlayer:
    def __init__(self):
        """Initialize MPV player"""
        self.player = None
        self.current_file = None
        self.is_playing = False
        self.is_loaded = False
        self.playback_task = None
        self._init_player()
        
    def _init_player(self):
        """Initialize MPV with proper settings"""
        try:
            self.player = mpv.MPV(
                input_default_bindings=True,
                input_vo_keyboard=True,
                osc=True,
                keep_open='always',  # Keep player open
                cache=True,
                cache_secs=5,
                volume=50,
                really_quiet=True,
                audio_device='auto',
                audio_exclusive=False,
                vo='null',  # No video output for audio-only
                idle=True,  # Start in idle mode
                ytdl=False
            )
            
            # Set up event handlers
            @self.player.property_observer('pause')
            def pause_observer(name, value):
                if value is not None:
                    self.is_playing = not value
                    logger.debug(f"Playback state: {'playing' if self.is_playing else 'paused'}")
            
            @self.player.event_callback('end-file')
            def end_file_callback(event):
                # Fixed: Access event properties correctly
                reason = event.reason if hasattr(event, 'reason') else 0
                logger.debug(f"Playback ended, reason: {reason}")
                self.is_playing = False
                self.is_loaded = False
                
            @self.player.event_callback('file-loaded')
            def file_loaded_callback(event):
                logger.debug("File loaded successfully")
                self.is_loaded = True
                
            logger.info("MPV player initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MPV: {e}")
            raise
    
    async def ensure_player(self):
        """Ensure player is initialized"""
        if self.player is None:
            await asyncio.to_thread(self._init_player)
    
    async def load(self, filename):
        """Load a file into MPV"""
        try:
            await self.ensure_player()
            
            if not os.path.exists(filename):
                logger.error(f"File not found: {filename}")
                return False
                
            logger.info(f"Loading file: {filename}")
            
            # Stop current playback first
            await self.stop()
            
            # Load new file
            await asyncio.to_thread(self.player.command, 'loadfile', filename)
            self.current_file = filename
            
            # Wait for file to load
            await asyncio.sleep(0.5)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load file: {e}")
            return False
    
    async def play(self):
        """Start/resume playback"""
        try:
            await self.ensure_player()
            
            if not self.is_loaded and self.current_file:
                # Reload file if needed
                await self.load(self.current_file)
                
            await asyncio.to_thread(self.player.command, 'set', 'pause', 'no')
            self.is_playing = True
            logger.debug("Playback started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to play: {e}")
            return False
    
    async def pause(self):
        """Pause playback"""
        try:
            await self.ensure_player()
            await asyncio.to_thread(self.player.command, 'set', 'pause', 'yes')
            self.is_playing = False
            logger.debug("Playback paused")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause: {e}")
            return False
    
    async def toggle_pause(self):
        """Toggle pause state - fixed to not skip songs"""
        try:
            await self.ensure_player()
            
            # Only toggle if we have a loaded file
            if self.is_loaded:
                await asyncio.to_thread(self.player.command, 'cycle', 'pause')
                return True
            elif self.current_file:
                # If no file is loaded but we have a current file, start playback
                await self.play()
                return True
            else:
                logger.debug("Cannot toggle pause: no file loaded")
                return False
            
        except Exception as e:
            logger.error(f"Toggle pause error: {e}")
            return False
    
    async def stop(self):
        """Stop playback"""
        try:
            await self.ensure_player()
            await asyncio.to_thread(self.player.command, 'stop')
            self.is_playing = False
            logger.debug("Playback stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop: {e}")
            return False
    
    async def set_volume(self, volume):
        """Set volume (0-100)"""
        try:
            await self.ensure_player()
            volume = max(0, min(100, volume))
            await asyncio.to_thread(self.player.command, 'set', 'volume', str(volume))
            logger.debug(f"Volume set to {volume}")
            return volume
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return 50
    
    async def get_status(self):
        """Get current playback status"""
        try:
            await self.ensure_player()
            
            # Get properties with error handling
            status = {
                'playing': self.is_playing,
                'loaded': self.is_loaded,
                'file': os.path.basename(self.current_file) if self.current_file else None
            }
            
            # Try to get position if file is loaded
            if self.is_loaded:
                try:
                    position = await asyncio.to_thread(self.player.command, 'get', 'time-pos')
                    if position and position != 'null':
                        status['position'] = float(position)
                    else:
                        status['position'] = 0.0
                except:
                    status['position'] = 0.0
                
                # Try to get duration
                try:
                    duration = await asyncio.to_thread(self.player.command, 'get', 'duration')
                    if duration and duration != 'null':
                        status['duration'] = float(duration)
                    else:
                        status['duration'] = 0.0
                except:
                    status['duration'] = 0.0
                
                # Try to get pause state
                try:
                    paused = await asyncio.to_thread(self.player.command, 'get', 'pause')
                    status['paused'] = paused == 'yes'
                except:
                    status['paused'] = not self.is_playing
            
            # Get volume
            try:
                volume = await asyncio.to_thread(self.player.command, 'get', 'volume')
                status['volume'] = int(volume) if volume else 50
            except:
                status['volume'] = 50
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {'error': str(e), 'playing': False, 'loaded': False}
    
    async def seek(self, seconds):
        """Seek to position in seconds"""
        try:
            await self.ensure_player()
            if self.is_loaded:
                await asyncio.to_thread(self.player.command, 'seek', str(seconds), 'absolute')
                logger.debug(f"Seeked to {seconds}s")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to seek: {e}")
            return False
    
    async def wait_for_playback(self):
        """Wait for playback to complete"""
        while self.is_playing and self.is_loaded:
            await asyncio.sleep(1)
    
    def cleanup(self):
        """Clean up MPV resources"""
        try:
            if self.player:
                logger.debug("Terminating MPV player")
                self.player.terminate()
                self.player = None
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

class AsyncLocalServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.subsonic_password = "ILoveCoco@13"
        self.subsonic_username = "MrGeo"
        self.subsonic_url = "http://10.0.0.104:4533"
        
        # MPV Player
        self.player = MPVPlayer()
        
        # Server attributes
        self.server = None
        self.active_tasks = set()
        self.shutdown_flag = False
        
        # Queue management
        self.song_queue = []
        self.currently_playing = None
        self.current_index = 0
        self.queue_task = None
        self.queue_lock = asyncio.Lock()
        self.skip_current = False
        self.rewound = False

        # Handle clients
        self.clients = {}

    async def start(self):
        """Start the async server"""
        try:
            self.server = await asyncio.start_server(
                self.handle_client,
                self.host,
                self.port,
                backlog=128
            )
            
            addr = self.server.sockets[0].getsockname()
            logger.info(f"[SERVER] Listening on {addr[0]}:{addr[1]}")
            
            # Start queue processor
            self.queue_task = asyncio.create_task(self.process_queue())
            
            async with self.server:
                await self.server.serve_forever()
                
        except asyncio.CancelledError:
            logger.info("[SERVER] Server cancelled")
        except Exception as e:
            logger.error(f"[SERVER] Error: {e}")
        finally:
            await self.cleanup()

    async def process_queue(self):
        """Process the queue sequentially"""
        while not self.shutdown_flag:
            try:
                # Check if we need to play a song
                async with self.queue_lock:
                    if self.song_queue and not self.currently_playing:
                        if self.rewound:
                            self.current_index -= 1
                        else:
                            self.current_index += 1

                        next_song = self.song_queue[self.current_index]
                        self.rewound = False
                        self.currently_playing = next_song
                        should_play = True
                    else:
                        should_play = False
                
                # Play the song WITHOUT holding the lock
                if should_play:
                    logger.info(f"Processing next song in queue: {next_song}")
                    
                    # Play the song
                    await self._play_song(next_song)
                    
                    # Wait for playback to complete
                    self._current_playback_task = asyncio.current_task()
                    try:
                        while self.currently_playing and not self.skip_current:
                            if not self.player.is_playing and not self.player.is_loaded:
                                break
                            await asyncio.sleep(0.5)
                    finally:
                        self._current_playback_task = None
                        self.skip_current = False
                    
                    # Clear currently_playing WITHOUT lock
                    self.currently_playing = None
                        
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                        
            except Exception as e:
                logger.error(f"Queue processor error: {e}")
                await asyncio.sleep(1)
                
    # In server.py, add this method to broadcast just the song ID
    async def broadcast_now_playing(self, song_id):
        """Send NOW_PLAYING message with just the song ID to all connected clients"""
        message = f"NOW_PLAYING:{json.dumps({'song_id': song_id})}"
        logger.info(f"[SERVER] Broadcasting: {message}")
        
        # Send to all connected clients
        disconnected = []
        for task, writer in list(self.clients.items()):
            try:
                writer.write(message.encode())
                await writer.drain()
                logger.info(f"[SERVER] Sent to client: {task}")
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(task)
        
        # Clean up disconnected clients
        for task in disconnected:
            self.clients.pop(task, None)
            self.active_tasks.discard(task)

    async def _play_song(self, song_id):
        """Internal method to play a single song"""
        try:
            # Stop current playback if any
            await self.player.stop()
            
            # Stream and play the song
            success = await self.stream_and_play(song_id)

            #FIXME sometimes the now playing doesn't update.
            #TODO Maybe make the client request the currently playing song and current queue every 5 sec and compare it with what's currently being displayed

            if success:
                await self.broadcast_now_playing(song_id)
            
            return success
        except Exception as e:
            logger.error(f"Error playing song {song_id}: {e}")
            return False

    async def get_song_details(self, song_id):
        """Get song details from Subsonic"""
        try:
            gen = await self._gen_salt(self.subsonic_password)
            
            params = {
                'u': self.subsonic_username,
                't': gen["token"],
                's': gen["salt"],
                'c': 'MyApp',
                'v': '1.16.1',
                'f': 'json',
                'id': song_id
            }
            
            url = f"{self.subsonic_url}/rest/getSong.view"
            response = await asyncio.to_thread(requests.get, url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                song = data.get('subsonic-response', {}).get('song', {})
                return {
                    'song_id': song_id,
                    'title': song.get('title', 'Unknown'),
                    'artist': song.get('artist', 'Unknown'),
                    'album': song.get('album', 'Unknown'),
                    'cover_art': f"{self.subsonic_url}/rest/getCoverArt.view?id={song.get('coverArt')}" if song.get('coverArt') else 'assets/NoCover.jpg',
                    'duration': song.get('duration', 0)
                }
        except Exception as e:
            logger.error(f"Error getting song details: {e}")
        
        return {
            'song_id': song_id,
            'title': 'Unknown',
            'artist': 'Unknown',
            'album': 'Unknown',
            'cover_art': 'assets/NoCover.jpg',
            'duration': 0
        }

    async def handle_client(self, reader: StreamReader, writer: StreamWriter):
        """Handle client connection asynchronously"""
        addr = writer.get_extra_info('peername')
        logger.info(f"[SERVER] Client connected from {addr}")
        
        task = asyncio.create_task(self._handle_client_connection(reader, writer, addr))
        
        # Store the writer with the task
        task.writer = writer
        self.active_tasks.add(task)
        self.clients[task] = writer  # Store for broadcasting
        
        task.add_done_callback(lambda t: self.active_tasks.discard(t))
        task.add_done_callback(lambda t: self.clients.pop(t, None))
        
        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"[SERVER] Client task cancelled for {addr}")
        finally:
            logger.info(f"[SERVER] Client disconnected from {addr}")
    
    async def _handle_client_connection(self, reader: StreamReader, writer: StreamWriter, addr):
        """Internal method to handle client connection"""
        try:
            while not self.shutdown_flag:
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=60.0)
                    
                    if not data:
                        break
                    
                    message = data.decode().strip()
                    logger.info(f"[SERVER] Received from {addr}: {message}")
                    
                    response = await self.process_command(message)
                    
                    writer.write(response.encode())
                    await writer.drain()
                    
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    try:
                        writer.write(b"PING")
                        await writer.drain()
                    except:
                        break
                    continue
                except ConnectionResetError:
                    logger.info(f"[SERVER] Connection reset by {addr}")
                    break
                except Exception as e:
                    logger.error(f"[SERVER] Error handling client {addr}: {e}")
                    break
                    
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def process_command(self, command: str) -> str:
        """Process incoming commands asynchronously"""
        command = command.strip()
        
        if command.startswith("shuffle "):
            playlist = command[8:]
            playlist = playlist.replace("'", "").replace("[", "").replace("]", "").replace(",", "").split(" ")
            return await self.shuffle(playlist)

        elif command.startswith("playlist "):
            playlist = command[9:]
            playlist = playlist.replace("'", "").replace("[", "").replace("]", "").replace(",", "").split(" ")
            return await self.queue(playlist)
            
        elif command.startswith("play "):
            item = command[5:]
            return await self.play([item])
            
        elif command == "skip":
            return await self.skip()
            
        elif command == "rewind":
            return await self.rewind()
            
        elif command == "toggle_pause":
            return await self.toggle_pause()
            
        elif command.startswith("volume "):
            try:
                volume = int(command[7:])
                return await self.set_volume(volume)
            except:
                return "Invalid volume value"
            
        elif command == "status":
            return await self.get_status()
            
        elif command == "queue":
            return await self.show_queue()
            
        elif command == "clear_queue":
            return await self.clear_queue()
            
        else:
            return f"{command} Unknown command"

    async def shuffle(self, playlist):
        shuffled = playlist.copy()
        random.shuffle(shuffled)
        return await self.queue(shuffled)

    async def queue(self, recieved_item):
        """Add songs to queue"""
        if len(recieved_item) > 1:
            await self.player.stop()
            await self.clear_queue()
            async with self.queue_lock:
                added_count = 0
                for item in recieved_item:
                    self.song_queue.append(item)
                    added_count += 1
            return f"Added {added_count} songs to queue. Queue size: {len(self.song_queue)}"
        else:
            async with self.queue_lock:
                self.song_queue.insert(self.current_index + 1, recieved_item[0])
            return "Added song to queue"
    
    async def play(self, item):
        """Handle play command - adds to queue or plays immediately"""
        if self.currently_playing or self.song_queue:
            return await self.queue(item)
        else:
            # Nothing playing, play immediately
            self.currently_playing = item
            asyncio.create_task(self._play_song(item))
            return f"Playing: {item}"

    async def show_queue(self):
        """Show current queue"""
        async with self.queue_lock:
            if not self.song_queue:
                return "Queue is empty"
            
            queue_list = list(self.song_queue)
            return queue_list
    
    async def clear_queue(self):
        """Clear the queue"""
        async with self.queue_lock:
            cleared_count = len(self.song_queue)
            self.song_queue.clear()
        return f"Cleared {cleared_count} songs from queue"
    
    async def skip(self):
        """Skip current track"""
        self.currently_playing = None
        await self.player.stop()
        return "Skipped current track"

    async def rewind(self):
        """Rewind current track - goes to previous song if within first 10 seconds"""
        try:
            status = await self.player.get_status()
            current_pos = status.get('position', 0)
            
            # If within first 10 seconds, go to previous song
            if current_pos <= 10:
                # Stop the current playback
                await self.player.stop()
                
                # Wait a moment for the stop to complete
                await asyncio.sleep(0.1)

                self.rewound = True
                
                # Clear currently_playing to allow queue processor to pick up the previous song
                async with self.queue_lock:
                    self.currently_playing = None

                return "Rewound to previous song"
            else:
                # Otherwise, rewind within current song
                new_pos = max(0, current_pos - 10)
                await self.player.seek(new_pos)
                return f"Rewound to {new_pos:.1f} seconds"
                
        except Exception as e:
            logger.error(f"Rewind error: {e}", exc_info=True)
            return f"Rewind error: {e}"
    
    async def set_volume(self, volume):
        """Set volume"""
        new_volume = await self.player.set_volume(volume)
        return f"Volume set to {new_volume}%"

    async def get_status(self):
        """Get current playback status"""
        status = await self.player.get_status()
        
        # Add queue information to status
        async with self.queue_lock:
            status['queue_size'] = len(self.song_queue)
            status['currently_playing'] = self.currently_playing
        
        return json.dumps(status, indent=2)

    async def toggle_pause(self):
        """Toggle pause state - fixed to not skip songs"""
        try:
            success = await self.player.toggle_pause()
            if success:
                status = await self.player.get_status()
                # Check if we have a file loaded before checking paused state
                if status.get('loaded', False):
                    if status.get('paused', False):
                        return "Playback paused"
                    else:
                        return "Playback resumed"
                else:
                    # This happens when we just started playing a new song
                    return "Playback started"
            else:
                return "No song loaded to pause/resume"
        except Exception as e:
            logger.error(f"Toggle pause error: {e}")
            return f"Error: {str(e)}"
    
    async def _gen_salt(self, password):
        """Generate salt and token for Subsonic authentication"""
        salt = uuid.uuid4().hex
        token = hashlib.md5((password + salt).encode()).hexdigest()
        return {"salt": salt, "token": token}

    async def stream_and_play(self, song_id):
        """Stream audio from Subsonic and play it"""
        gen = await self._gen_salt(self.subsonic_password)

        params = {
            'u': self.subsonic_username,
            't': gen["token"],
            's': gen["salt"],
            'c': 'MyApp',
            'v': '1.16.1',
            'f': 'json',
            'id': song_id
        }

        url = f"{self.subsonic_url}/rest/stream.view"
        
        try:
            response = await asyncio.to_thread(
                requests.get, url, params=params, stream=True
            )
            
            if response.status_code == 200:
                # Create temp file
                temp_file = await asyncio.to_thread(
                    tempfile.NamedTemporaryFile, mode='wb', suffix='.mp3', delete=False
                )
                temp_filename = temp_file.name
                
                try:
                    # Download file
                    chunk_size = 1024 * 100
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            await asyncio.to_thread(temp_file.write, chunk)
                            await asyncio.to_thread(temp_file.flush)
                    
                    logger.info(f"Download finished: {temp_filename}")
                    
                    # Load and play with MPV
                    success = await self.player.load(temp_filename)
                    if success:
                        await self.player.play()
                        return True
                    else:
                        logger.error("Failed to load file into MPV")
                        return False
                    
                finally:
                    # Clean up temp file after playback
                    if os.path.exists(temp_filename):
                        await asyncio.to_thread(os.remove, temp_filename)
                        logger.info(f"Cleaned up: {temp_filename}")
                        
            else:
                logger.error(f"Error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            return False
    
    async def cleanup(self):
        """Clean up server resources"""
        logger.info("[SERVER] Cleaning up...")
        
        # Stop queue processor
        self.shutdown_flag = True
        if self.queue_task:
            self.queue_task.cancel()
            try:
                await self.queue_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all client tasks
        for task in self.active_tasks:
            if not task.done():
                task.cancel()
        
        if self.active_tasks:
            await asyncio.wait(self.active_tasks, timeout=5.0)
        
        # Clean up MPV player
        await asyncio.to_thread(self.player.cleanup)
        
        logger.info("[SERVER] Cleanup complete")

def get_arguments():
    """Parse command line arguments"""
    parser = optparse.OptionParser()
    
    server = optparse.OptionGroup(parser, "Server Options", "Options for when starting a server")
    server.add_option("-i", "--ip", dest="ip", help="Server IP")
    server.add_option("-p", "--port", dest="port", help="Server Port")
    
    parser.add_option_group(server)
    (options, arguments) = parser.parse_args()
    
    if not options.ip or not options.port:
        return "Missing IP or Port (--ip and --port) use --help"
    else:
        return options

async def main():
    """Main entry point"""
    options = get_arguments()
    if isinstance(options, str):
        print(options)
        return
    
    server = AsyncLocalServer(options.ip, int(options.port))
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Keyboard interrupt received")
        await server.cleanup()
    except Exception as e:
        logger.error(f"Server error: {e}")
        await server.cleanup()

if __name__ == "__main__":
    asyncio.run(main())