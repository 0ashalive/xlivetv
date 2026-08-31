from http.server import BaseHTTPRequestHandler
import urllib.parse
import urllib.request

# ==============================================================================
# 1. PLAYLIST MAPPING (id -> source URL)
# ==============================================================================
PLAYLISTS = {
    # Original Playlists
    "jio": "https://raw.githubusercontent.com/0ashalive/xlivetv/refs/heads/main/jbonio.m3u",
    "bdix": "https://raw.githubusercontent.com/streamifytv/abbas/refs/heads/main/bd.m3u",
    "jago": "https://m3u-tvb.pages.dev/Jjago.br.m3u8",
    "bdix2": "https://github.com/abusaeeidx/Mrgify-BDIX-IPTV/raw/main/playlist.m3u",
    
    # Additional Category Playlists
    "bd_all": "https://raw.githubusercontent.com/m3u8playlist/bangladesh-iptv/main/bd.m3u",
    "sports": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/sports.m3u",
    "news": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/news.m3u",
    "movies": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/movies.m3u",
    "music": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/music.m3u",
    "entertainment": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/entertainment.m3u",
    "animation": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/animation.m3u",
}

DEFAULT_PLAYLIST_ID = "jio"
TELEGRAM_URL = "https://t.me/bdtvlive"

# User-Agent Verification Lists
BROWSER_USER_AGENTS = ["mozilla", "chrome", "safari", "edge", "opera", "firefox"]
MEDIA_PLAYER_AGENTS = ["okhttp", "kodi", "iptv", "tivimate", "exoplayer", "vlc", "mxplayer"]

# ==============================================================================
# 2. AUTOMATIC REMOVAL CONFIGURATION
# ==============================================================================

# A. 특정 লিঙ্ক বা ডোমেইন রিমুভ করার তালিকা (Add extra links/domains here)
REMOVE_URLS = [
    "https://playztv.pages.dev/promo/master.m3u8", # Target Promo Stream
                        # Domain match
    "1000398131.png",                              # Promo Logo
    # আরও লিঙ্ক বাদ দিতে নিচে কমা (,) দিয়ে যুক্ত করুন:
    # "https://example.com/ad/stream.m3u8",
    # "another-ad-domain.com",
]

# B. চ্যানেল টাইটেল বা মেটাডেটার কি-ওয়ার্ড রিমুভ করার তালিকা
REMOVE_KEYWORDS = [
    "welcome to playz tv",
    "playz tv",
    "promo",
    "advertisement",
    "join telegram",
    "subscribe",
    "new app",
    "download app",
    # আরও কি-ওয়ার্ড বাদ দিতে নিচে কমা (,) দিয়ে যুক্ত করুন:
    # "ad_channel_name",
]


# ==============================================================================
# 3. M3U CLEANING & LINK DEDUPLICATION ENGINE
# ==============================================================================
def clean_m3u_content(raw_text: str) -> str:
    """
    Parses raw M3U playlist data, filters out specified promo ads/links,
    and automatically strips duplicate m3u8 stream URLs.
    """
    lines = raw_text.splitlines()
    cleaned_lines = []
    
    # Track unique stream URLs to avoid double entries
    seen_stream_urls = set()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect start of entry block (#EXTINF)
        if line.startswith("#EXTINF"):
            block = [lines[i]]
            i += 1
            
            stream_url = ""
            # Capture full channel block (tags, headers, and stream URL)
            while i < len(lines) and not lines[i].strip().startswith("#EXTINF"):
                block.append(lines[i])
                curr_line = lines[i].strip()
                if not curr_line.startswith("#") and curr_line != "":
                    stream_url = curr_line
                    break
                i += 1
            
            block_text = "\n".join(block)
            block_text_lower = block_text.lower()
            
            should_remove = False

            # Check 1: Target Stream/Logo URL or Domain Removal
            if any(url.lower() in block_text_lower for url in REMOVE_URLS if url.strip()):
                should_remove = True

            # Check 2: Target Keyword Removal
            if not should_remove:
                if any(kw.lower() in block_text_lower for kw in REMOVE_KEYWORDS if kw.strip()):
                    should_remove = True

            # Check 3: Strict m3u8 Link Deduplication
            if not should_remove and stream_url:
                normalized_url = stream_url.lower()
                if normalized_url in seen_stream_urls:
                    should_remove = True
                else:
                    seen_stream_urls.add(normalized_url)

            # Retain block if clean and unique
            if not should_remove:
                cleaned_lines.extend(block)
            continue
        
        # Standalone stream links or comments handling
        else:
            if line:
                if not line.startswith("#"):
                    normalized_url = line.lower()
                    if normalized_url not in seen_stream_urls:
                        seen_stream_urls.add(normalized_url)
                        cleaned_lines.append(lines[i])
                else:
                    cleaned_lines.append(lines[i])
            i += 1

    return "\n".join(cleaned_lines)


# ==============================================================================
# 4. HTTP REQUEST HANDLER
# ==============================================================================
class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        user_agent = (self.headers.get("User-Agent") or "").lower()

        is_media_player = any(player in user_agent for player in MEDIA_PLAYER_AGENTS)
        is_browser = any(browser in user_agent for browser in BROWSER_USER_AGENTS)

        # 1. Redirect standard web browsers to Telegram
        if is_browser and not is_media_player:
            self.send_response(302)
            self.send_header("Location", TELEGRAM_URL)
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            return

        # 2. Extract ?id= query parameter
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        playlist_id = query_params.get("id", [DEFAULT_PLAYLIST_ID])[0].lower()

        # Handle missing key in PLAYLISTS dictionary
        if playlist_id not in PLAYLISTS:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"#ERROR: Playlist key '{playlist_id}' not found.".encode("utf-8"))
            return

        target_url = PLAYLISTS[playlist_id]

        # 3. Request raw M3U playlist file content
        try:
            req = urllib.request.Request(
                target_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
                },
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                m3u_content_raw = response.read().decode("utf-8", errors="ignore")

            # Clean promo links and remove duplicate channels
            m3u_content_cleaned = clean_m3u_content(m3u_content_raw)

            # 4. Output cleaned M3U data directly to media player
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(m3u_content_cleaned.encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            err_msg = f"#EXTM3U\n#ERROR: Failed to fetch target playlist: {str(e)}"
            self.wfile.write(err_msg.encode("utf-8"))
