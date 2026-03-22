import uuid, requests, hashlib, json, pylast

class pySubsonic():
    def __init__(self, url, username, password, api, secret, lfm_user, lfm_password):
        self.url = url
        self.username = username
        self.password = password.decode()
        self.api = api.decode()
        self.secret = secret.decode()
        self.lfm_user = lfm_user
        self.lfm_password = lfm_password.decode()

    def _gen_salt(self, password):
        salt = uuid.uuid4().hex
        token = hashlib.md5((password + salt).encode()).hexdigest()
        return {"salt": salt, "token": token}

    def getPlaylists(self):
        gen = self._gen_salt(self.password)
        params = {
            'u': self.username,
            't': gen["token"],
            's': gen["salt"],
            'v': '1.16.1',
            'c': "MyApp",
            'f': "json"
        }

        response = requests.get(f"{self.url}/rest/getPlaylists.view", params=params)
        return response.json()
    
    def getSong(self, id):
        gen = self._gen_salt(self.password)
        params = {
            'u': self.username,
            't': gen["token"],
            's': gen["salt"],
            'v': '1.16.1',
            'c': "MyApp",
            'f': "json",
            'id': id
        }

        response = requests.get(f"{self.url}/rest/getSong.view", params=params)
        return response.json()["subsonic-response"]["song"]

    def getSongsInPlaylist(self, playlist):
        gen = self._gen_salt(self.password)
        params = {
            'u': self.username,
            't': gen["token"],
            's': gen["salt"],
            'v': '1.16.1',
            'c': "MyApp",
            'f': "json",
            'id': playlist
        }

        response = requests.get(f"{self.url}/rest/getPlaylist.view", params=params)
        return response.json()
    
    def songdetails(self, artist, title):
        pass_hash = pylast.md5(self.lfm_password)

        network = pylast.LastFMNetwork(
            api_key = self.api,
            api_secret = self.secret,
            username = self.username,
            password_hash = pass_hash
        )

        try:
            network.homepage
            return network.get_album(artist=artist, title=title)
        except pylast.WSError as e:
            print(f"Failed: {e}")
            return False
        
    def playlistCover(self, playlist):
        playlists = self.getPlaylists()["subsonic-response"]["playlists"]["playlist"]
        for item in playlists:
            if item["name"] == playlist:
                art_id = item["coverArt"]
        gen = self._gen_salt(self.password)
        return f"{self.url}/rest/getCoverArt.view?u={self.username}&t={gen["token"]}&s={gen["salt"]}&v=1.16.1&c=myClient&f=json&id={art_id}&size=300"
    
    def albumCover(self, song):
        gen = self._gen_salt(self.password)
        return f"{self.url}/rest/getCoverArt.view?u={self.username}&t={gen["token"]}&s={gen["salt"]}&v=1.16.1&c=myClient&f=json&id={song}&size=300"
        
    # songdetails(artist, title).get_cover_image(size=1)