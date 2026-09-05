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
    "entall": "https://bestiptvpro.pages.dev/All.m3u",
    "sports": "https://bestiptvpro.pages.dev/Sports.m3u",
    "fmradio": "https://bestiptvpro.pages.dev/FMRadio.m3u",
    "music": "https://drive.usercontent.google.com/u/0/uc?id=1y7PPKjhnhDZktA_HQxXfQns_dZWJG5Er&export=download",
    "257": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/entertainment.m3u",
    "animation": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/animation.m3u",
}

DEFAULT_PLAYLIST_ID = "jio"
TELEGRAM_URL = "https://t.me/bdtvlive"

BROWSER_USER_AGENTS = ["mozilla", "chrome", "safari", "edge", "opera", "firefox"]
MEDIA_PLAYER_AGENTS = ["okhttp", "kodi", "iptv", "tivimate", "exoplayer", "vlc", "mxplayer"]

# ==============================================================================
# 2. AUTOMATIC REMOVAL CONFIGURATION
# ==============================================================================

# A. যেসব নির্দিষ্ট লিঙ্ক বা ডোমেইন মুছে ফেলতে চান:
REMOVE_URLS = [
    "https://playztv.pages.dev/promo/master.m3u8",
    "https://raw.githubusercontent.com/streamifytv/abbas/refs/heads/main/sportzfy.ts",
    "sportzfy.ts",
    "1000398131.png",
    # নতুন কোনো লিঙ্ক বাদ দিতে চাইলে নিচে কমা (,) দিয়ে বসাবেন:
    # "https://example.com/ad.m3u8",
]

# B. যেসব টেক্সট বা কি-ওয়ার্ড যুক্ত চ্যানেল/লাইন মুছে ফেলতে চান:
REMOVE_KEYWORDS = [
    "welcome to playz tv",
    "playz tv",
    "sportzfy",
    "promo",
    "advertisement",
    "join telegram",
    "subscribe",
    "new app",
    "download app",
    "Download Sportzfy TV",
    # নতুন কোনো কি-ওয়ার্ড বাদ দিতে চাইলে নিচে কমা (,) দিয়ে বসাবেন:
    # "another_keyword",
]


# ==============================================================================
# 3. UNIVERSAL M3U CLEANING & DEDUPLICATION ENGINE
# ==============================================================================
def clean_m3u_content(raw_text: str) -> str:
    """
    Parses M3U content and strictly filters out targeted URLs, keywords, 
    standalone ad links (even without #EXTINF), and duplicates.
    """
    lines = raw_text.splitlines()
    cleaned_lines = []
    seen_stream_urls = set()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue

        # ১. যদি লিঙ্ক বা লাইনে কোনো ফিল্টার কি-ওয়ার্ড/ইউআরএল থাকে তবে সরাসরি স্কিপ করবে
        line_lower = line.lower()
        if any(url.lower() in line_lower for url in REMOVE_URLS if url.strip()):
            i += 1
            continue
        if any(kw.lower() in line_lower for kw in REMOVE_KEYWORDS if kw.strip()):
            i += 1
            continue

        # ২. স্ট্যান্ডার্ড #EXTINF চ্যানেল ব্লক প্রসেস করা
        if line.startswith("#EXTINF"):
            block = [lines[i]]
            i += 1
            
            stream_url = ""
            while i < len(lines) and not lines[i].strip().startswith("#EXTINF"):
                curr = lines[i].strip()
                block.append(lines[i])
                if curr and not curr.startswith("#"):
                    stream_url = curr
                    break
                i += 1
            
            block_text = "\n".join(block).lower()
            
            should_remove = False

            # ব্লকের ভেতরে কোনো ফিল্টার লিঙ্ক বা কি-ওয়ার্ড আছে কি না চেক
            if any(url.lower() in block_text for url in REMOVE_URLS if url.strip()):
                should_remove = True
            elif any(kw.lower() in block_text for kw in REMOVE_KEYWORDS if kw.strip()):
                should_remove = True
            
            # ডুপ্লিকেট লিঙ্ক ফিল্টারিং
            if not should_remove and stream_url:
                norm_url = stream_url.lower()
                if norm_url in seen_stream_urls:
                    should_remove = True
                else:
                    seen_stream_urls.add(norm_url)

            if not should_remove:
                cleaned_lines.extend(block)
            continue
        
        # ৩. Standalone URLs বা অন্যান্য ট্যাগের (যেমন #EXTVLCOPT) ফিল্টারিং
        else:
            if not line.startswith("#"):
                norm_url = line.lower()
                if norm_url in seen_stream_urls:
                    i += 1
                    continue
                seen_stream_urls.add(norm_url)
            
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
            
