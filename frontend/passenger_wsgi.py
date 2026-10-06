import sys
import os
import urllib.request
import urllib.parse
import re
import json
import mimetypes
import ssl

# ─────────────────────────────────────────────
# Path Setup (agar semua import dari folder ini)
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
try:
    os.chdir(BASE_DIR)
except Exception:
    pass

import db_helper
db_helper.init_db()


# ─────────────────────────────────────────────
# Konfigurasi situs (config.json)
# ─────────────────────────────────────────────
DEFAULT_CONFIG = {
    "logo_url": "/assets/logo.jpg",
    "favicon_url": "/assets/logo.jpg",
    "default_theme": "dark",
    "analytics_id": "",
    "meta_title": "Komivex - Baca Manga Terpopuler",
    "meta_description": "Platform baca komik (Manga, Manhua, Manhwa) terpopuler dan terlengkap gratis bahasa Indonesia.",
    "verification_code": "",
    "scraper_target_domain": "https://komikcast.app",
    "custom_ad_codes": {
        "head": "",
        "body": "",
        "header": "",
        "sidebar_1": "",
        "sidebar_2": "",
        "footer": ""
    }
}

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
site_config = DEFAULT_CONFIG.copy()
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            if "custom_ad_codes" in loaded:
                ads = loaded["custom_ad_codes"]
                if "sidebar" in ads and ads["sidebar"] and not ads.get("sidebar_1"):
                    ads["sidebar_1"] = ads["sidebar"]
            site_config.update(loaded)
    except Exception as e:
        print("Error loading config:", e)


def get_scraper_domain():
    return site_config.get("scraper_target_domain", "https://komikcast.info").rstrip('/')


# ─────────────────────────────────────────────
# SSL & HTTP Helpers
# ─────────────────────────────────────────────
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}


def fetch_html(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, context=ctx, timeout=15) as res:
        return res.read().decode('utf-8', errors='ignore')


# ─────────────────────────────────────────────
# Parsers
# ─────────────────────────────────────────────
def parse_card(part):
    """Parse a manga card from komikcast.app homepage HTML block."""
    slug_match = re.search(r'href="https?://[^/]+/(?:manga|komik|series)/([^/"]+)/?"', part)
    title_match = re.search(r'<h[234][^>]*>\s*([^<]{2,120})\s*</h[234]>', part)
    if not title_match:
        title_match = re.search(r'title="(?:Komik|Manga)?\s*([^"]{2,120})"', part)
    cover_match = re.search(r'data-src="(https?://[^"]+)"', part)
    if not cover_match:
        cover_match = re.search(r'data-lazy-src="(https?://[^"]+)"', part)
    if not cover_match:
        cover_match = re.search(r'<noscript><img[^>]+src="([^"]+)"', part)
    if not cover_match:
        cover_match = re.search(r'<img[^>]+src="(https?://[^"]+\.(?:jpg|png|webp)[^"]*)"', part)
    cover = "/assets/manga_cover_1.jpg"
    if cover_match:
        cover = cover_match.group(1)
    manga_type = "Manga"
    type_m = re.search(r'class="[^"]*\b(Manhwa|Manhua|Manga)\b[^"]*"', part, re.IGNORECASE)
    if not type_m:
        type_m = re.search(r'<span[^>]*>\s*(Manhwa|Manhua|Manga)\s*</span>', part, re.IGNORECASE)
    if type_m:
        t = type_m.group(1).strip()
        if t.lower() == 'manhwa': manga_type = 'Manhwa'
        elif t.lower() == 'manhua': manga_type = 'Manhua'
    rating = 0.0
    rating_m = re.search(r'aria-label="Rating\s*([\d\.]+)\s*dari\s*10"', part, re.IGNORECASE)
    if not rating_m:
        rating_m = re.search(r'class="system-rating"[\s\S]{0,120}<span[^>]*>([\d\.]+)</span>', part)
    if rating_m:
        try: rating = float(rating_m.group(1))
        except: pass
    ch_match = re.search(r'/chapter[-/]([\d\.]+)/?["\s]', part, re.IGNORECASE)
    latest_ch = 1
    if ch_match:
        try:
            v = float(ch_match.group(1))
            latest_ch = int(v) if v.is_integer() else v
        except: pass
    else:
        ch_txt = re.search(r'(?:Ch|Chapter)\.?\s*([\d\.]+)', part, re.IGNORECASE)
        if ch_txt:
            try:
                v = float(ch_txt.group(1))
                latest_ch = int(v) if v.is_integer() else v
            except: pass
    slug = slug_match.group(1) if slug_match else "unknown"
    title = re.sub(r'\s+', ' ', title_match.group(1)).strip() if title_match else slug.replace('-', ' ').title()
    if cover.startswith('/'*2): cover = 'https:' + cover
    if cover.startswith('http'):
        cover = f"/api/proxy-img?url={urllib.parse.quote(cover)}"
    return {
        "id": slug, "title": title, "type": manga_type,
        "rating": rating, "rank": 99, "latestChapter": latest_ch,
        "cover": cover, "author": "Unknown", "genres": ["Action"],
        "synopsis": "Sinopsis tidak tersedia.", "updatedAt": "Baru saja"
    }


