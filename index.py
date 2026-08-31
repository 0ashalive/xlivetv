from http.server import BaseHTTPRequestHandler
import urllib.parse
import urllib.request

# ==============================================================================
# 1. PLAYLIST MAPPING (id -> source URL)
# ==============================================================================
PLAYLISTS = {
    "jio": "https://raw.githubusercontent.com/0ashalive/xlivetv/refs/heads/main/jbonio.m3u",
    "bdix": "https://raw.githubusercontent.com/streamifytv/abbas/refs/heads/main/bd.m3u",
    "jago": "https://m3u-tvb.pages.dev/Jjago.br.m3u8",
    "bdix2": "https://github.com/abusaeeidx/Mrgify-BDIX-IPTV/raw/main/playlist.m3u",
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

BROWSER_USER_AGENTS = ["mozilla", "chrome", "safari", "edge", "opera", "firefox"]
MEDIA_PLAYER_AGENTS = ["okhttp", "kodi", "iptv", "tivimate", "exoplayer", "vlc", "mxplayer"]

# ==============================================================================
# 2. AUTOMATIC REMOVAL CONFIGURATION
# ==============================================================================

# Keywords in tvg-name, group-title, titles, or logos to filter out
REMOVE_KEYWORDS = [
    # Specific targeted block text
    "welcome to playz tv",
    "playz tv",
    "welcome to playz tv | new app",
    "blogger.googleusercontent.com/img/b/r29vzgxl/avvxsegynikyw9puz1okx5bgzlaswgvsu p0e7hx9fxvtmjmhxhu8x0tpucgsplbzgm8pcyrjjh0p2_dtc1-wzp4mmuu4sknozghgpcwwdbyooa4jtyhpr7ydnj-uk-bc56imsk2h3wzj-szszik0dtpyabcfr2_zjc2_c86w1pv7odfbt_y-hyjs62g-3zcjkpgd",
    
    # Generic advertising and promo keywords
    "promo",
    "advertisement",
    "join telegram",
    "subscribe",
    "new app",
    "download app",

    # Place additional title or metadata keywords to remove here:
    # "another_ad_keyword",
]

# Specific stream URLs, logo URLs, or host domains to filter out completely
REMOVE_URLS = [
    # Target stream link
    "https://playztv.pages.dev/promo/master.m3u8",
    "playztv.pages.dev",
    
    # Target logo URL pattern
    "1000398131.png",

    # Place additional stream URLs or domain paths to remove here:
    # "https://example.com/promo.m3u8",
]


# ==============================================================================
# 3. M3U CLEANING ENGINE
# ==============================================================================
def clean_m3u_content(raw_text: str) -> str:
    """
    Parses raw M3U playlist data line-by-line into discrete channel blocks.
    If a block matches any REMOVE_KEYWORDS or REMOVE_URLS, it is dropped.
    """
    lines = raw_text.splitlines()
    cleaned_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect start of entry block
        if line.startswith("#EXTINF"):
            block = [lines[i]]
            i += 1
            # Collect full block (metadata tags + stream link)
            while i < len(lines) and not lines[i].strip().startswith("#EXTINF"):
                block.append(lines[i])
                if not lines[i].strip().startswith("#") and lines[i].strip() != "":
                    break
                i += 1
            
            block_text = "\n".join(block)
            block_text_lower = block_text.lower()
            
            should_remove = False

            # Check 1: Match keywords in full block text (includes metadata & logo)
            if any(kw.lower() in block_text_lower for kw in REMOVE_KEYWORDS if kw.strip()):
                should_remove = True

            # Check 2: Match stream/logo URLs or hostnames
            if not should_remove:
                if any(url.lower() in block_text_lower for url in REMOVE_URLS if url.strip()):
                    should_remove = True

            # Retain block if clean
            if not should_remove:
                cleaned_lines.extend(block)
            continue
        
        else:
            if line:
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

        if is_browser and not is_media_player:
            self.send_response(302)
            self.send_header("Location", TELEGRAM_URL)
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            return

        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        playlist_id = query_params.get("id", [DEFAULT_PLAYLIST_ID])[0].lower()

        if playlist_id not in PLAYLISTS:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"#ERROR: Playlist key '{playlist_id}' not found.".encode("utf-8"))
            return

        target_url = PLAYLISTS[playlist_id]

        try:
            req = urllib.request.Request(
                target_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
                },
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                m3u_content_raw = response.read().decode("utf-8", errors="ignore")

            m3u_content_cleaned = clean_m3u_content(m3u_content_raw)

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
            
