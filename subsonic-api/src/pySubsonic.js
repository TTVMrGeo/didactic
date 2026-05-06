const axios = require('axios');
const crypto = require('crypto');
const { v4: uuidv4 } = require('uuid');
const LastFm = require('lastfm');

class PySubsonic {
  constructor({ url, username, password, api, secret, lfmUser, lfmPassword }) {
    this.url = url;
    this.username = username;
    this.password = password;
    this.api = api;
    this.secret = secret;
    this.lfmUser = lfmUser;
    this.lfmPassword = lfmPassword;
  }

  // --- Private Helpers ---

  _genSalt() {
    const salt = uuidv4().replace(/-/g, '');
    const token = crypto
      .createHash('md5')
      .update(this.password + salt)
      .digest('hex');
    return { salt, token };
  }

  _baseParams() {
    const { salt, token } = this._genSalt();
    return {
      u: this.username,
      t: token,
      s: salt,
      v: '1.16.1',
      c: 'MyApp',
      f: 'json',
    };
  }

  async _get(endpoint, extraParams = {}) {
    const params = { ...this._baseParams(), ...extraParams };
    const response = await axios.get(`${this.url}/rest/${endpoint}`, { params });
    return response.data;
  }

  // --- Public Methods ---

  async getPlaylists() {
    return this._get('getPlaylists.view');
  }

  async getSong(id) {
    const data = await this._get('getSong.view', { id });
    return data['subsonic-response'].song;
  }

  async getSongsInPlaylist(playlist) {
    return this._get('getPlaylist.view', { id: playlist });
  }

  async songDetails(artist, title) {
    try {
      // Use 'lastfm' npm package instead of pylast
      const LastFm = require('lastfm-node-client');
      const lastfm = new LastFm(this.api, this.secret, this.lfmUser, this.lfmPassword);
      return await lastfm.albumGetInfo({ artist, album: title });
    } catch (err) {
      console.error(`Failed: ${err.message}`);
      return false;
    }
  }

  _coverArtUrl(id) {
    const { salt, token } = this._genSalt();
    const params = new URLSearchParams({
      u: this.username,
      t: token,
      s: salt,
      v: '1.16.1',
      c: 'myClient',
      f: 'json',
      id,
      size: '300',
    });
    return `${this.url}/rest/getCoverArt.view?${params.toString()}`;
  }

  async playlistCover(playlistName) {
    const data = await this.getPlaylists();
    const playlists = data['subsonic-response'].playlists.playlist;
    const match = playlists.find((p) => p.name === playlistName);
    if (!match) throw new Error(`Playlist "${playlistName}" not found`);
    return this._coverArtUrl(match.coverArt);
  }

  albumCover(songId) {
    return this._coverArtUrl(songId);
  }
}

module.exports = PySubsonic;