def scrape_details(slug):
    try:
        domain = get_scraper_domain()
        try:
            url = f"{domain}/manga/{slug}/"
            content = fetch_html(url)
        except Exception:
            url = f"{domain}/komik/{slug}/"
            content = fetch_html(url)

                # Title
        title_m = re.search(r'<h1[^>]*>\s*([\s\S]{2,150}?)\s*</h1>', content)
        title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else slug.replace('-', ' ').title()
        title = re.sub(r'\s+', ' ', title)
        # Cover
        cover_match = re.search(r'<meta property="og:image"\s+content="([^"]+)"', content)
        if not cover_match:
            cover_match = re.search(r'data-src="(https?://[^"]+\.(?:jpg|png|webp)[^"]*)"', content)
        if not cover_match:
            cover_match = re.search(r'<img[^>]+src="(https?://[^"]+\.(?:jpg|png|webp)[^"]*)"', content)
        cover_raw = cover_match.group(1) if cover_match else None
        if cover_raw and cover_raw.startswith('//'): cover_raw = 'https:' + cover_raw
        cover = f"/api/proxy-img?url={urllib.parse.quote(cover_raw)}" if cover_raw and cover_raw.startswith('http') else "/assets/manga_cover_1.jpg"
        # Synopsis
        syn_m = re.search(r'<div[^>]+class="[^"]*(?:synopsis|sinopsis|description|entry-content)[^"]*"[^>]*>([\s\S]*?)</div>', content, re.IGNORECASE)
        if not syn_m:
            syn_m = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', content, re.IGNORECASE)
        synopsis = re.sub(r'<[^>]+>', '', syn_m.group(1)).strip() if syn_m else "Tidak ada sinopsis."
        synopsis = re.sub(r'\s+', ' ', synopsis)
        # Author
        author = "Unknown"
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
        # Genres
        genre_matches = re.findall(r'href="[^"]+/(?:genre|tag|genres)/[^/"]+/?"[^>]*>\s*([^<]{2,40})\s*</a>', content, re.IGNORECASE)
        if not genre_matches: genre_matches = ["Action"]
        genre_matches = list(dict.fromkeys(g.strip() for g in genre_matches if g.strip()))[:10]
        # Type
        manga_type = "Manga"
        type_m2 = re.search(r'(?:Type|Jenis|Tipe)[^<]{0,50}?(Manhwa|Manhua|Manga)', content, re.IGNORECASE)
        if type_m2:
            t = type_m2.group(1).strip()
            if t.lower() == 'manhwa': manga_type = 'Manhwa'
            elif t.lower() == 'manhua': manga_type = 'Manhua'
        # Rating
        rating = 7.5
        rating_m = re.search(r'aria-label="Rating\s*([\d\.]+)\s*dari\s*10"', content, re.IGNORECASE)
        if not rating_m:
            rating_m = re.search(r'class="system-rating"[\s\S]{0,120}<span[^>]*>([\d\.]+)</span>', content)
        if rating_m:
            try: rating = float(rating_m.group(1))
            except: pass
        # Status
        status = ""
        status_m = re.search(r'(?:Status)[^<]{0,30}(Ongoing|Completed|Tamat|Berlangsung|Hiatus)', content, re.IGNORECASE)
        if status_m: status = status_m.group(1).strip()
        # Release year
        year_m = re.search(r'(?:Released|Rilis|Tahun|Year)[^<]{0,30}(\d{4})', content, re.IGNORECASE)
        release_year = year_m.group(1) if year_m else ""
        # Chapters: fetch complete list via official JSON endpoint, fallback to HTML parsing
        chapters = []
        seen = set()
        try:
            ch_api_url = f"{domain}/api/manga/{slug}/chapters"
            ch_json_str = fetch_html(ch_api_url)
            ch_data = json.loads(ch_json_str)
            for item in ch_data.get("chapters", []):
                val = item.get("value")
                if val:
                    try:
                        ch_num = float(val)
                        key = int(ch_num) if ch_num.is_integer() else ch_num
                        if key not in seen:
                            seen.add(key)
                            title_lbl = item.get("title") or f"Chapter {key}"
                            chapters.append({"chapter_number": key, "title": title_lbl, "url": f"{slug}/chapter/{key}/"})
                    except: pass
        except Exception as e:
            print("Error fetching chapters API:", e)

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
            "genres": genre_matches, "status": status, "rating": rating,
            "rank": "", "author": author, "release_year": release_year,
            "latestChapter": latest_ch, "chapters": chapters
        }
    except Exception as e:
        print("Error scraping details:", e)
        return None


