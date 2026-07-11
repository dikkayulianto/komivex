import http.server
import socketserver
import urllib.request
import urllib.parse
import re
import json
import html
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
        # API: Get Popular Manga (scraped from komikid.net)
        if self.path == '/api/popular':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            data = self.scrape_komikid()
            if data and 'popularManga' in data:
                mapped = []
                for m in data['popularManga']:
                    latest_ch = 100
                    if m.get('last_chapter'):
                        latest_ch = m['last_chapter'].get('chapter_number', 100)
                    
                    genres_list = [g.get('name', 'Action') for g in m.get('genres', [])] if m.get('genres') else ["Action"]
                    
                    mapped.append({
                        "id": m.get("slug") or str(m.get("id")),
                        "title": m.get("title"),
                        "type": m.get("type", "Manga"),
                        "rating": float(m.get("rating") or 0.0) if m.get("rating") else 0.0,
                        "rank": int(m.get("id", 99) % 20) or 99,
                        "latestChapter": latest_ch,
                        "cover": m.get("poster") or "/assets/manga_cover_1.jpg",
                        "author": m.get("author") if m.get("author") and m.get("author") != '-' else "Unknown",
                        "genres": genres_list,
                        "synopsis": m.get("synopsis") or "Sinopsis tidak tersedia untuk judul ini.",
                        "updatedAt": "Terbaru"
                    })
                self.wfile.write(json.dumps(mapped).encode('utf-8'))
            else:
                self.send_error_response("Failed to scrape popular manga")
                
        # API: Get Latest Manga Updates
        elif self.path == '/api/updates':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            data = self.scrape_komikid()
            if data and 'latestMangaUpdates' in data:
                mapped = []
                times = ["5 mnt lalu", "15 mnt lalu", "1 jam lalu", "2 jam lalu", "4 jam lalu", "6 jam lalu", "12 jam lalu", "1 hari lalu", "2 hari lalu"]
                for idx, m in enumerate(data['latestMangaUpdates']):
                    latest_ch = 50
                    if m.get('last_chapter'):
                        latest_ch = m['last_chapter'].get('chapter_number', 50)
                    
                    time_text = times[idx] if idx < len(times) else "Baru saja"
                    genres_list = [g.get('name', 'Action') for g in m.get('genres', [])] if m.get('genres') else ["Action"]

                    mapped.append({
                        "id": m.get("slug") or str(m.get("id")),
                        "title": m.get("title"),
                        "type": m.get("type", "Manga"),
                        "rating": float(m.get("rating") or 0.0) if m.get("rating") else 0.0,
                        "rank": idx + 1,
                        "latestChapter": latest_ch,
                        "cover": m.get("poster") or "/assets/manga_cover_1.jpg",
                        "author": m.get("author") if m.get("author") and m.get("author") != '-' else "Unknown",
                        "genres": genres_list,
                        "synopsis": m.get("synopsis") or "Sinopsis tidak tersedia.",
                        "updatedAt": time_text
                    })
                self.wfile.write(json.dumps(mapped).encode('utf-8'))
            else:
                self.send_error_response("Failed to scrape updates")
                
        # API: Search suggestions (relays suggestions server-side to avoid CORS)
        elif self.path.startswith('/api/search'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            query = params.get('q', [''])[0]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if not query:
                self.wfile.write(json.dumps([]).encode('utf-8'))
                return
                
            results = self.relay_search(query)
            self.wfile.write(json.dumps(results).encode('utf-8'))

        # API: Get Paginated Manga Directory (scraped from komikid.net/manga?page={page})
        elif self.path.startswith('/api/mangas'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            page = params.get('page', ['1'])[0]
            manga_type = params.get('type', [''])[0]
            genre = params.get('genre', [''])[0]
            sort = params.get('sort', [''])[0]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            data = self.scrape_komikid_page(page, manga_type, genre, sort)
            if data and 'mangas' in data:
                mangas_data = data['mangas']
                mapped_data = []
                for m in mangas_data.get('data', []):
                    latest_ch = 100
                    if m.get('last_chapter'):
                        latest_ch = m['last_chapter'].get('chapter_number', 100)
                    
                    genres_list = [g.get('name', 'Action') for g in m.get('genres', [])] if m.get('genres') else ["Action"]
                    
                    mapped_data.append({
                        "id": m.get("slug") or str(m.get("id")),
                        "title": m.get("title"),
                        "type": m.get("type", "Manga"),
                        "rating": float(m.get("rating") or 0.0) if m.get("rating") else 0.0,
                        "rank": 99,
                        "latestChapter": latest_ch,
                        "cover": m.get("poster") or "/assets/manga_cover_1.jpg",
                        "author": m.get("author") if m.get("author") and m.get("author") != '-' else "Unknown",
                        "genres": genres_list,
                        "synopsis": m.get("synopsis") or "Sinopsis tidak tersedia.",
                        "updatedAt": "Terbaru"
                    })
                
                payload = {
                    "current_page": mangas_data.get("current_page", 1),
                    "last_page": mangas_data.get("last_page", 1),
                    "total": mangas_data.get("total", 0),
                    "data": mapped_data
                }
                self.wfile.write(json.dumps(payload).encode('utf-8'))
            else:
                self.send_error_response("Failed to scrape directory")

        # API: Get Chapter Reading Images (scraped from komikid.net/manga/{manga_slug}/chapter/{chapter_number})
        elif self.path.startswith('/api/read'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            manga = params.get('manga', [''])[0]
            chapter_num = params.get('chapter', [''])[0]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if not manga or not chapter_num:
                self.send_error_response("Missing manga or chapter parameter")
                return
                
            data = self.scrape_komikid_chapter(manga, chapter_num)
            if data and 'chapter' in data:
                ch = data['chapter']
                prev_ch = data.get('prev')
                next_ch = data.get('next')
                manga_info = data.get('manga', {})
                
                # Extract image paths sorted by order
                images_list = ch.get('images', [])
                sorted_images = sorted(images_list, key=lambda x: x.get('order', 0))
                mapped_images = [img.get('image_path') for img in sorted_images if img.get('image_path')]
                
                # Fetch list of chapters for dropdown
                all_chapters = []
                for c in data.get('chapters', []):
                    all_chapters.append({
                        "chapter_number": c.get('chapter_number'),
                        "title": c.get('title') or f"Chapter {c.get('chapter_number')}"
                    })
                
                payload = {
                    "manga_title": manga_info.get("title") or manga.replace('-', ' ').title(),
                    "manga_id": manga_info.get("slug") or manga,
                    "chapter_title": ch.get("title") or f"Chapter {chapter_num}",
                    "chapter_number": ch.get("chapter_number"),
                    "images": mapped_images,
                    "prev_chapter": prev_ch.get("chapter_number") if prev_ch else None,
                    "next_chapter": next_ch.get("chapter_number") if next_ch else None,
                    "chapters": all_chapters
                }
                self.wfile.write(json.dumps(payload).encode('utf-8'))
            else:
                self.send_error_response("Failed to scrape chapter images")

        # API: Proxy Image to bypass hotlinking protection
        elif self.path.startswith('/api/proxy-img'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            img_url = params.get('url', [''])[0]
            
            if not img_url:
                self.send_response(400)
                self.end_headers()
                return
                
            try:
                # Add referer matching the image source host to bypass hotlink block
                req = urllib.request.Request(
                    img_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                        'Referer': 'https://komiku.org/'
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    content_type = response.headers.get('Content-Type', 'image/jpeg')
                    self.send_response(200)
                    self.send_header('Content-Type', content_type)
                    # Cache control to avoid repetitive downloading
                    self.send_header('Cache-Control', 'public, max-age=86400')
                    self.end_headers()
                    
                    # Stream the bytes in chunks
                    while True:
                        chunk = response.read(16384)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except Exception as e:
                print("Error proxying image:", img_url, e)
                self.send_response(500)
                self.end_headers()

        # Fallback to standard static file server
        else:
            super().do_GET()
            
    def send_error_response(self, message):
        self.wfile.write(json.dumps({"error": message}).encode('utf-8'))
            
    def scrape_komikid_page(self, page, manga_type='', genre='', sort=''):
        try:
            # Build URL with filters
            query_parts = [f"page={page}"]
            if manga_type and manga_type != 'all':
                query_parts.append(f"type={manga_type.lower()}")
            if genre and genre != 'all':
                query_parts.append(f"genre={genre.lower()}")
            if sort:
                sort_val = 'rating'
                if sort == 'rank' or sort == 'popular':
                    sort_val = 'popular'
                elif sort == 'alphabet' or sort == 'title' or sort == 'az':
                    sort_val = 'title'
                query_parts.append(f"sort={sort_val}")
                
            query_str = "&".join(query_parts)
            url = f"https://komikid.net/manga?{query_str}"
            
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                html_content = response.read().decode('utf-8')
                
            match = re.search(r'data-page="([^"]+)"', html_content)
            if match:
                unescaped = html.unescape(match.group(1))
                parsed = json.loads(unescaped)
                return parsed.get("props", {})
        except Exception as e:
            print(f"Error scraping komikid.net page {page} with query {query_str if 'query_str' in locals() else ''}:", e)
    def scrape_komikid_chapter(self, manga, chapter_num):
        try:
            url = f"https://komikid.net/manga/{manga}/chapter/{chapter_num}"
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                html_content = response.read().decode('utf-8')
                
            match = re.search(r'data-page="([^"]+)"', html_content)
            if match:
                unescaped = html.unescape(match.group(1))
                parsed = json.loads(unescaped)
                return parsed.get("props", {})
        except Exception as e:
            print(f"Error scraping chapter {manga} ch {chapter_num}:", e)
        return None
            
    def scrape_komikid(self):
        try:
            req = urllib.request.Request(
                'https://komikid.net/', 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                html_content = response.read().decode('utf-8')
                
            match = re.search(r'data-page="([^"]+)"', html_content)
            if match:
                unescaped = html.unescape(match.group(1))
                parsed = json.loads(unescaped)
                return parsed.get("props", {})
        except Exception as e:
            print("Error scraping komikid.net:", e)
        return None
        
    def relay_search(self, query):
        try:
            url = f"https://komikid.net/api/search?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                results = json.loads(response.read().decode('utf-8'))
                
            mapped = []
            for item in results:
                genres_val = item.get('genres')
                if isinstance(genres_val, list):
                    genres_list = genres_val
                elif isinstance(genres_val, str):
                    genres_list = [g.strip() for g in genres_val.split(',')]
                else:
                    genres_list = ["Action"]
                
                mapped.append({
                    "id": item.get("slug") or str(item.get("id")),
                    "title": item.get("title"),
                    "type": item.get("type", "Manga"),
                    "rating": float(item.get("rating") or 0.0) if item.get("rating") else 0.0,
                    "rank": 99,
                    "latestChapter": item.get("chapters_count", 10),
                    "cover": f"/api/proxy-img?url={urllib.parse.quote(item.get('poster') or item.get('poster_url'))}" if (item.get('poster') or item.get('poster_url')) else "/assets/manga_cover_1.jpg",
                    "author": item.get("author") or "Unknown",
                    "genres": genres_list,
                    "synopsis": item.get("synopsis") or "",
                    "updatedAt": "Baru saja"
                })
            return mapped
        except Exception as e:
            print("Error search suggestion:", e)
        return []

# Avoid port in use errors on server restart
socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("", PORT), ScraperHandler) as httpd:
    print(f"KomikID Python Scraper Proxy server running at http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()
