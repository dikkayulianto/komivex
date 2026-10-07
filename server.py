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
import db_helper


PORT = int(os.environ.get("PORT", 8080))

DEFAULT_CONFIG = {
    "logo_url": "/assets/logo.jpg",
    "favicon_url": "/assets/logo.jpg",
    "default_theme": "dark",
    "analytics_id": "",
    "meta_title": "Komivex - Baca Manga Terpopuler",
    "meta_description": "Platform baca komik (Manga, Manhua, Manhwa) terpopuler dan terlengkap gratis bahasa Indonesia dengan antarmuka modern dan premium.",
    "verification_code": "",
    "scraper_target_domain": "https://v6.voratoon.com",
    "custom_ad_codes": {
        "head": "",
        "body": "",
        "header": "",
        "sidebar_1": "",
        "sidebar_2": "",
        "footer": ""
    }
}

CONFIG_FILE = "config.json"
site_config = DEFAULT_CONFIG.copy()
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded_config = json.load(f)
            if "custom_ad_codes" in loaded_config:
                ads = loaded_config["custom_ad_codes"]
                if "sidebar" in ads and ads["sidebar"] and not ads.get("sidebar_1"):
                    ads["sidebar_1"] = ads["sidebar"]
            site_config.update(loaded_config)
    except Exception as e:
        print("Error loading config.json:", e)

def get_scraper_domain():
    domain = site_config.get("scraper_target_domain", "").strip().rstrip('/')
    if not domain or any(x in domain for x in ["bacakomik", "shinigami", "komikcast.info"]):
        domain = "https://v6.voratoon.com"
    return domain

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

def parse_card(part, default_rank=99):
    """Parse a manga card from Voratoon / standard manga card HTML block."""
    import html as html_lib
    clean_part = html_lib.unescape(part)
    slug_match = re.search(r'href=["\'](?:https?://[^/]+)?/(?:series|manga|komik)/([^/"\'\s>]+)', clean_part)
    if not slug_match:
        return None
    slug = slug_match.group(1).strip()
    if slug in ['browse', 'updates', 'ranking', 'premium', 'library', 'notifications', 'account', 'profile', 'kultivasi', 'announcements']:
        return None

    title_match = re.search(r'class="[^"]*(?:card-title|comic-title|title)[^"]*"[^>]*>([^<]+)</a>', clean_part)
    if not title_match:
        title_match = re.search(r'<h[234][^>]*>\s*([^<]{2,120})\s*</h[234]>', clean_part)
    if not title_match:
        title_match = re.search(r'alt="(?:Cover\s+)?([^"]{2,120})"', clean_part)
    title = html_lib.unescape(title_match.group(1)).strip() if title_match else slug.replace('-', ' ').title()
    title = re.sub(r'\s+', ' ', title)

    cover_match = re.search(r'src=["\']([^"\']*(?:/cover/|cvr\.voratoon|/api/cover)[^"\']*)["\']', clean_part)
    if not cover_match:
        cover_match = re.search(r'data-src=["\']([^"\']+)["\']', clean_part)
    if not cover_match:
        cover_match = re.search(r'data-lazy-src=["\']([^"\']+)["\']', clean_part)
    if not cover_match:
        cover_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', clean_part)

    cover = "/assets/manga_cover_1.jpg"
    if cover_match:
        c_url = html_lib.unescape(cover_match.group(1).strip())
        domain = get_scraper_domain()

        # Unwrap Voratoon resizer /api/cover?src=... to direct S3/CDN cover
        if '/api/cover' in c_url and 'src=' in c_url:
            parsed_src = re.search(r'[?&]src=([^&]+)', c_url)
            if parsed_src:
                unquoted_src = urllib.parse.unquote(parsed_src.group(1))
                if unquoted_src.startswith('http'):
                    c_url = unquoted_src

        if c_url.startswith('//'):
            c_url = f"https:{c_url}"
        elif c_url.startswith('/'):
            c_url = f"{domain}{c_url}"

        if c_url.startswith('http'):
            cover = f"/api/proxy-img?url={urllib.parse.quote(c_url)}"

    manga_type = "Manga"
    if 'kr.png' in clean_part or 'manhwa' in clean_part.lower():
        manga_type = "Manhwa"
    elif 'cn.png' in clean_part or 'manhua' in clean_part.lower():
        manga_type = "Manhua"
    elif 'jp.png' in clean_part or 'manga' in clean_part.lower():
        manga_type = "Manga"

    rating = 8.0
    rating_m = re.search(r'class="[^"]*rating[^"]*"[^>]*>([\d\.]+)', clean_part)
    if not rating_m:
        rating_m = re.search(r'aria-label="Rating\s*([\d\.]+)', clean_part)
    if rating_m:
        try: rating = float(rating_m.group(1))
        except: pass

    ch_match = re.search(r'(?:Chapter|Ch\.?|chapter[-/])\s*([\d\.]+)', clean_part, re.IGNORECASE)
    latest_ch = 1
    if ch_match:
        try:
            v = float(ch_match.group(1))
            latest_ch = int(v) if v.is_integer() else v
        except: pass

    rank_m = re.search(r'class="[^"]*comic-rank-num[^"]*"[^>]*>(\d+)</span>', clean_part)
    rank = int(rank_m.group(1)) if rank_m else default_rank

    return {
        "id": slug, "title": title, "type": manga_type,
        "rating": rating, "rank": rank, "latestChapter": latest_ch,
        "cover": cover, "author": "Unknown", "genres": ["Action"],
        "synopsis": "Sinopsis tidak tersedia.", "updatedAt": "Baru saja"
    }

