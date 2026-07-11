import http.server
import socketserver
import urllib.request
import urllib.parse
import re
import json
import html
import os
import mimetypes
import ssl

PORT = 8080

# Bypass SSL verify for secure connections (e.g. MangaDex/CDN SSL mismatches)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Force register correct MIME types to prevent Windows registry pollution (e.g. .css served as text/plain)
mimetypes.init()
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/html', '.html')
mimetypes.add_type('image/jpeg', '.jpg')
mimetypes.add_type('image/jpeg', '.jpeg')
mimetypes.add_type('image/png', '.png')
mimetypes.add_type('image/svg+xml', '.svg')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

def fetch_html(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as res:
        return res.read().decode('utf-8', errors='ignore')

def parse_card(part):
    slug_match = re.search(r'href="https://bacakomik.my/komik/([^/]+)/"', part)
    title_match = re.search(r'title="(?:Komik|Manga)\s*([^"]+)"', part)
    if not title_match:
        title_match = re.search(r'<h4>([^<]+)</h4>', part)
        
    cover_match = re.search(r'data-lazy-src="([^"]+)"', part)
    if not cover_match:
        cover_match = re.search(r'<noscript><img[^>]+src="([^"]+)"', part)
        
    type_match = re.search(r'class="typeflag\s*([^"]+)"', part)
    
    # Match rating
    rating_match = re.search(r'<div class="rating">.*?<i>([\d\.]+)</i>', part, re.DOTALL)
    if not rating_match:
        rating_match = re.search(r'(?:⭐|<i class="fa(?:s)? fa-star"></i>)\s*([\d\.]+)', part)
    
    # Chapter info
    ch_match = re.search(r'href="https://bacakomik.my/([^"]+)-chapter-([\d\.]+)/"', part)
    latest_ch = 1
    if ch_match:
        latest_ch = float(ch_match.group(2))
        if latest_ch.is_integer():
            latest_ch = int(latest_ch)
    else:
        ch_text_match = re.search(r'Ch\.\s*([\d\.]+)', part)
        if ch_text_match:
            latest_ch = float(ch_text_match.group(1))
            if latest_ch.is_integer():
                latest_ch = int(latest_ch)

    slug = slug_match.group(1) if slug_match else "unknown"
    title = title_match.group(1).strip() if title_match else slug.replace('-', ' ').title()
    cover = cover_match.group(1) if cover_match else "/assets/manga_cover_1.jpg"
    manga_type = type_match.group(1).strip() if type_match else "Manga"
    rating = float(rating_match.group(1)) if rating_match else 7.5

    if cover.startswith('//'):
        cover = 'https:' + cover

    return {
        "id": slug,
        "title": title,
        "type": manga_type,
        "rating": rating,
        "rank": 99,
        "latestChapter": latest_ch,
        "cover": cover,
        "author": "Unknown",
        "genres": ["Action"],
        "synopsis": "Sinopsis tidak tersedia.",
        "updatedAt": "Baru saja"
    }

def scrape_details(slug):
    url = f"https://bacakomik.my/komik/{slug}/"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=8) as res:
            content = res.read().decode('utf-8', errors='ignore')
            
            # Title
            title_match = re.search(r'<div class="dtlx"><h1>([^<]+)</h1>', content)
            title = title_match.group(1).strip() if title_match else slug.replace('-', ' ').title()
            
            # Cover
            cover_match = re.search(r'class="thumb"[^>]*>.*?<img[^>]+src="([^"]+)"', content, re.DOTALL)
            if not cover_match:
                cover_match = re.search(r'class="thumb"[^>]*>.*?<img[^>]+data-lazy-src="([^"]+)"', content, re.DOTALL)
            cover = cover_match.group(1) if cover_match else "/assets/manga_cover_1.jpg"
            if cover.startswith('//'):
                cover = 'https:' + cover
                
            # Synopsis
            syn_match = re.search(r'class="[^"]*entry-content[^"]*" itemprop="description">([\s\S]*?)</div>', content)
            if not syn_match:
                syn_match = re.search(r'class="[^"]*sinopsis[^"]*">([\s\S]*?)</div>', content)
            synopsis = re.sub(r'<[^>]+>', '', syn_match.group(1)).strip() if syn_match else "Sinopsis tidak tersedia."
            
            # Author
            author_match = re.search(r'<span><b>Author:</b>\s*([^<]+)</span>', content, re.IGNORECASE)
            author = author_match.group(1).strip() if author_match else "Unknown"
            
            # Genres
            genre_info_match = re.search(r'<div class="genre-info[^"]*">([\s\S]*?)</div>', content)
            genres = []
            if genre_info_match:
                genres = re.findall(r'<a[^>]*>([^<]+)</a>', genre_info_match.group(1))
            if not genres:
                genres = ["Action"]
                
            # Type
            type_match = re.search(r'<span><b>Type:</b>\s*([^<]+)</span>', content, re.IGNORECASE)
            manga_type = type_match.group(1).strip() if type_match else "Manga"
            
            # Rating
            rating_match = re.search(r'itemprop="ratingValue"[^>]*>\s*([\d\.]+)', content)
            if not rating_match:
                rating_match = re.search(r'<div class="rating">.*?<i>([\d\.]+)</i>', content, re.DOTALL)
            rating = float(rating_match.group(1)) if rating_match else 7.5
            
            # Chapters
            ch_matches = re.findall(r'href="https://bacakomik.my/([^"]+-chapter-([\d\.]+)/)"', content)
            seen = set()
            chapters = []
            for ch_path, num_str in ch_matches:
                ch_num = float(num_str)
                if ch_num.is_integer():
                    ch_num = int(ch_num)
                if ch_num not in seen:
                    seen.add(ch_num)
                    chapters.append({
                        "chapter_number": ch_num,
                        "title": f"Chapter {ch_num}"
                    })
            chapters.sort(key=lambda x: x["chapter_number"], reverse=True)
            latest_ch = chapters[0]["chapter_number"] if chapters else 1
            
            return {
                "id": slug,
                "title": title,
                "type": manga_type,
                "rating": rating,
                "rank": 99,
                "latestChapter": latest_ch,
                "cover": cover,
                "author": author,
                "genres": genres,
                "synopsis": synopsis,
                "chapters": chapters
            }
    except Exception as e:
        print(f"Error scraping details for {slug}: {e}")
    return None

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
        # API: Get Popular Manga (from bacakomik.my)
        if self.path == '/api/popular':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                html_content = fetch_html("https://bacakomik.my/")
                pop_start = html_content.find('mangapopuler')
                pop_end = html_content.find('chapterbaru')
                if pop_start != -1 and pop_end != -1:
                    block = html_content[pop_start:pop_end]
                else:
                    block = html_content
                    
                parts = block.split('<div class="animepost">')[1:]
                mangas = []
                for idx, p in enumerate(parts[:12]):
                    card = parse_card(p)
                    card["rank"] = idx + 1
                    mangas.append(card)
                self.wfile.write(json.dumps(mangas).encode('utf-8'))
            except Exception as e:
                print("Error popular API:", e)
                self.wfile.write(json.dumps([]).encode('utf-8'))
                
        # API: Get Latest Manga Updates (from bacakomik.my)
        elif self.path == '/api/updates':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                html_content = fetch_html("https://bacakomik.my/")
                pop_end = html_content.find('chapterbaru')
                if pop_end != -1:
                    block = html_content[pop_end:]
                else:
                    block = html_content
                    
                parts = block.split('<div class="animepost">')[1:]
                mangas = []
                times = ["2 mnt lalu", "15 mnt lalu", "45 mnt lalu", "1 jam lalu", "2 jam lalu", "4 jam lalu", "6 jam lalu", "12 jam lalu", "1 hari lalu"]
                for idx, p in enumerate(parts[:9]):
                    card = parse_card(p)
                    card["updatedAt"] = times[idx] if idx < len(times) else "Baru saja"
                    mangas.append(card)
                self.wfile.write(json.dumps(mangas).encode('utf-8'))
            except Exception as e:
                print("Error updates API:", e)
                self.wfile.write(json.dumps([]).encode('utf-8'))
                
        # API: Search suggestions (relays suggestions server-side or filters local database)
        elif self.path.startswith('/api/search'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            query = params.get('q', [''])[0].strip()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if not query:
                self.wfile.write(json.dumps([]).encode('utf-8'))
                return
                
            try:
                html_content = fetch_html(f"https://bacakomik.my/?s={urllib.parse.quote(query)}")
                parts = html_content.split('<div class="animepost">')[1:]
                results = []
                for p in parts[:6]:
                    results.append(parse_card(p))
                self.wfile.write(json.dumps(results).encode('utf-8'))
            except Exception as e:
                print("Error search API:", e)
                self.wfile.write(json.dumps([]).encode('utf-8'))

        # API: Get Paginated Manga Directory (from bacakomik.my)
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
            
            try:
                query_parts = []
                if manga_type and manga_type != 'all':
                    m_type = manga_type.lower()
                    query_parts.append(f"type={m_type}")
                if genre and genre != 'all':
                    query_parts.append(f"genre={genre.lower()}")
                if sort:
                    sort_val = 'update'
                    if sort == 'rating' or sort == 'popular':
                        sort_val = 'popular'
                    elif sort == 'alphabet':
                        sort_val = 'title'
                    query_parts.append(f"order={sort_val}")
                    
                query_str = "&".join(query_parts)
                url = f"https://bacakomik.my/daftar-komik/page/{page}/"
                if query_str:
                    url += f"?{query_str}"
                    
                html_content = fetch_html(url)
                
                parts = html_content.split('<div class="animepost">')[1:]
                paginated_data = []
                for p in parts:
                    paginated_data.append(parse_card(p))
                    
                # Detect max pages
                last_page = 1
                pag_match = re.search(r'<div class="pagination">([\s\S]*?)</div>', html_content)
                if pag_match:
                    pages = re.findall(r'page/(\d+)/', pag_match.group(1))
                    if pages:
                        last_page = max(map(int, pages))
                
                payload = {
                    "current_page": page,
                    "last_page": last_page,
                    "total": last_page * len(paginated_data) if paginated_data else 0,
                    "data": paginated_data
                }
                self.wfile.write(json.dumps(payload).encode('utf-8'))
            except Exception as e:
                print("Error directory API:", e)
                self.wfile.write(json.dumps({"current_page":1,"last_page":1,"total":0,"data":[]}).encode('utf-8'))

        # API: Get Manga Details dynamically (to populate Modal with real genres/synopsis)
        elif self.path.startswith('/api/manga'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            slug = params.get('id', [''])[0]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if not slug:
                self.wfile.write(json.dumps({"error": "Missing id parameter"}).encode('utf-8'))
                return
                
            details = scrape_details(slug)
            if details:
                self.wfile.write(json.dumps(details).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"error": "Failed to scrape details"}).encode('utf-8'))

        # API: Get Chapter Reading Images (from bacakomik.my)
        elif self.path.startswith('/api/read'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            manga_id = params.get('manga', [''])[0]
            chapter_num = params.get('chapter', ['1'])[0]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if not manga_id:
                self.wfile.write(json.dumps({"error": "Missing manga parameter"}).encode('utf-8'))
                return
                
            try:
                reader_url = f"https://bacakomik.my/{manga_id}-chapter-{chapter_num}/"
                content = fetch_html(reader_url)
                
                # Extract image list inside anjay_ini_id_kh block
                start_pos = content.find('<div id="anjay_ini_id_kh">')
                if start_pos != -1:
                    end_pos = content.find('<div class="navig"', start_pos)
                    if end_pos != -1:
                        block = content[start_pos:end_pos]
                    else:
                        block = content[start_pos:start_pos+30000]
                    
                    noscript_imgs = re.findall(r'<noscript><img[^>]+src="([^"]+)"', block)
                    mapped_images = []
                    for src in noscript_imgs:
                        if src.startswith('//'):
                            src = 'https:' + src
                        mapped_images.append(f"/api/proxy-img?url={urllib.parse.quote(src)}")
                else:
                    mapped_images = []
                
                # Fetch details page to get list of all chapters for the dropdown selector
                details = scrape_details(manga_id)
                all_chapters = details["chapters"] if details else []
                manga_title = details["title"] if details else manga_id.replace('-', ' ').title()
                
                # Fallback if no chapters parsed
                if not all_chapters:
                    latest_ch = 100
                    try:
                        latest_ch = int(float(chapter_num))
                    except:
                        pass
                    for c in range(1, latest_ch + 20):
                        all_chapters.append({
                            "chapter_number": c,
                            "title": f"Chapter {c}"
                        })
                    all_chapters.sort(key=lambda x: x["chapter_number"], reverse=True)
                
                payload = {
                    "manga_title": manga_title,
                    "manga_id": manga_id,
                    "chapter_title": f"Chapter {chapter_num}",
                    "chapter_number": chapter_num,
                    "images": mapped_images,
                    "prev_chapter": str(int(float(chapter_num)) - 1) if float(chapter_num) > 1 else None,
                    "next_chapter": str(int(float(chapter_num)) + 1) if float(chapter_num) < len(all_chapters) else None,
                    "chapters": all_chapters
                }
                
                # Check actual prev/next from the chapters list if available
                if details and details.get("chapters"):
                    ch_nums = [c["chapter_number"] for c in details["chapters"]]
                    try:
                        curr_num = float(chapter_num)
                        if curr_num.is_integer():
                            curr_num = int(curr_num)
                        if curr_num in ch_nums:
                            idx = ch_nums.index(curr_num)
                            payload["prev_chapter"] = str(ch_nums[idx + 1]) if idx + 1 < len(ch_nums) else None
                            payload["next_chapter"] = str(ch_nums[idx - 1]) if idx - 1 >= 0 else None
                    except Exception as ex:
                        print("Error resolving prev/next:", ex)
                
                self.wfile.write(json.dumps(payload).encode('utf-8'))
            except Exception as e:
                print(f"Error serving read chapter {manga_id} ch {chapter_num}: {e}")
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

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
                        'Referer': 'https://bacakomik.my/'
                    }
                )
                with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                    content_type = response.headers.get('Content-Type', 'image/jpeg')
                    self.send_response(200)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Cache-Control', 'public, max-age=86400')
                    self.end_headers()
                    
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

# Avoid port in use errors on server restart
socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("", PORT), ScraperHandler) as httpd:
    print(f"KomikID Live WordPress Scraper Server running at http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()
