require('dotenv').config();
const express = require('express');
const PySubsonic = require('./src/pySubsonic');
const routes = require('./src/routes');

const app = express();
app.use(express.json());

const client = new PySubsonic({
  url: process.env.SUBSONIC_URL,
  username: process.env.SUBSONIC_USER,
  password: process.env.SUBSONIC_PASS,
  api: process.env.LFM_API_KEY,
  secret: process.env.LFM_SECRET,
  lfmUser: process.env.LFM_USER,
  lfmPassword: process.env.LFM_PASS,
});

app.use('/api', routes(client));

app.listen(3000, () => console.log('Server running on port 3000'));