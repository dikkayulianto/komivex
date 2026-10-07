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
    domain = site_config.get("scraper_target_domain", "").strip().rstrip('/')
    if not domain or any(x in domain for x in ["bacakomik", "shinigami", "komikcast.info"]):
        domain = "https://v6.voratoon.com"
    return domain


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
            try:
                content = fetch_html(f"{domain}/ranking")
            except Exception:
                content = fetch_html(f"{domain}/browse?order=popular")
            if '<a class="comic-row"' in content:
                parts = content.split('<a class="comic-row')[1:]
            elif '<article' in content:
                parts = [x for x in content.split('<article')[1:] if '/series/' in x or '/manga/' in x]
            else:
                parts = [x for x in content.split('<article')[1:]]
            mangas = []
            seen = set()
            for x in parts:
                card = parse_card(x)
                if card and card["id"] not in seen:
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
            try:
                content = fetch_html(f"{domain}/updates")
            except Exception:
                content = fetch_html(f"{domain}/")
            parts = [x for x in content.split('<article')[1:] if '/series/' in x or '/manga/' in x]
            times = ["2 mnt lalu","15 mnt lalu","45 mnt lalu","1 jam lalu","2 jam lalu","4 jam lalu","6 jam lalu","12 jam lalu","1 hari lalu"]
            mangas = []
            seen = set()
            for x in parts:
                card = parse_card(x)
                if card and card["id"] not in seen:
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
            try:
                content = fetch_html(f"{domain}/browse?q={urllib.parse.quote(query)}")
            except Exception:
                content = fetch_html(f"{domain}/?s={urllib.parse.quote(query)}")
            parts = [x for x in content.split('<article')[1:] if '/series/' in x or '/manga/' in x]
            results = []
            seen = set()
            for x in parts:
                c = parse_card(x)
                if c and c["id"] not in seen:
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
            query_parts_cat = []
            if page > 1:
                query_parts_cat.append(f"page={page}")
            if manga_type and manga_type.lower() not in ('all', 'semua'):
                query_parts_cat.append(f"format={manga_type.lower()}")
            if genre and genre.lower() not in ('all', 'semua'):
                query_parts_cat.append(f"genre={urllib.parse.quote(genre)}")
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
                query_parts_cat.append(f"sort={sort_map.get(sort.lower(), 'rating')}")
            qs_cat = "&".join(query_parts_cat)
            url = f"{domain}/browse" + (f"?{qs_cat}" if qs_cat else "")
            try:
                content = fetch_html(url)
            except Exception:
                url = f"{domain}/manga/" + (f"?{qs_cat}" if qs_cat else "")
                content = fetch_html(url)
            parts = [x for x in content.split('<article')[1:] if '/series/' in x or '/manga/' in x or 'card' in x]
            data = []
            seen = set()
            for p in parts:
                c = parse_card(p)
                if c and c["id"] not in seen:
                    seen.add(c["id"])
                    if manga_type and manga_type.lower() not in ('all', 'semua'):
                        c["type"] = manga_type.capitalize()
                    if genre and genre.lower() not in ('all', 'semua'):
                        c["genres"] = [genre.capitalize()]
                    data.append(c)
            last_page = 1
            pages = re.findall(r'page=(\d+)', content)
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
            import html as html_lib
            domain = get_scraper_domain()
            reader_url = f"{domain}/series/{manga_id}/chapter/{chapter_num}"
            try:
                content = fetch_html(reader_url)
            except Exception:
                reader_url = f"{domain}/manga/{manga_id}/chapter/{chapter_num}"
                content = fetch_html(reader_url)

            # Find all reader images
            img_srcs = re.findall(r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', content, re.IGNORECASE)
            cdn_imgs = [src for src in img_srcs if 'cdn.voratoon.com' in src or 'cdnkomiku' in src or 'dondon' in src or 'chapter' in src]
            if not cdn_imgs:
                cdn_imgs = [src for src in img_srcs if not any(x in src for x in ['logo', 'avatar', 'icon', 'banner', 'wp-content/themes', 'gravatar', 'flagcdn', 'histats'])]
            images = [f"/api/proxy-img?url={urllib.parse.quote(html_lib.unescape(src))}" for src in cdn_imgs]
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
                "images": images,
                "prev_chapter": prev_ch,
                "next_chapter": next_ch,
                "all_chapters": all_chapters,
                "chapters": all_chapters
            }
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

            req = urllib.request.Request(img_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': domain + '/'
            })
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
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
    # GET: /robots.txt
    # ──────────────────────────
    if method == 'GET' and path == '/robots.txt':
        robots_file = os.path.join(BASE_DIR, "robots.txt")
        if os.path.exists(robots_file):
            with open(robots_file, "r", encoding="utf-8") as rf:
                content = rf.read()
        else:
            content = "User-agent: *\nAllow: /\nDisallow: /admin.html\nDisallow: /api/admin/\nDisallow: /api/comments/delete\n\nSitemap: https://komivex.my.id/sitemap.xml\n"
        start_response('200 OK', [
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Access-Control-Allow-Origin', '*'),
        ])
        return [content.encode('utf-8')]

    # ──────────────────────────
    # GET: /sitemap.xml
    # ──────────────────────────
    if method == 'GET' and path == '/sitemap.xml':
        sitemap_file = os.path.join(BASE_DIR, "sitemap.xml")
        if os.path.exists(sitemap_file):
            with open(sitemap_file, "r", encoding="utf-8") as sf:
                xml_content = sf.read()
            start_response('200 OK', [
                ('Content-Type', 'application/xml; charset=utf-8'),
                ('Access-Control-Allow-Origin', '*'),
            ])
            return [xml_content.encode('utf-8')]
        try:
            host = environ.get('HTTP_HOST', 'komivex.my.id')
            xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            xml += f'  <url><loc>https://{host}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>\n'
            xml += f'  <url><loc>https://{host}/manga.html</loc><changefreq>daily</changefreq><priority>0.9</priority></url>\n'
            xml += f'  <url><loc>https://{host}/library.html</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>\n'
            xml += '</urlset>'
            start_response('200 OK', [
                ('Content-Type', 'application/xml; charset=utf-8'),
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
            host = environ.get('HTTP_HOST', 'komivex.my.id')
            sitemap_file = os.path.join(BASE_DIR, "sitemap.xml")
            if os.path.exists(sitemap_file):
                return json_response(start_response, {"status": "success", "message": "Sitemap.xml sudah aktif dan valid!"})
            xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            xml += f'  <url><loc>https://{host}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>\n'
            xml += f'  <url><loc>https://{host}/manga.html</loc><changefreq>daily</changefreq><priority>0.9</priority></url>\n'
            xml += f'  <url><loc>https://{host}/library.html</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>\n'
            xml += '</urlset>'
            with open(sitemap_file, "w", encoding="utf-8") as sf:
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
