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
    "scraper_target_domain": "https://bacakomik.my",
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
    return site_config.get("scraper_target_domain", "https://bacakomik.my").rstrip('/')


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
    slug_match = re.search(r'href="https?://[^/]+/komik/([^/]+)/"', part)
    title_match = re.search(r'title="(?:Komik|Manga)\s*([^"]+)"', part)
    if not title_match:
        title_match = re.search(r'<h4>([^<]+)</h4>', part)

    cover_match = re.search(r'data-lazy-src="([^"]+)"', part)
    if not cover_match:
        cover_match = re.search(r'<noscript><img[^>]+src="([^"]+)"', part)

    cover = "/assets/manga_cover_1.jpg"
    if cover_match:
        cover = cover_match.group(1)
    else:
        img_srcs = re.findall(r'<img[^>]+src="([^"]+)"', part)
        for src in img_srcs:
            if not src.startswith('data:'):
                cover = src
                break

    type_match = re.search(r'class="typeflag\s*([^"]+)"', part)
    rating_match = re.search(r'<div class="rating">.*?<i>([\d\.]+)</i>', part, re.DOTALL)

    chapter_match = re.search(r'Chapter\s+([\d\.]+)', part)
    chapter_link_match = re.search(r'href="https?://[^"]+chapter-([\d\.]+)(?:/[^"]*)?"', part)
    ch_num = "1"
    if chapter_match:
        ch_num = chapter_match.group(1)
    elif chapter_link_match:
        ch_num = chapter_link_match.group(1)

    slug = slug_match.group(1).strip() if slug_match else ""
    title = title_match.group(1).strip() if title_match else slug.replace('-', ' ').title()
    cover_proxied = f"/api/proxy-img?url={urllib.parse.quote(cover)}" if cover and not cover.startswith('/') else cover
    manga_type = type_match.group(1).strip().capitalize() if type_match else "Manga"
    rating = rating_match.group(1) if rating_match else "7.0"

    return {
        "id": slug,
        "slug": slug,
        "title": title,
        "cover": cover_proxied,
        "type": manga_type,
        "rating": rating,
        "latest_chapter": ch_num,
    }


def scrape_details(slug):
    try:
        url = f"{get_scraper_domain()}/komik/{slug}/"
        content = fetch_html(url)

        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content)
        title = title_match.group(1).strip() if title_match else slug.replace('-', ' ').title()

        cover_match = re.search(r'<div class="thumb"[^>]*>.*?<img[^>]+src="([^"]+)"', content, re.DOTALL)
        if not cover_match:
            cover_match = re.search(r'<noscript><img[^>]+src="([^"]+)"', content)
        cover_raw = cover_match.group(1) if cover_match else ""
        cover = f"/api/proxy-img?url={urllib.parse.quote(cover_raw)}" if cover_raw and not cover_raw.startswith('/') else "/assets/manga_cover_1.jpg"

        synopsis_match = re.search(r'<div class="desc">.*?<p>(.*?)</p>', content, re.DOTALL)
        synopsis = re.sub(r'<[^>]+>', '', synopsis_match.group(1)) if synopsis_match else "Tidak ada sinopsis."

        type_match = re.search(r'Type.*?<a[^>]+>([^<]+)</a>', content, re.DOTALL)
        genre_matches = re.findall(r'class="genre-item"[^>]*>.*?<a[^>]+>([^<]+)</a>', content, re.DOTALL)
        if not genre_matches:
            genre_matches = re.findall(r'href="https?://[^/]+/genres/[^"]+">([^<]+)</a>', content)

        status_match = re.search(r'Status.*?<span[^>]*>([^<]+)</span>', content, re.DOTALL)

        # Chapters
        ch_matches = re.findall(r'href="https?://[^/]+/([^"]+-chapter-([\d\.]+)/)"', content)
        chapters = []
        seen = set()
        for ch_path, num_str in ch_matches:
            try:
                ch_num = float(num_str)
                ch_num_key = int(ch_num) if ch_num.is_integer() else ch_num
            except:
                continue
            if ch_num_key not in seen:
                seen.add(ch_num_key)
                chapters.append({
                    "chapter_number": ch_num_key,
                    "title": f"Chapter {ch_num_key}",
                    "url": ch_path
                })

        chapters.sort(key=lambda x: x["chapter_number"], reverse=True)

        return {
            "id": slug,
            "slug": slug,
            "title": title,
            "cover": cover,
            "synopsis": synopsis,
            "type": type_match.group(1).strip() if type_match else "Manga",
            "genres": genre_matches[:10],
            "status": status_match.group(1).strip() if status_match else "Ongoing",
            "chapters": chapters
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
            pop_start = content.find('mangapopuler')
            pop_end = content.find('chapterbaru')
            block = content[pop_start:pop_end] if pop_start != -1 and pop_end != -1 else content
            parts = block.split('<div class="animepost">')[1:]
            mangas = []
            for idx, p in enumerate(parts[:12]):
                card = parse_card(p)
                card["rank"] = idx + 1
                mangas.append(card)
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
            pop_end = content.find('chapterbaru')
            block = content[pop_end:] if pop_end != -1 else content
            parts = block.split('<div class="animepost">')[1:]
            times = ["2 mnt lalu","15 mnt lalu","45 mnt lalu","1 jam lalu","2 jam lalu","4 jam lalu","6 jam lalu","12 jam lalu","1 hari lalu"]
            mangas = []
            for idx, p in enumerate(parts[:9]):
                card = parse_card(p)
                card["updatedAt"] = times[idx] if idx < len(times) else "Baru saja"
                mangas.append(card)
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
            parts = content.split('<div class="animepost">')[1:]
            return json_response(start_response, [parse_card(p) for p in parts[:6]])
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
            query_parts = []
            if manga_type and manga_type != 'all':
                query_parts.append(f"type={manga_type.lower()}")
            if genre and genre != 'all':
                query_parts.append(f"genre={genre.lower()}")
            if sort:
                sort_map = {'rating': 'popular', 'popular': 'popular', 'alphabet': 'title'}
                query_parts.append(f"order={sort_map.get(sort, 'update')}")
            qs = "&".join(query_parts)
            url = f"{domain}/daftar-komik/page/{page}/"
            if qs:
                url += f"?{qs}"
            content = fetch_html(url)
            parts = content.split('<div class="animepost">')[1:]
            data = [parse_card(p) for p in parts]
            last_page = 1
            pag = re.search(r'<div class="pagination">([\s\S]*?)</div>', content)
            if pag:
                pages = re.findall(r'page/(\d+)/', pag.group(1))
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
            reader_url = f"{domain}/{manga_id}-chapter-{chapter_num}/"
            content = fetch_html(reader_url)
            start_pos = content.find('<div id="anjay_ini_id_kh">')
            if start_pos != -1:
                end_pos = content.find('<div class="navig"', start_pos)
                block = content[start_pos:end_pos] if end_pos != -1 else content[start_pos:start_pos+30000]
                noscript_imgs = re.findall(r'<noscript><img[^>]+src="([^"]+)"', block)
                images = [f"/api/proxy-img?url={urllib.parse.quote(src if not src.startswith('//') else 'https:'+src)}" for src in noscript_imgs]
            else:
                images = []
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
