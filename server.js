const express = require('express');
const axios = require('axios');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8080;

// Serve static frontend files
app.use(express.static(__dirname));

// Set up standard browser Headers to avoid getting blocked
const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
};

// Helper to decode HTML entities extracted from attributes
function decodeHtmlEntities(str) {
    if (!str) return '';
    return str
        .replace(/&quot;/g, '"')
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&#039;/g, "'")
        .replace(/&#x27;/g, "'");
}

// Scrape HTML and extract Inertia.js data-page
async function getKomikIdData() {
    try {
        const response = await axios.get('https://komikid.net/', { headers, timeout: 8000 });
        const html = response.data;
        const match = html.match(/data-page="([^"]+)"/);
        
        if (match) {
            const unescaped = decodeHtmlEntities(match[1]);
            const parsed = JSON.parse(unescaped);
            return parsed.props || {};
        }
        throw new Error("Could not find data-page attribute");
    } catch (err) {
        console.error("Error scraping komikid.net: ", err.message);
        return null;
    }
}

// 1. API: Get Popular Manga (scraped from komikid.net)
app.get('/api/popular', async (req, res) => {
    const props = await getKomikIdData();
    
    if (props && props.popularManga) {
        try {
            const mapped = props.popularManga.map(m => {
                const latestCh = m.last_chapter ? m.last_chapter.chapter_number : 100;
                
                // Get genres array
                const genresList = m.genres ? m.genres.map(g => g.name) : ["Action"];

                return {
                    id: m.slug || m.id.toString(),
                    title: m.title,
                    type: m.type || "Manga",
                    rating: m.rating ? parseFloat(m.rating) : 0.0,
                    rank: m.id % 20 || 99, // use id or index as rank
                    latestChapter: latestCh,
                    cover: m.poster || '/assets/manga_cover_1.jpg',
                    author: m.author && m.author !== '-' ? m.author : "Unknown",
                    genres: genresList,
                    synopsis: m.synopsis || "Sinopsis tidak tersedia untuk judul ini.",
                    updatedAt: "Terbaru"
                };
            });
            return res.json(mapped);
        } catch (e) {
            console.error("Mapping popularManga failed: ", e);
        }
    }
    
    // If scraper fails, return empty or trigger fallback
    res.status(500).json({ error: "Failed to scrape popular manga" });
});

// 2. API: Get Latest Manga Updates
app.get('/api/updates', async (req, res) => {
    const props = await getKomikIdData();
    
    if (props && props.latestMangaUpdates) {
        try {
            const mapped = props.latestMangaUpdates.map((m, idx) => {
                const latestCh = m.last_chapter ? m.last_chapter.chapter_number : 50;
                
                // Custom readable time calculation based on index
                const times = ["5 mnt lalu", "15 mnt lalu", "1 jam lalu", "2 jam lalu", "4 jam lalu", "6 jam lalu", "12 jam lalu", "1 hari lalu", "2 hari lalu"];
                const timeText = times[idx] || "Baru saja";

                return {
                    id: m.slug || m.id.toString(),
                    title: m.title,
                    type: m.type || "Manga",
                    rating: m.rating ? parseFloat(m.rating) : 0.0,
                    rank: idx + 1,
                    latestChapter: latestCh,
                    cover: m.poster || '/assets/manga_cover_1.jpg',
                    author: m.author && m.author !== '-' ? m.author : "Unknown",
                    genres: m.genres ? m.genres.map(g => g.name) : ["Action"],
                    synopsis: m.synopsis || "Sinopsis tidak tersedia.",
                    updatedAt: timeText
                };
            });
            return res.json(mapped);
        } catch (e) {
            console.error("Mapping updates failed: ", e);
        }
    }
    
    res.status(500).json({ error: "Failed to scrape updates" });
});

// 3. API: Search suggestions (relays suggestions server-side to avoid CORS)
app.get('/api/search', async (req, res) => {
    const query = req.query.q || '';
    if (!query) {
        return res.json([]);
    }

    try {
        const response = await axios.get(`https://komikid.net/api/search?q=${encodeURIComponent(query)}`, { headers, timeout: 6000 });
        const results = response.data || [];
        
        // Map komikid suggestions into our standard structure
        const mapped = results.map(item => {
            return {
                id: item.slug || item.id.toString(),
                title: item.title,
                type: item.type || "Manga",
                rating: item.rating ? parseFloat(item.rating) : 0.0,
                rank: 99,
                latestChapter: item.chapters_count || 10,
                cover: item.poster || item.poster_url || '/assets/manga_cover_1.jpg',
                author: item.author || "Unknown",
                genres: item.genres ? item.genres.split(',') : ["Action"], // genres comma-separated string on search api
                synopsis: item.synopsis || "",
                updatedAt: "Baru saja"
            };
        });

        res.json(mapped);
    } catch (err) {
        console.error("Search suggestion relay failed: ", err.message);
        res.json([]); // return empty array on failure so frontend doesn't break
    }
});

// Serve index.html for all other routes (SPA fallback)
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Start listening
app.listen(PORT, () => {
    console.log(`KomikID Scraper Proxy server running at http://localhost:${PORT}`);
});
