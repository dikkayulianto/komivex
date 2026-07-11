import http.server
import socketserver
import urllib.parse
import json
import os
import mimetypes

PORT = 8080

# Force register correct MIME types to prevent Windows registry pollution (e.g. .css served as text/plain)
mimetypes.init()
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/html', '.html')
mimetypes.add_type('image/jpeg', '.jpg')
mimetypes.add_type('image/jpeg', '.jpeg')
mimetypes.add_type('image/png', '.png')
mimetypes.add_type('image/svg+xml', '.svg')

# 1. Local Stable Manga Database
LOCAL_MANGA_DB = [
    {
        "id": "one-piece",
        "title": "One Piece",
        "type": "Manga",
        "rating": 9.2,
        "rank": 1,
        "latestChapter": 1187,
        "cover": "/assets/manga_cover_1.jpg",
        "author": "Eiichiro Oda",
        "genres": ["Action", "Adventure", "Fantasy", "Comedy"],
        "synopsis": "Gol D. Roger dikenal sebagai Raja Bajak Laut, bajak laut terkuat dan paling terkenal yang pernah berlayar di Grand Line. Sebelum eksekusinya, ia mengungkapkan keberadaan hartanya yang legendaris, One Piece. Monkey D. Luffy, seorang remaja berusia 17 tahun yang memakan Buah Iblis Gomu Gomu, berangkat dalam petualangan besar untuk menemukan One Piece dan menjadi Raja Bajak Laut yang baru.",
        "updatedAt": "10 menit yang lalu"
    },
    {
        "id": "solo-leveling",
        "title": "Solo Leveling",
        "type": "Manhwa",
        "rating": 9.6,
        "rank": 2,
        "latestChapter": 200,
        "cover": "/assets/manga_cover_2.jpg",
        "author": "Chugong",
        "genres": ["Action", "Fantasy", "Adventure"],
        "synopsis": "Di dunia di mana monster bermunculan dari portal dimensi (gate), orang-orang biasa dibekali kekuatan supranatural untuk memburu mereka, disebut Hunters. Sung Jin-Woo adalah Hunter terlemah kelas E yang berjuang bertahan hidup demi biaya rumah sakit ibunya. Suatu hari ia mendapat sistem unik yang memungkinkannya menaikkan level kekuatannya tanpa batas.",
        "updatedAt": "25 menit yang lalu"
    },
    {
        "id": "martial-peak",
        "title": "Martial Peak",
        "type": "Manhua",
        "rating": 7.8,
        "rank": 3,
        "latestChapter": 3882,
        "cover": "/assets/manga_cover_3.jpg",
        "author": "Momo",
        "genres": ["Action", "Fantasy", "Adventure"],
        "synopsis": "Perjalanan ke puncak bela diri adalah jalan yang sepi, sunyi, dan panjang. Di hadapan kesulitan, kamu harus tetap tegar dan tak tergoyahkan. Hanya dengan begitu kamu dapat menerobos dan melanjutkan perjalananmu untuk menjadi yang terkuat.",
        "updatedAt": "1 jam yang lalu"
    },
    {
        "id": "lookism",
        "title": "Lookism",
        "type": "Manhwa",
        "rating": 8.9,
        "rank": 4,
        "latestChapter": 585,
        "cover": "/assets/manga_cover_4.jpg",
        "author": "Park Tae-jun",
        "genres": ["Action", "Comedy", "Drama"],
        "synopsis": "Daniel Park adalah seorang siswa SMA penyendiri yang sering dirundung karena penampilannya yang gemuk dan tidak menarik. Suatu hari, ia terbangun dalam tubuh baru yang sangat tampan, atletis, dan sempurna.",
        "updatedAt": "2 jam yang lalu"
    },
    {
        "id": "rebirth-urban-cultivator",
        "title": "Rebirth Of The Urban Immortal Cultivator",
        "type": "Manhua",
        "rating": 8.2,
        "rank": 5,
        "latestChapter": 1064,
        "cover": "/assets/manga_cover_3.jpg",
        "author": "Tenisi",
        "genres": ["Action", "Fantasy"],
        "synopsis": "Chen Fan, seorang kultivator tertinggi yang jatuh saat menerobos kesengsaraan surgawi, bereinkarnasi kembali ke masa mudanya saat tinggal di bumi. Berbekal memori ribuan tahun kultivasi, ia memutuskan untuk melindungi orang-orang yang dicintainya dan menghancurkan musuh-musuh masa lalunya dengan kekuatan absolut.",
        "updatedAt": "4 jam yang lalu"
    },
    {
        "id": "new-career-every-week",
        "title": "I Randomly Have A New Career Every Week",
        "type": "Manhua",
        "rating": 8.5,
        "rank": 6,
        "latestChapter": 890,
        "cover": "/assets/manga_cover_4.jpg",
        "author": "Chao Shen",
        "genres": ["Comedy", "Romance", "Action"],
        "synopsis": "Lin Yi, seorang pemuda biasa, tiba-tiba mendapatkan sistem misterius yang memberikannya karir baru secara acak setiap minggu. Dari kurir makanan biasa, sopir taksi mewah, hingga agen rahasia dunia.",
        "updatedAt": "6 jam yang lalu"
    },
    {
        "id": "naruto",
        "title": "Naruto",
        "type": "Manga",
        "rating": 8.8,
        "rank": 7,
        "latestChapter": 700,
        "cover": "/assets/manga_cover_1.jpg",
        "author": "Masashi Kishimoto",
        "genres": ["Action", "Adventure", "Fantasy"],
        "synopsis": "Naruto Uzumaki adalah ninja yatim piatu berisik yang memiliki monster rubah ekor sembilan tersegel di dalam dirinya. Dia bermimpi menjadi Hokage, pemimpin desa ninja Konoha, demi mendapatkan pengakuan dari semua orang.",
        "updatedAt": "12 jam yang lalu"
    },
    {
        "id": "bleach",
        "title": "Bleach",
        "type": "Manga",
        "rating": 8.5,
        "rank": 8,
        "latestChapter": 686,
        "cover": "/assets/manga_cover_2.jpg",
        "author": "Tite Kubo",
        "genres": ["Action", "Adventure", "Fantasy"],
        "synopsis": "Ichigo Kurosaki adalah siswa SMA berambut oranye yang bisa melihat roh gentayangan. Hidupnya berubah selamanya setelah ia bertemu Rukia Kuchiki, seorang Shinigami (Dewa Kematian), dan mewarisi kekuatannya untuk bertarung melawan monster Hollow.",
        "updatedAt": "1 hari yang lalu"
    },
    {
        "id": "chainsaw-man",
        "title": "Chainsaw Man",
        "type": "Manga",
        "rating": 8.7,
        "rank": 9,
        "latestChapter": 160,
        "cover": "/assets/manga_cover_3.jpg",
        "author": "Tatsuki Fujimoto",
        "genres": ["Action", "Supernatural"],
        "synopsis": "Denji adalah seorang pemuda miskin yang bekerja sebagai Devil Hunter demi melunasi hutang ayahnya kepada Yakuza dengan bantuan anjing iblisnya, Pochita. Setelah dikhianati dan dibunuh, Denji bergabung dengan Pochita menjadi Chainsaw Man.",
        "updatedAt": "2 hari lalu"
    },
    {
        "id": "jujutsu-kaisen",
        "title": "Jujutsu Kaisen",
        "type": "Manga",
        "rating": 8.9,
        "rank": 10,
        "latestChapter": 262,
        "cover": "/assets/manga_cover_4.jpg",
        "author": "Gege Akutami",
        "genres": ["Action", "Supernatural"],
        "synopsis": "Yuji Itadori adalah siswa SMA berbakat fisik luar biasa yang secara tidak sengaja memakan jari iblis legendaris Ryomen Sukuna untuk menyelamatkan teman-temannya. Ia terpaksa memasuki dunia sekolah penyihir Jujutsu untuk mengumpulkan sisa jari Sukuna.",
        "updatedAt": "3 hari lalu"
    }
]