# ─────────────────────────────────────────────
# WSGI Response Helpers
# ─────────────────────────────────────────────
def json_response(start_response, data, status="200 OK"):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    start_response(status, [
        ('Content-Type', 'application/json; charset=utf-8'),
        ('Access-Control-Allow-Origin', '*'),
        ('Cache-Control', 'no-cache'),
    ])
    return [body]


def error_response(start_response, code, message):
    start_response(f'{code}', [('Content-Type', 'text/plain')])
    return [message.encode('utf-8')]


# ─────────────────────────────────────────────
# WSGI Application Entry Point
# ─────────────────────────────────────────────
def application(environ, start_response):
    method = environ.get('REQUEST_METHOD', 'GET').upper()
    path = environ.get('PATH_INFO', '/')
    query_string = environ.get('QUERY_STRING', '')

    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')

    params = urllib.parse.parse_qs(query_string)

    # ──────────────────────────
    # POST: Add Comment
    # ──────────────────────────
    if method == 'POST' and path == '/api/comments':
        try:
            length = int(environ.get('CONTENT_LENGTH', 0))
            body = environ['wsgi.input'].read(length)
            data = json.loads(body)
            
            manga_id = data.get('manga_id')
            manga_title = data.get('manga_title')
            chapter_id = data.get('chapter_id')
            username = data.get('username')
            email = data.get('email')
            content = data.get('content')
            
            if not all([manga_id, manga_title, username, email, content]):
                return json_response(start_response, {"status": "error", "message": "Missing required fields"}, "400 Bad Request")
                
            comment_id = db_helper.add_comment(manga_id, manga_title, chapter_id, username, email, content)
            return json_response(start_response, {"status": "success", "comment_id": comment_id})
        except Exception as e:
            return json_response(start_response, {"status": "error", "message": str(e)}, "500 Internal Server Error")

    # ──────────────────────────
    # POST: Mark Notification as Read
    # ──────────────────────────
    if method == 'POST' and path == '/api/notifications/read':
        try:
            length = int(environ.get('CONTENT_LENGTH', 0))
            body = environ['wsgi.input'].read(length)
            data = json.loads(body)
            
            notification_id = data.get('id')
            target_user = data.get('email')
            role = data.get('role')
            
            if role == 'admin':
                target_user = 'admin'
                
            db_helper.mark_notification_as_read(notification_id, target_user)
            return json_response(start_response, {"status": "success"})
        except Exception as e:
            return json_response(start_response, {"status": "error", "message": str(e)}, "500 Internal Server Error")

    # ──────────────────────────
    # GET: Get Comments
    # ──────────────────────────
    if method == 'GET' and path.startswith('/api/comments'):
        manga_id = params.get('manga', [''])[0]
        chapter_id = params.get('chapter', [None])[0]
        if not manga_id:
            return json_response(start_response, {"error": "Missing manga parameter"}, "400 Bad Request")
        comments = db_helper.get_comments(manga_id, chapter_id)
        return json_response(start_response, comments)

    # ──────────────────────────
    # GET: Get Notifications
    # ──────────────────────────
    if method == 'GET' and path.startswith('/api/notifications'):
        email = params.get('email', [''])[0]
        role = params.get('role', ['user'])[0]
        target_user = 'admin' if role == 'admin' else email
        if not target_user:
            return json_response(start_response, [])
        notifications = db_helper.get_notifications(target_user)
        return json_response(start_response, notifications)

    # ──────────────────────────
    # POST: Save Config
    # ──────────────────────────
    if method == 'POST' and path == '/api/config':
        try:
            length = int(environ.get('CONTENT_LENGTH', 0))
            body = environ['wsgi.input'].read(length)
            updates = json.loads(body)
            # Merge top-level and nested custom_ad_codes
            for key, val in updates.items():
                if key == "custom_ad_codes" and isinstance(val, dict):
                    if "custom_ad_codes" not in site_config:
                        site_config["custom_ad_codes"] = {}
                    site_config["custom_ad_codes"].update(val)
                else:
                    site_config[key] = val
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(site_config, f, ensure_ascii=False, indent=2)
            return json_response(start_response, {"status": "ok"})
        except Exception as e:
            return json_response(start_response, {"status": "error", "message": str(e)}, "500 Internal Server Error")

    # ──────────────────────────
    # POST: Upload logo / favicon
    # ──────────────────────────
    if method == 'POST' and path == '/api/upload':
        try:
            file_type = environ.get('HTTP_X_FILE_TYPE', '')
            if file_type not in ('logo', 'favicon'):
                return json_response(start_response, {"status": "error", "message": "Invalid file type"}, "400 Bad Request")
            length = int(environ.get('CONTENT_LENGTH', 0))
            file_data = environ['wsgi.input'].read(length)
            assets_dir = os.path.join(BASE_DIR, 'assets')
            os.makedirs(assets_dir, exist_ok=True)
            filename = f"{file_type}_uploaded.png"
            filepath = os.path.join(assets_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(file_data)
            url_path = f"/assets/{filename}"
            if file_type == 'logo':
                site_config['logo_url'] = url_path
            else:
                site_config['favicon_url'] = url_path
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(site_config, f, ensure_ascii=False, indent=2)
            return json_response(start_response, {"status": "ok", "url": url_path})
        except Exception as e:
            return json_response(start_response, {"status": "error", "message": str(e)}, "500 Internal Server Error")

    # ──────────────────────────
    # GET: /api/config
    # ──────────────────────────
    if method == 'GET' and path == '/api/config':
        return json_response(start_response, site_config)

    # ──────────────────────────
    # GET: /api/popular
    # ──────────────────────────
    if method == 'GET' and path == '/api/popular':
        try:
            domain = get_scraper_domain()
            content = fetch_html(f"{domain}/")
            # Split by article or animepost or bsx
            if '<article' in content:
                parts = [x for x in content.split('<article')[1:] if 'system-content-card' in x or '/manga/' in x or '/series/' in x]
            elif '<div class="animepost">' in content:
                parts = content.split('<div class="animepost">')[1:]
            elif '<div class="bsx">' in content:
                parts = content.split('<div class="bsx">')[1:]
            else:
                parts = [x for x in content.split('<article')[1:]]
            mangas = []
            seen = set()
            for x in parts:
                card = parse_card(x)
                if card["id"] != "unknown" and card["id"] not in seen:
                    seen.add(card["id"])
                    card["rank"] = len(mangas) + 1
                    mangas.append(card)
                if len(mangas) >= 12:
                    break
            return json_response(start_response, mangas)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return json_response(start_response, {"error": str(e)}, "500 Internal Server Error")

    # ──────────────────────────
    # GET: /api/updates
    # ──────────────────────────
    if method == 'GET' and path == '/api/updates':
        try:
            domain = get_scraper_domain()
            content = fetch_html(f"{domain}/")
            if '<article' in content:
                parts = [x for x in content.split('<article')[1:] if 'system-content-card' in x or '/manga/' in x or '/series/' in x]
            elif '<div class="animepost">' in content:
                parts = content.split('<div class="animepost">')[1:]
            elif '<div class="bsx">' in content:
                parts = content.split('<div class="bsx">')[1:]
            else:
                parts = [x for x in content.split('<article')[1:]]
            times = ["2 mnt lalu","15 mnt lalu","45 mnt lalu","1 jam lalu","2 jam lalu","4 jam lalu","6 jam lalu","12 jam lalu","1 hari lalu"]
            mangas = []
            seen = set()
            for x in parts:
                card = parse_card(x)
                if card["id"] != "unknown" and card["id"] not in seen:
                    seen.add(card["id"])
                    idx = len(mangas)
                    card["updatedAt"] = times[idx] if idx < len(times) else "Baru saja"
                    mangas.append(card)
                if len(mangas) >= 9:
                    break
            return json_response(start_response, mangas)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return json_response(start_response, {"error": str(e)}, "500 Internal Server Error")

    # ──────────────────────────
    # GET: /api/search
    # ──────────────────────────
    if method == 'GET' and path.startswith('/api/search'):
        query = params.get('q', [''])[0].strip()
        if not query:
            return json_response(start_response, [])
        try:
            domain = get_scraper_domain()
            content = fetch_html(f"{domain}/?s={urllib.parse.quote(query)}")
            parts = [x for x in content.split('<article')[1:] if '/manga/' in x]
            results = []
            seen = set()
            for x in parts:
                c = parse_card(x)
                if c["id"] != "unknown" and c["id"] not in seen:
                    seen.add(c["id"])
                    results.append(c)
                if len(results) >= 6:
                    break
            return json_response(start_response, results)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return json_response(start_response, {"error": str(e)}, "500 Internal Server Error")

    # ──────────────────────────
    # GET: /api/mangas
    # ──────────────────────────
    if method == 'GET' and path.startswith('/api/mangas'):
        page = int(params.get('page', ['1'])[0])
        manga_type = params.get('type', [''])[0]
        genre = params.get('genre', [''])[0]
        sort = params.get('sort', [''])[0]
        try:
            domain = get_scraper_domain()
            # Route to komikcast.app catalog (/manga/?page=N)
            query_parts_cat = []
            if page > 1:
                query_parts_cat.append(f"page={page}")
            if manga_type and manga_type != 'all':
                query_parts_cat.append(f"type={manga_type.lower()}")
            if sort:
                sort_map = {'rating': 'rating', 'popular': 'popular', 'alphabet': 'title'}
                query_parts_cat.append(f"order={sort_map.get(sort, 'update')}")
            qs_cat = "&".join(query_parts_cat)
            url = f"{domain}/manga/" + (f"?{qs_cat}" if qs_cat else "")

            content = fetch_html(url)
            parts = [x for x in content.split('<article')[1:] if 'system-content-card' in x or '/manga/' in x]
            data = [parse_card(p) for p in parts]
            last_page = 1
            pages = re.findall(r'href="[^"]*page=(\d+)[^"]*"', content)
            if pages:
                last_page = max(map(int, pages))
            return json_response(start_response, {
                "current_page": page,
                "last_page": last_page,
                "total": last_page * len(data) if data else 0,
                "data": data
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return json_response(start_response, {"error": str(e)}, "500 Internal Server Error")

    # ──────────────────────────
    # GET: /api/manga?id=<slug>
    # ──────────────────────────
    if method == 'GET' and path.startswith('/api/manga') and not path.startswith('/api/mangas'):
        slug = params.get('id', [''])[0]
        if not slug:
            return json_response(start_response, {"error": "Missing id"}, "400 Bad Request")
        details = scrape_details(slug)
        if details:
            return json_response(start_response, details)
        return json_response(start_response, {"error": "Not found"}, "404 Not Found")

    # ──────────────────────────
    # GET: /api/read
    # ──────────────────────────
    if method == 'GET' and path.startswith('/api/read'):
        manga_id = params.get('manga', [''])[0]
        chapter_num = params.get('chapter', ['1'])[0]
        if not manga_id:
            return json_response(start_response, {"error": "Missing manga"}, "400 Bad Request")
        try:
            domain = get_scraper_domain()
            reader_url = f"{domain}/manga/{manga_id}/chapter/{chapter_num}"
            try:
                content = fetch_html(reader_url)
            except:
                reader_url = f"{domain}/manga/{manga_id}/chapter/{chapter_num}.00"
                content = fetch_html(reader_url)
            
            # Find all reader images
            img_srcs = re.findall(r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|webp))', content, re.IGNORECASE)
            cdn_imgs = [src for src in img_srcs if 'cdnkomiku' in src or 'dondon' in src or 'chapter' in src]
            if not cdn_imgs:
                cdn_imgs = [src for src in img_srcs if not any(x in src for x in ['logo', 'avatar', 'icon', 'banner', 'wp-content/themes', 'gravatar'])]
            images = [f"/api/proxy-img?url={urllib.parse.quote(src)}" for src in cdn_imgs]
            details = scrape_details(manga_id)
            all_chapters = details["chapters"] if details else []
            manga_title = details["title"] if details else manga_id.replace('-', ' ').title()
            payload = {
                "manga_title": manga_title,
                "manga_id": manga_id,
                "chapter_title": f"Chapter {chapter_num}",
                "chapter_number": chapter_num,
                "images": images,
                "prev_chapter": None,
                "next_chapter": None,
                "chapters": all_chapters
            }
            if all_chapters:
                ch_nums = [c["chapter_number"] for c in all_chapters]
                try:
                    curr = float(chapter_num)
                    curr_key = int(curr) if curr.is_integer() else curr
                    if curr_key in ch_nums:
                        idx = ch_nums.index(curr_key)
                        payload["prev_chapter"] = str(ch_nums[idx + 1]) if idx + 1 < len(ch_nums) else None
                        payload["next_chapter"] = str(ch_nums[idx - 1]) if idx - 1 >= 0 else None
                except Exception:
                    pass
            return json_response(start_response, payload)
        except Exception as e:
            return json_response(start_response, {"error": str(e)}, "500 Internal Server Error")

    # ──────────────────────────
    # GET: /api/proxy-img
    # ──────────────────────────
    if method == 'GET' and path.startswith('/api/proxy-img'):
        img_url = params.get('url', [''])[0]
        if not img_url:
            return error_response(start_response, '400 Bad Request', 'Missing url')
        try:
            req = urllib.request.Request(img_url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': get_scraper_domain() + '/'
            })
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                ctype = resp.headers.get('Content-Type', 'image/jpeg')
                start_response('200 OK', [
                    ('Content-Type', ctype),
                    ('Cache-Control', 'public, max-age=86400'),
                    ('Access-Control-Allow-Origin', '*'),
                ])
                return [resp.read()]
        except Exception as e:
            return error_response(start_response, '500 Internal Server Error', str(e))

    # ──────────────────────────
    # GET: /sitemap.xml
    # ──────────────────────────
    if method == 'GET' and path == '/sitemap.xml':
        try:
            host = environ.get('HTTP_HOST', 'komivex.my.id')
            domain = get_scraper_domain()
            html_content = fetch_html(domain)
            slugs = list(set(re.findall(r'href="https?://[^/]+/komik/([^/]+)/"', html_content)))[:30]
            xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            xml += f'  <url><loc>https://{host}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>\n'
            xml += f'  <url><loc>https://{host}/#library</loc><changefreq>daily</changefreq><priority>0.8</priority></url>\n'
            xml += f'  <url><loc>https://{host}/#manga</loc><changefreq>daily</changefreq><priority>0.8</priority></url>\n'
            for slug in slugs:
                xml += f'  <url><loc>https://{host}/#manga-{slug}</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>\n'
            xml += '</urlset>'
            start_response('200 OK', [
                ('Content-Type', 'application/xml'),
                ('Access-Control-Allow-Origin', '*'),
            ])
            return [xml.encode('utf-8')]
        except Exception as e:
            return error_response(start_response, '500 Internal Server Error', str(e))

    # ──────────────────────────
    # POST: Generate Sitemap
    # ──────────────────────────
    if method == 'POST' and path == '/api/generate-sitemap':
        try:
            domain = get_scraper_domain()
            host = environ.get('HTTP_HOST', 'localhost')
            html_content = fetch_html(domain)
            slugs = list(set(re.findall(r'href="https?://[^/]+/komik/([^/]+)/"', html_content)))[:30]
            xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            xml += f'  <url><loc>https://{host}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>\n'
            for slug in slugs:
                xml += f'  <url><loc>https://{host}/#manga-{slug}</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>\n'
            xml += '</urlset>'
            with open(os.path.join(BASE_DIR, "sitemap.xml"), "w", encoding="utf-8") as sf:
                sf.write(xml)
            return json_response(start_response, {"status": "success", "message": "Sitemap.xml berhasil di-generate!"})
        except Exception as e:
            return json_response(start_response, {"status": "error", "message": str(e)}, "500 Internal Server Error")

    # ──────────────────────────
    # POST: Clear Cache (mock)
    # ──────────────────────────
    if method == 'POST' and path == '/api/clear-cache':
        return json_response(start_response, {"status": "success", "message": "Cache berhasil dibersihkan!"})

    # ──────────────────────────
    # Static Files & index.html
    # ──────────────────────────
    local_path = path.lstrip('/')
    if not local_path:
        local_path = 'index.html'

    full_path = os.path.join(BASE_DIR, local_path)
    if os.path.isfile(full_path):
        ctype, _ = mimetypes.guess_type(full_path)
        if not ctype:
            ctype = 'text/html' if full_path.endswith('.html') else 'application/octet-stream'
        # Force correct MIME types
        if full_path.endswith('.css'):
            ctype = 'text/css'
        elif full_path.endswith('.js'):
            ctype = 'application/javascript'
        start_response('200 OK', [
            ('Content-Type', ctype),
            ('Cache-Control', 'public, max-age=3600'),
        ])
        with open(full_path, 'rb') as f:
            return [f.read()]

    start_response('404 Not Found', [('Content-Type', 'text/html')])
    return [b'<h1>404 Not Found</h1>']
