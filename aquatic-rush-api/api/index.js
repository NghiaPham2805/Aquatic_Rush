const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');

const app = express();
app.use(cors());
app.use(express.json());

// Connect to Neon PostgreSQL
const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
});

// GET: Fetch top 10 scores
app.get('/api', async (req, res) => {
    try {
        const result = await pool.query('SELECT player_name, score FROM leaderboard ORDER BY score DESC LIMIT 10');
        res.status(200).json(result.rows);
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: 'Database error' });
    }
});

// POST: Submit a new score
app.post('/api', async (req, res) => {
    const { player_name, score } = req.body;
    if (!player_name || score === undefined) {
        return res.status(400).json({ error: 'Missing name or score' });
    }
    
    try {
        await pool.query('INSERT INTO leaderboard (player_name, score) VALUES ($1, $2)', [player_name, score]);
        res.status(201).json({ message: 'Score saved' });
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: 'Database error' });
    }
});

module.exports = app;