class ScraperHandler(http.server.SimpleHTTPRequestHandler):
    # Ensure correct extensions map is used
    extensions_map = http.server.SimpleHTTPRequestHandler.extensions_map.copy()
    extensions_map.update({
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.html': 'text/html',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.svg': 'image/svg+xml'
    })

    def do_GET(self):
        # API: Get Popular Manga (from local stable database)
        if self.path == '/api/popular':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(LOCAL_MANGA_DB).encode('utf-8'))
                
        # API: Get Latest Manga Updates
        elif self.path == '/api/updates':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Use top 9 manga as updates
            updates = LOCAL_MANGA_DB[:9]
            self.wfile.write(json.dumps(updates).encode('utf-8'))
                
        # API: Search suggestions (relays suggestions server-side or filters local database)
        elif self.path.startswith('/api/search'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            query = params.get('q', [''])[0].strip().lower()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if not query:
                self.wfile.write(json.dumps([]).encode('utf-8'))
                return
                
            results = []
            for manga in LOCAL_MANGA_DB:
                if query in manga['title'].lower() or any(query in g.lower() for g in manga['genres']):
                    results.append(manga)
            self.wfile.write(json.dumps(results).encode('utf-8'))

        # API: Get Paginated Manga Directory
        elif self.path.startswith('/api/mangas'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            page = int(params.get('page', ['1'])[0])
            manga_type = params.get('type', [''])[0]
            genre = params.get('genre', [''])[0]
            sort = params.get('sort', [''])[0]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Apply filters
            filtered = LOCAL_MANGA_DB
            if manga_type and manga_type != 'all':
                filtered = [m for m in filtered if m['type'].lower() == manga_type.lower()]
            if genre and genre != 'all':
                filtered = [m for m in filtered if genre.lower() in [g.lower() for g in m['genres']]]
            
            # Apply sorting
            if sort == 'rating':
                filtered = sorted(filtered, key=lambda x: x['rating'], reverse=True)
            elif sort == 'rank' or sort == 'popular':
                filtered = sorted(filtered, key=lambda x: x['rank'])
            elif sort == 'alphabet':
                filtered = sorted(filtered, key=lambda x: x['title'].lower())
                
            # Paginate: 6 items per page for directory
            items_per_page = 6
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            paginated_data = filtered[start_idx:end_idx]
            
            total_pages = (len(filtered) + items_per_page - 1) // items_per_page
            
            payload = {
                "current_page": page,
                "last_page": max(1, total_pages),
                "total": len(filtered),
                "data": paginated_data
            }
            self.wfile.write(json.dumps(payload).encode('utf-8'))

        # API: Get Chapter Reading Images (from local stable database using placeholder service)
        elif self.path.startswith('/api/read'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            manga_id = params.get('manga', [''])[0]
            chapter_num = int(params.get('chapter', ['1'])[0])
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if not manga_id:
                self.wfile.write(json.dumps({"error": "Missing manga parameter"}).encode('utf-8'))
                return
                
            # Find manga in local db
            manga = next((m for m in LOCAL_MANGA_DB if m['id'] == manga_id), None)
            manga_title = manga['title'] if manga else manga_id.replace('-', ' ').title()
            latest_ch = manga['latestChapter'] if manga else 100
            
            # Generate stable, clean mock reading pages using placehold.co API
            # This requires no scraping, has no hotlinking protections, and loads instantly
            pages_count = 10
            mapped_images = [
                f"https://placehold.co/700x1000/0f172a/94a3b8?text={urllib.parse.quote(manga_title)}+-+Chapter+{chapter_num}+-+Halaman+{i}"
                for i in range(1, pages_count + 1)
            ]
            
            # Generate chapters list
            all_chapters = []
            for c in range(1, latest_ch + 1):
                all_chapters.append({
                    "chapter_number": c,
                    "title": f"Chapter {c}"
                })
            
            payload = {
                "manga_title": manga_title,
                "manga_id": manga_id,
                "chapter_title": f"Chapter {chapter_num}",
                "chapter_number": chapter_num,
                "images": mapped_images,
                "prev_chapter": chapter_num - 1 if chapter_num > 1 else None,
                "next_chapter": chapter_num + 1 if chapter_num < latest_ch else None,
                "chapters": all_chapters
            }
            self.wfile.write(json.dumps(payload).encode('utf-8'))

        # API: Proxy Image (not needed for local placeholder but kept for compatibility)
        elif self.path.startswith('/api/proxy-img'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            img_url = params.get('url', [''])[0]
            
            if not img_url:
                self.send_response(400)
                self.end_headers()
                return
                
            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.end_headers()
            self.wfile.write(b'')

        # Fallback to standard static file server
        else:
            super().do_GET()

# Avoid port in use errors on server restart
socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("", PORT), ScraperHandler) as httpd:
    print(f"KomikID Stable Local Server running at http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()
