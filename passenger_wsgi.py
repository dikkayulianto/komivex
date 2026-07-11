import sys
import os
import urllib.parse
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import functions from server.py
from server import fetch_html, parse_card, scrape_details, ctx

def application(environ, start_response):
    path = environ.get('PATH_INFO', '')
    query_string = environ.get('QUERY_STRING', '')
    
    # Normalize path suffix
    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')
        
    # 1. API: Get Popular Manga
    if path == '/api/popular':
        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*')
        ])
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
            return [json.dumps(mangas).encode('utf-8')]
        except Exception as e:
            return [json.dumps([]).encode('utf-8')]

    # 2. API: Get Latest Manga Updates
    elif path == '/api/updates':
        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*')
        ])
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
            return [json.dumps(mangas).encode('utf-8')]
        except Exception as e:
            return [json.dumps([]).encode('utf-8')]

    # 3. API: Search suggestions
    elif path.startswith('/api/search'):
        params = urllib.parse.parse_qs(query_string)
        query = params.get('q', [''])[0].strip()
        
        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*')
        ])
        if not query:
            return [json.dumps([]).encode('utf-8')]
            
        try:
            html_content = fetch_html(f"https://bacakomik.my/?s={urllib.parse.quote(query)}")
            parts = html_content.split('<div class="animepost">')[1:]
            results = []
            for p in parts[:6]:
                results.append(parse_card(p))
            return [json.dumps(results).encode('utf-8')]
        except Exception as e:
            return [json.dumps([]).encode('utf-8')]

    # 4. API: Get Paginated Manga Directory
    elif path.startswith('/api/mangas'):
        params = urllib.parse.parse_qs(query_string)
        page = int(params.get('page', ['1'])[0])
        manga_type = params.get('type', [''])[0]
        genre = params.get('genre', [''])[0]
        sort = params.get('sort', [''])[0]
        
        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*')
        ])
        try:
            import re
            query_parts = []
            if manga_type and manga_type != 'all':
                query_parts.append(f"type={manga_type.lower()}")
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
            return [json.dumps(payload).encode('utf-8')]
        except Exception as e:
            return [json.dumps({"current_page":1,"last_page":1,"total":0,"data":[]}).encode('utf-8')]

    # 5. API: Get Manga Details
    elif path.startswith('/api/manga'):
        params = urllib.parse.parse_qs(query_string)
        slug = params.get('id', [''])[0]
        
        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*')
        ])
        if not slug:
            return [json.dumps({"error": "Missing id parameter"}).encode('utf-8')]
            
        details = scrape_details(slug)
        if details:
            return [json.dumps(details).encode('utf-8')]
        else:
            return [json.dumps({"error": "Failed to scrape details"}).encode('utf-8')]

    # 6. API: Get Chapter Reading Images
    elif path.startswith('/api/read'):
        params = urllib.parse.parse_qs(query_string)
        manga_id = params.get('manga', [''])[0]
        chapter_num = params.get('chapter', ['1'])[0]
        
        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*')
        ])
        if not manga_id:
            return [json.dumps({"error": "Missing manga parameter"}).encode('utf-8')]
            
        try:
            import re
            reader_url = f"https://bacakomik.my/{manga_id}-chapter-{chapter_num}/"
            content = fetch_html(reader_url)
            
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
            
            details = scrape_details(manga_id)
            all_chapters = details["chapters"] if details else []
            manga_title = details["title"] if details else manga_id.replace('-', ' ').title()
            
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
            
            return [json.dumps(payload).encode('utf-8')]
        except Exception as e:
            return [json.dumps({"error": str(e)}).encode('utf-8')]

    # 7. API: Proxy Image
    elif path.startswith('/api/proxy-img'):
        import urllib.request
        params = urllib.parse.parse_qs(query_string)
        img_url = params.get('url', [''])[0]
        
        if not img_url:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b'Missing url parameter']
            
        try:
            req = urllib.request.Request(
                img_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                    'Referer': 'https://bacakomik.my/'
                }
            )
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                content_type = response.headers.get('Content-Type', 'image/jpeg')
                start_response('200 OK', [
                    ('Content-Type', content_type),
                    ('Cache-Control', 'public, max-age=86400')
                ])
                return [response.read()]
        except Exception as e:
            start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
            return [str(e).encode('utf-8')]

    # 8. Serve Static Files
    else:
        # If accessing the root, serve index.html
        local_path = path.lstrip('/')
        if not local_path or local_path == '':
            local_path = 'index.html'
            
        if os.path.exists(local_path) and os.path.isfile(local_path):
            import mimetypes
            content_type, _ = mimetypes.guess_type(local_path)
            if not content_type:
                content_type = 'text/html' if local_path.endswith('.html') else 'application/octet-stream'
                
            start_response('200 OK', [('Content-Type', content_type)])
            with open(local_path, 'rb') as f:
                return [f.read()]
        else:
            start_response('404 Not Found', [('Content-Type', 'text/html')])
            return [b'<h1>404 Not Found</h1>']