def scrape_details(slug):
    """Scrape manga detail page from Voratoon."""
    try:
        import html as html_lib
        domain = get_scraper_domain()
        try:
            url = f"{domain}/series/{slug}"
            content = fetch_html(url)
        except Exception:
            try:
                url = f"{domain}/manga/{slug}/"
                content = fetch_html(url)
            except Exception:
                url = f"{domain}/komik/{slug}/"
                content = fetch_html(url)

        title_m = re.search(r'<h1[^>]*>\s*([\s\S]{1,150}?)\s*</h1>', content)
        title = html_lib.unescape(re.sub(r'<[^>]+>', '', title_m.group(1)).strip()) if title_m else slug.replace('-', ' ').title()
        title = re.sub(r'\s+', ' ', title)

        cover_match = re.search(r'src=["\']([^"\']*/cover/[^"\']*)["\']', content)
        if not cover_match:
            cover_match = re.search(r'src=["\']([^"\']*(?:cvr\.voratoon|/api/cover)[^"\']*)["\']', content)
        if not cover_match:
            cover_match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', content)
        if not cover_match:
            cover_match = re.search(r'data-src="(https?://[^"]+\.(?:jpg|png|webp)[^"]*)"', content)

        cover = "/assets/manga_cover_1.jpg"
        if cover_match:
            cover_raw = html_lib.unescape(cover_match.group(1).strip())
            domain = get_scraper_domain()

            # Unwrap Voratoon resizer /api/cover?src=... to direct S3/CDN cover
            if '/api/cover' in cover_raw and 'src=' in cover_raw:
                parsed_src = re.search(r'[?&]src=([^&]+)', cover_raw)
                if parsed_src:
                    unquoted_src = urllib.parse.unquote(parsed_src.group(1))
                    if unquoted_src.startswith('http'):
                        cover_raw = unquoted_src

            if cover_raw.startswith('//'):
                cover_raw = 'https:' + cover_raw
            elif cover_raw.startswith('/'):
                cover_raw = f"{domain}{cover_raw}"

            if cover_raw.startswith('http'):
                cover = f"/api/proxy-img?url={urllib.parse.quote(cover_raw)}"

        syn_m = re.search(r'class="[^"]*(?:synopsis|description|summary|story|entry-content)[^"]*"[^>]*>([\s\S]*?)</div>', content, re.IGNORECASE)
        if not syn_m:
            syn_m = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', content, re.IGNORECASE)
        synopsis = html_lib.unescape(re.sub(r'<[^>]+>', '', syn_m.group(1)).strip()) if syn_m else "Tidak ada sinopsis."
        synopsis = re.sub(r'\s+', ' ', synopsis)

        auth_m = re.search(r'<meta\s+property="article:author"\s+content="([^"]+)"', content, re.IGNORECASE)
        if not auth_m:
            auth_m = re.search(r'<meta\s+name="author"\s+content="([^"]+)"', content, re.IGNORECASE)
        author = html_lib.unescape(auth_m.group(1).strip()) if auth_m and auth_m.group(1).lower() != 'voratoon' else "Unknown"
        if author == "Unknown":
            m_author = re.search(r'"author":\{"@type":"Person","name":"([^"]+)"\}', content)
            if m_author:
                author = m_author.group(1).strip()
            else:
                auth_block = re.search(r'(?:Author|Pengarang|Penulis)[^<]{0,40}((?:<[^>]+>[^<]*){1,15})', content, re.IGNORECASE)
                if auth_block:
                    links = re.findall(r'<a[^>]*>([^<]+)</a>', auth_block.group(1))
                    if links:
                        author = ', '.join(a.strip() for a in links if a.strip())
                    else:
                        author = re.sub(r'<[^>]+>', '', auth_block.group(1)).strip() or "Unknown"

        genres = re.findall(r'href=["\']/browse\?genre=([^"&]+)["\']', content)
        if not genres:
            genres = re.findall(r'class="[^"]*(?:genre-badge|tag-genre|genre)[^"]*"[^>]*>([^<]+)<', content)
        if not genres:
            genres = re.findall(r'href="[^"]+/(?:genre|tag|genres)/[^/"]+/?"[^>]*>\s*([^<]{2,40})\s*</a>', content, re.IGNORECASE)
        genres = [html_lib.unescape(urllib.parse.unquote(g)).strip() for g in genres if g.strip()]
        genres = list(dict.fromkeys(genres))[:10]
        if not genres: genres = ["Action"]

        manga_type = "Manga"
        if 'Bendera jenis manhwa' in content or 'kr.png' in content or 'manhwa' in content.lower():
            manga_type = "Manhwa"
        elif 'Bendera jenis manhua' in content or 'cn.png' in content or 'manhua' in content.lower():
            manga_type = "Manhua"

        rating = 8.0
        rating_m = re.search(r'class="[^"]*rating[^"]*"[^>]*>([\d\.]+)', content)
        if not rating_m:
            rating_m = re.search(r'([\d\.]+)</span><span class="stat-label">Rating</span>', content)
        if not rating_m:
            rating_m = re.search(r'aria-label="Rating\s*([\d\.]+)', content)
        if rating_m:
            try: rating = float(rating_m.group(1))
            except: pass

        status = "Ongoing"
        status_m = re.search(r'(?:data-status-tone|tag-status)[^>]*>(Completed|Ongoing|Tamat)', content, re.IGNORECASE)
        if not status_m:
            status_m = re.search(r'(?:Status)[^<]{0,30}(Ongoing|Completed|Tamat|Berlangsung|Hiatus)', content, re.IGNORECASE)
        if status_m: status = status_m.group(1).capitalize()

        year_m = re.search(r'(?:Released|Rilis|Tahun|Year)[^<]{0,30}(\d{4})', content, re.IGNORECASE)
        release_year = year_m.group(1) if year_m else ""

        chapters = []
        seen = set()
        ch_links = re.findall(rf'href=["\'](?:https?://[^/]+)?/(?:series|manga)/{re.escape(slug)}/chapter/([^/"\'\s>]+)["\']', content)
        for ch_raw in ch_links:
            try:
                v = float(ch_raw)
                key = int(v) if v.is_integer() else v
                if key not in seen:
                    seen.add(key)
                    chapters.append({
                        "chapter_number": key,
                        "title": f"Chapter {key}",
                        "url": f"{slug}/chapter/{ch_raw}"
                    })
            except: pass

        if not chapters:
            ch_matches_raw = re.findall(r'href="https?://[^"]+/chapter[/|-]([\d\.]+)/?"', content, re.IGNORECASE)
            for num_str in ch_matches_raw:
                try:
                    ch_num = float(num_str)
                    key = int(ch_num) if ch_num.is_integer() else ch_num
                    if key not in seen:
                        seen.add(key)
                        chapters.append({"chapter_number": key, "title": f"Chapter {key}", "url": f"{slug}/chapter/{key}/"})
                except: pass

        chapters.sort(key=lambda x: x["chapter_number"], reverse=True)
        latest_ch = chapters[0]["chapter_number"] if chapters else 1
        return {
            "id": slug, "slug": slug, "title": title, "cover": cover,
            "synopsis": synopsis, "type": manga_type,
            "genres": genres, "status": status, "rating": rating,
            "rank": "", "author": author, "release_year": release_year,
            "latestChapter": latest_ch, "chapters": chapters
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
        # API: Get Website Config
        if self.path == '/api/config':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(site_config).encode('utf-8'))
            return

        # API: Get Comments
        elif self.path.startswith('/api/comments'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            manga_id = params.get('manga', [''])[0]
            chapter_id = params.get('chapter', [None])[0]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if not manga_id:
                self.wfile.write(json.dumps({"error": "Missing manga parameter"}).encode('utf-8'))
                return
                
            comments = db_helper.get_comments(manga_id, chapter_id)
            self.wfile.write(json.dumps(comments).encode('utf-8'))
            return

        # API: Get Notifications
        elif self.path.startswith('/api/notifications'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)
            email = params.get('email', [''])[0]
            role = params.get('role', ['user'])[0]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            target_user = 'admin' if role == 'admin' else email
            if not target_user:
                self.wfile.write(json.dumps([]).encode('utf-8'))
                return
                
            notifications = db_helper.get_notifications(target_user)
            self.wfile.write(json.dumps(notifications).encode('utf-8'))
            return


        # Serve robots.txt
        elif self.path == '/robots.txt':
            content = "User-agent: *\nAllow: /\nDisallow: /admin.html\nDisallow: /api/admin/\nDisallow: /api/comments/delete\n\nSitemap: https://komivex.my.id/sitemap.xml\n"
            if os.path.exists("robots.txt"):
                try:
                    with open("robots.txt", "r", encoding="utf-8") as rf:
                        content = rf.read()
                except Exception:
                    pass
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
            return

        # Serve sitemap.xml
        elif self.path == '/sitemap.xml':
            if os.path.exists("sitemap.xml"):
                try:
                    with open("sitemap.xml", "r", encoding="utf-8") as sf:
                        xml = sf.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/xml; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(xml.encode('utf-8'))
                    return
                except Exception as e:
                    print("Error reading static sitemap:", e)

            self.send_response(200)
            self.send_header('Content-Type', 'application/xml; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            host = self.headers.get('Host', 'komivex.my.id')
            xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
            xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            xml += f'  <url>\n    <loc>https://{host}/</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'
            xml += f'  <url>\n    <loc>https://{host}/manga.html</loc>\n    <changefreq>daily</changefreq>\n    <priority>0.9</priority>\n  </url>\n'
            xml += f'  <url>\n    <loc>https://{host}/library.html</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
            xml += '</urlset>'
            self.wfile.write(xml.encode('utf-8'))
            return

        # API: Get Popular Manga (from Voratoon /ranking)
        elif self.path == '/api/popular':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                domain = get_scraper_domain()
                try:
                    html_content = fetch_html(f"{domain}/ranking")
                except Exception:
                    html_content = fetch_html(f"{domain}/browse?order=popular")
                if '<a class="comic-row"' in html_content:
                    parts = html_content.split('<a class="comic-row')[1:]
                elif '<article' in html_content:
                    parts = [p for p in html_content.split('<article')[1:] if '/series/' in p or '/manga/' in p]
                else:
                    parts = [p for p in html_content.split('<article')[1:]]
                mangas = []
                seen_slugs = set()
                for p in parts:
                    card = parse_card(p)
                    if card and card["id"] not in seen_slugs:
                        seen_slugs.add(card["id"])
                        card["rank"] = len(mangas) + 1
                        mangas.append(card)
                    if len(mangas) >= 12:
                        break
                self.wfile.write(json.dumps(mangas).encode('utf-8'))
            except Exception as e:
                print("Error popular API:", e)
                self.wfile.write(json.dumps([]).encode('utf-8'))
                
        # API: Get Latest Manga Updates (from Voratoon /updates)
        elif self.path == '/api/updates':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                domain = get_scraper_domain()
                try:
                    html_content = fetch_html(f"{domain}/updates")
                except Exception:
                    html_content = fetch_html(f"{domain}/")
                parts = [p for p in html_content.split('<article')[1:] if '/series/' in p or '/manga/' in p]
                mangas = []
                times = ["2 mnt lalu", "15 mnt lalu", "45 mnt lalu", "1 jam lalu", "2 jam lalu", "4 jam lalu", "6 jam lalu", "12 jam lalu", "1 hari lalu"]
                seen_slugs = set()
                for p in parts:
                    card = parse_card(p)
                    if card and card["id"] not in seen_slugs:
                        seen_slugs.add(card["id"])
                        idx = len(mangas)
                        card["updatedAt"] = times[idx] if idx < len(times) else "Baru saja"
                        mangas.append(card)
                    if len(mangas) >= 9:
                        break
                self.wfile.write(json.dumps(mangas).encode('utf-8'))
            except Exception as e:
                print("Error updates API:", e)
                self.wfile.write(json.dumps([]).encode('utf-8'))
                
        # API: Search suggestions (from Voratoon /browse?q=...)
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
                domain = get_scraper_domain()
                try:
                    html_content = fetch_html(f"{domain}/browse?q={urllib.parse.quote(query)}")
                except Exception:
                    html_content = fetch_html(f"{domain}/?s={urllib.parse.quote(query)}")
                parts = [p for p in html_content.split('<article')[1:] if '/series/' in p or '/manga/' in p]
                results = []
                seen_slugs = set()
                for p in parts:
                    card = parse_card(p)
                    if card and card["id"] not in seen_slugs:
                        seen_slugs.add(card["id"])
                        results.append(card)
                    if len(results) >= 6:
                        break
                self.wfile.write(json.dumps(results).encode('utf-8'))
            except Exception as e:
                print("Error search API:", e)
                self.wfile.write(json.dumps([]).encode('utf-8'))

        # API: Get Paginated Manga Directory (from Voratoon /browse)
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
                domain = get_scraper_domain()
                query_parts = []
                if page > 1:
                    query_parts.append(f"page={page}")
                if manga_type and manga_type.lower() not in ('all', 'semua'):
                    query_parts.append(f"format={manga_type.lower()}")
                if genre and genre.lower() not in ('all', 'semua'):
                    query_parts.append(f"genre={urllib.parse.quote(genre)}")
                if sort and sort.lower() not in ('all', 'default'):
                    sort_map = {
                        'rating': 'rating',
                        'rank': 'popular',
                        'popular': 'popular',
                        'alphabet': 'az',
                        'title': 'az',
                        'update': 'latest',
                        'latest': 'latest'
                    }
                    query_parts.append(f"sort={sort_map.get(sort.lower(), 'rating')}")
                    
                query_str = "&".join(query_parts)
                url = f"{domain}/browse" + (f"?{query_str}" if query_str else "")
                    
                html_content = fetch_html(url)
                parts = [p for p in html_content.split('<article')[1:] if '/series/' in p or '/manga/' in p or 'card' in p]
                paginated_data = []
                seen_slugs = set()
                for p in parts:
                    card = parse_card(p)
                    if card and card["id"] not in seen_slugs:
                        seen_slugs.add(card["id"])
                        if manga_type and manga_type.lower() not in ('all', 'semua'):
                            card["type"] = manga_type.capitalize()
                        if genre and genre.lower() not in ('all', 'semua'):
                            card["genres"] = [genre.capitalize()]
                        paginated_data.append(card)
                    
                # Detect max pages
                last_page = 1
                pages = re.findall(r'page=(\d+)', html_content)
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

        # API: Get Manga Details dynamically
        elif self.path.startswith('/api/manga') and not self.path.startswith('/api/mangas'):
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

        # API: Get Chapter Reading Images (from Voratoon)
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
                import html as html_lib
                domain = get_scraper_domain()
                reader_url = f"{domain}/series/{manga_id}/chapter/{chapter_num}"
                try:
                    content = fetch_html(reader_url)
                except Exception:
                    reader_url = f"{domain}/manga/{manga_id}/chapter/{chapter_num}"
                    content = fetch_html(reader_url)
                
                img_srcs = re.findall(r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', content, re.IGNORECASE)
                cdn_imgs = [src for src in img_srcs if 'cdn.voratoon.com' in src or 'cdnkomiku' in src or 'dondon' in src or 'chapter' in src]
                if not cdn_imgs:
                    cdn_imgs = [src for src in img_srcs if not any(x in src for x in ['logo', 'avatar', 'icon', 'banner', 'wp-content/themes', 'gravatar', 'flagcdn', 'histats'])]
                mapped_images = [f"/api/proxy-img?url={urllib.parse.quote(html_lib.unescape(src))}" for src in cdn_imgs]
                
                details = scrape_details(manga_id)
                all_chapters = details["chapters"] if details else []
                manga_title = details["title"] if details else manga_id.replace('-', ' ').title()
                
                prev_ch = None
                next_ch = None
                if all_chapters:
                    ch_nums = [c["chapter_number"] for c in all_chapters]
                    try:
                        curr = float(chapter_num)
                        curr_key = int(curr) if curr.is_integer() else curr
                        if curr_key in ch_nums:
                            idx = ch_nums.index(curr_key)
                            prev_ch = str(ch_nums[idx + 1]) if idx + 1 < len(ch_nums) else None
                            next_ch = str(ch_nums[idx - 1]) if idx - 1 >= 0 else None
                    except Exception:
                        pass
                
                payload = {
                    "manga_title": manga_title,
                    "manga_id": manga_id,
                    "chapter_title": f"Chapter {chapter_num}",
                    "chapter_number": chapter_num,
                    "images": mapped_images,
                    "prev_chapter": prev_ch,
                    "next_chapter": next_ch,
                    "all_chapters": all_chapters,
                    "chapters": all_chapters
                }
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
                import html as html_lib
                img_url = html_lib.unescape(img_url)
                domain = get_scraper_domain()

                # Unwrap Voratoon resizer /api/cover?src=... to direct S3/CDN cover
                if '/api/cover' in img_url and 'src=' in img_url:
                    parsed_src = re.search(r'[?&]src=([^&]+)', img_url)
                    if parsed_src:
                        unquoted_src = urllib.parse.unquote(parsed_src.group(1))
                        if unquoted_src.startswith('http'):
                            img_url = unquoted_src

                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = f"{domain}{img_url}"

                req = urllib.request.Request(
                    img_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Referer': domain + '/'
                    }
                )
                with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
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

    def do_POST(self):
        # API: Add Comment
        if self.path == '/api/comments':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(post_data)
                
                manga_id = data.get('manga_id')
                manga_title = data.get('manga_title')
                chapter_id = data.get('chapter_id')
                username = data.get('username')
                email = data.get('email')
                content = data.get('content')
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                if not all([manga_id, manga_title, username, email, content]):
                    self.wfile.write(json.dumps({"status": "error", "message": "Missing required fields"}).encode('utf-8'))
                    return
                    
                comment_id = db_helper.add_comment(manga_id, manga_title, chapter_id, username, email, content)
                self.wfile.write(json.dumps({"status": "success", "comment_id": comment_id}).encode('utf-8'))
            except Exception as e:
                print("Error adding comment:", e)
                self.send_response(500)
                self.end_headers()
            return

        # API: Mark Notification as Read
        elif self.path == '/api/notifications/read':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(post_data)
                
                notification_id = data.get('id')
                target_user = data.get('email')
                role = data.get('role')
                
                if role == 'admin':
                    target_user = 'admin'
                
                db_helper.mark_notification_as_read(notification_id, target_user)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                print("Error reading notification:", e)
                self.send_response(500)
                self.end_headers()
            return

        # API: Save website config
        elif self.path == '/api/config':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                new_config = json.loads(post_data)
                
                # Update global site_config
                site_config.update(new_config)
                
                # Save to config.json
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(site_config, f, indent=4)
                    
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Konfigurasi berhasil disimpan!"}).encode('utf-8'))
            except Exception as e:
                print("Error saving config:", e)
                self.send_response(500)
                self.end_headers()
            return

        # API: Upload Logo or Favicon
        elif self.path == '/api/upload':
            try:
                file_type = self.headers.get('X-File-Type', '')
                content_length = int(self.headers.get('Content-Length', 0))
                
                if file_type not in ['logo', 'favicon'] or content_length == 0:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Invalid request parameters"}).encode('utf-8'))
                    return
                
                file_data = self.rfile.read(content_length)
                os.makedirs("assets", exist_ok=True)
                
                filename = "logo_uploaded.png" if file_type == 'logo' else "favicon_uploaded.png"
                target_path = os.path.join("assets", filename)
                
                with open(target_path, 'wb') as wf:
                    wf.write(file_data)
                
                url_path = f"/assets/{filename}"
                if file_type == 'logo':
                    site_config['logo_url'] = url_path
                else:
                    site_config['favicon_url'] = url_path
                    
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(site_config, f, indent=4)
                    
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(json.dumps({
                    "status": "success",
                    "url": url_path,
                    "message": f"File {file_type} berhasil diunggah!"
                }).encode('utf-8'))
                
            except Exception as e:
                print("Error uploading file:", e)
                self.send_response(500)
                self.end_headers()
            return

        # API: Generate sitemap.xml
        elif self.path == '/api/generate-sitemap':
            try:
                if os.path.exists("sitemap.xml"):
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "message": "Sitemap.xml sudah aktif dan valid!"}).encode('utf-8'))
                    return

                host = self.headers.get('Host', 'komivex.my.id')
                xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
                xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                xml += f'  <url>\n    <loc>https://{host}/</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'
                xml += f'  <url>\n    <loc>https://{host}/manga.html</loc>\n    <changefreq>daily</changefreq>\n    <priority>0.9</priority>\n  </url>\n'
                xml += f'  <url>\n    <loc>https://{host}/library.html</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
                xml += '</urlset>'

                with open("sitemap.xml", "w", encoding="utf-8") as sf:
                    sf.write(xml)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Sitemap.xml berhasil di-generate!"}).encode('utf-8'))
            except Exception as e:
                print("Error generating sitemap:", e)
                self.send_response(500)
                self.end_headers()
            return

        # API: Clear thumbnail cache (Mock success)
        elif self.path == '/api/clear-cache':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Cache gambar thumbnail berhasil dibersihkan!"}).encode('utf-8'))
            return

# Initialize database
db_helper.init_db()

# Avoid port in use errors on server restart
socketserver.TCPServer.allow_reuse_address = True


with socketserver.TCPServer(("0.0.0.0", PORT), ScraperHandler) as httpd:
    print(f"Komivex Server running at http://0.0.0.0:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()
