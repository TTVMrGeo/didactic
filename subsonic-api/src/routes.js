const express = require('express');
const router = express.Router();

module.exports = (client) => {
  router.get('/playlists', async (req, res) => {
    try {
      res.json(await client.getPlaylists());
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  router.get('/song/:id', async (req, res) => {
    try {
      res.json(await client.getSong(req.params.id));
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  router.get('/playlist/:id/songs', async (req, res) => {
    try {
      res.json(await client.getSongsInPlaylist(req.params.id));
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  router.get('/playlist/:name/cover', async (req, res) => {
    try {
      res.json({ url: await client.playlistCover(req.params.name) });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  router.get('/album/:id/cover', (req, res) => {
    res.json({ url: client.albumCover(req.params.id) });
  });

  router.get('/song-details', async (req, res) => {
    const { artist, title } = req.query;
    try {
      res.json(await client.songDetails(artist, title));
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  return router;
};