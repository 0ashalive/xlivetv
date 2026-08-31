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
    
    # Additional Categories
    
}

DEFAULT_PLAYLIST_ID = "jio"
TELEGRAM_URL = "https://t.me/bdtvlive"

# Browsers to detect and redirect to Telegram
BROWSER_USER_AGENTS = [
    "mozilla",
    "chrome",
    "safari",
    "edge",
    "opera",
    "firefox",
]

# Media player User-Agent signatures allowed to fetch playlists directly
MEDIA_PLAYER_AGENTS = [
    "okhttp",
    "kodi",
    "iptv",
    "tivimate",
    "exoplayer",
    "vlc",
    "mxplayer",
]

# ==============================================================================
# 2. AUTOMATIC REMOVAL CONFIGURATION
# ==============================================================================

# Keywords in channel names, group titles, or metadata to automatically filter out
REMOVE_KEYWORDS = [
    "welcome to playz tv",
    "advertisement",
    "join telegram",
    "subscribe",
    # Add extra keywords below:
    # "another_ad_keyword",
]

# Stream URLs or domain matches to automatically filter out
REMOVE_URLS = [
    "https://playztv.pages.dev/promo/master.m3u8",
    # Add extra stream URLs or domain paths below:
    # "https://example.com/promo.m3u8",
]


# ==============================================================================
# 3. M3U CLEANING ENGINE
# ==============================================================================
def clean_m3u_content(raw_text: str) -> str:
    """
    Parses raw M3U playlist data line-by-line into discrete channel blocks.
    If a block contains any matched keywords or URLs, the entire block is stripped automatically.
    """
    lines = raw_text.splitlines()
    cleaned_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Identify the start of an M3U entry block
        if line.startswith("#EXTINF"):
            block = [lines[i]]
            i += 1
            # Group all tags, metadata, and stream URLs belonging to this entry
            while i < len(lines) and not lines[i].strip().startswith("#EXTINF"):
                block.append(lines[i])
                if not lines[i].strip().startswith("#") and lines[i].strip() != "":
                    break
                i += 1
            
            block_text = "\n".join(block)
            block_text_lower = block_text.lower()
            
            should_remove = False

            # Check 1: Match against target keywords
            if any(kw.lower() in block_text_lower for kw in REMOVE_KEYWORDS if kw.strip()):
                should_remove = True

            # Check 2: Match against target stream URLs or hostnames
            if not should_remove:
                if any(url.lower() in block_text_lower for url in REMOVE_URLS if url.strip()):
                    should_remove = True

            # Retain block if it passes all removal checks
            if not should_remove:
                cleaned_lines.extend(block)
            continue
        
        else:
            # Maintain standard headers (#EXTM3U) and non-block lines
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

        # Check request client type
        is_media_player = any(player in user_agent for player in MEDIA_PLAYER_AGENTS)
        is_browser = any(browser in user_agent for browser in BROWSER_USER_AGENTS)

        # 1. Redirect standard browsers to Telegram
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

        # Handle missing key
        if playlist_id not in PLAYLISTS:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"#ERROR: Playlist key '{playlist_id}' not found.".encode("utf-8"))
            return

        target_url = PLAYLISTS[playlist_id]

        # 3. Fetch remote M3U playlist content
        try:
            req = urllib.request.Request(
                target_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
                },
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                m3u_content_raw = response.read().decode("utf-8", errors="ignore")

            # 4. Filter out specified keywords and URLs dynamically
            m3u_content_cleaned = clean_m3u_content(m3u_content_raw)

            # 5. Output processed playlist to media player
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
            
