from http.server import BaseHTTPRequestHandler
import urllib.parse
import urllib.request
import re

# Dynamic playlist mapping (id -> source URL)
PLAYLISTS = {
    "jio": "https://raw.githubusercontent.com/0ashalive/xlivetv/refs/heads/main/jbonio.m3u",
    "bdix": "https://raw.githubusercontent.com/streamifytv/abbas/refs/heads/main/bd.m3u",
    "jago": "https://m3u-tvb.pages.dev/Jjago.br.m3u8",
    "bdix2": "https://github.com/abusaeeidx/Mrgify-BDIX-IPTV/raw/main/playlist.m3u",
}

DEFAULT_PLAYLIST_ID = "jio"
TELEGRAM_URL = "https://t.me/bdtvlive"

BROWSER_USER_AGENTS = ["mozilla", "chrome", "safari", "edge", "opera", "firefox"]
MEDIA_PLAYER_AGENTS = ["okhttp", "kodi", "iptv", "tivimate", "exoplayer", "vlc", "mxplayer"]

# ==============================================================================
# REMOVAL / FILTER CONFIGURATION
# ==============================================================================
# ১. যেসব কি-ওয়ার্ড, টাইটেল, গ্রুপ বা লিঙ্ক বাদ দিতে চান তা এখানে লিখে রাখুন:
REMOVE_KEYWORDS = [
    "welcome to playz tv",
    "playztv.pages.dev",
    "promo",
    "advertisement",
    "join telegram",
    "subscribe",
    # আরও কিছু রিমুভ করতে চাইলে নিচে কমা (,) দিয়ে যুক্ত করুন:
    # "example_domain.com",
    # "ad_channel_name",
]

# ২. আরও অ্যাডভান্সড ফিল্টারিং এর জন্য Regex Pattern (ঐচ্ছিক):
REMOVE_REGEX_PATTERNS = [
    r"https://playztv.pages.dev/promo/master.m3u8", # Promo m3u8 লিঙ্ক রিমুভ করার জন্য
]


def clean_m3u_content(raw_text: str) -> str:
    """
    প্লেলিস্ট থেকে নির্দিষ্ট অ্যাড বা প্রোমো ব্লক ফিল্টার করে বাদ দেয়।
    """
    lines = raw_text.splitlines()
    cleaned_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # M3U এর চ্যানেল ব্লক (#EXTINF দিয়ে শুরু হয়)
        if line.startswith("#EXTINF"):
            # পুরো ব্লক সংগ্রহ করা (EXTINF + অতিরিক্ত হেডার লাইন + স্ট্রিমিং URL)
            block = [lines[i]]
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("#EXTINF"):
                block.append(lines[i])
                if not lines[i].strip().startswith("#") and lines[i].strip() != "":
                    # স্ট্রিমিং URL পাওয়ার পর ব্লক শেষ
                    break
                i += 1
            
            block_text = "\n".join(block)
            block_text_lower = block_text.lower()
            
            # ১. Keywords Check
            should_remove = any(kw.lower() in block_text_lower for kw in REMOVE_KEYWORDS)
            
            # ২. Regex Patterns Check
            if not should_remove:
                for pattern in REMOVE_REGEX_PATTERNS:
                    if re.search(pattern, block_text, re.IGNORECASE):
                        should_remove = True
                        break
            
            # ফিল্টার পাস করলে মেইন প্লেলিস্টে যুক্ত করা
            if not should_remove:
                cleaned_lines.extend(block)
            continue
        
        else:
            # সাধারণ হেডার বা কমেন্ট বজায় রাখা
            if line:
                cleaned_lines.append(lines[i])
            i += 1

    return "\n".join(cleaned_lines)


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

            # অটোমেটিক ফিল্টারিং ও রিমুভ ফাংশন কল
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
            
