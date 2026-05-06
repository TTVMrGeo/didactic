import requests, tempfile, os, asyncio, json, logging, mpv, random
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
        self._loop = asyncio.get_event_loop()  # Store the event loop
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
                print("-"*40)
                
                # Update flags directly (they're thread-safe for simple booleans)
                self.is_playing = False
                self.is_loaded = False
                self.current_file = None
                
                # Schedule a notification to the asyncio loop if needed
                if self._loop and not self._loop.is_closed():
                    asyncio.run_coroutine_threadsafe(
                        self._notify_playback_ended(),
                        self._loop
                    )
            
            @self.player.event_callback('file-loaded')
            def file_loaded_callback(event):
                logger.debug("File loaded successfully")
                self.is_loaded = True
                
                # Schedule a notification to the asyncio loop if needed
                if self._loop and not self._loop.is_closed():
                    asyncio.run_coroutine_threadsafe(
                        self._notify_file_loaded(),
                        self._loop
                    )
                
            logger.info("MPV player initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MPV: {e}")
            raise
    
    async def _notify_playback_ended(self):
        """Notify that playback ended (can be overridden or used for callbacks)"""
        # This runs in the asyncio event loop
        logger.debug("Playback ended notification sent to event loop")
    
    async def _notify_file_loaded(self):
        """Notify that file loaded (can be overridden or used for callbacks)"""
        logger.debug("File loaded notification sent to event loop")
    
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
            
            # Reset flags
            self.is_loaded = False
            self.is_playing = False
            
            # Load new file
            await asyncio.to_thread(self.player.command, 'loadfile', filename)
            self.current_file = filename
            
            # Wait for file to load with timeout
            timeout = 10
            start_time = asyncio.get_event_loop().time()
            while not self.is_loaded and (asyncio.get_event_loop().time() - start_time) < timeout:
                await asyncio.sleep(0.1)
            
            if not self.is_loaded:
                logger.warning(f"File loading timed out after {timeout} seconds")
                return False
            
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
            self.is_paused = False
            logger.debug("Playback started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to play: {e}")
            return False
    
    async def toggle_pause(self):
        """Toggle pause state"""
        try:
            await self.ensure_player()
            
            if self.is_loaded:
                await asyncio.to_thread(self.player.command, 'cycle', 'pause')
                return True
            elif self.current_file:
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
            self.is_loaded = False
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
                
                try:
                    duration = await asyncio.to_thread(self.player.command, 'get', 'duration')
                    if duration and duration != 'null':
                        status['duration'] = float(duration)
                    else:
                        status['duration'] = 0.0
                except:
                    status['duration'] = 0.0
                
                try:
                    paused = await asyncio.to_thread(self.player.command, 'get', 'pause')
                    status['paused'] = paused == 'yes'
                except:
                    status['paused'] = not self.is_playing
            
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
            await asyncio.sleep(0.5)
    
    def cleanup(self):
        """Clean up MPV resources"""
        try:
            if self.player:
                logger.debug("Terminating MPV player")
                self.player.terminate()
                self.player = None
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
