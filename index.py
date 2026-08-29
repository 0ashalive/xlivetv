from http.server import BaseHTTPRequestHandler
import urllib.parse
import urllib.request

# Dynamic playlist mapping (id -> source URL)
PLAYLISTS = {
    "jio":"https://raw.githubusercontent.com/0ashalive/xlivetv/refs/heads/main/jbonio.m3u",
    "bdix":"https://raw.githubusercontent.com/streamifytv/abbas/refs/heads/main/bd.m3u",
    "jago":"https://m3u-tvb.pages.dev/Jjago.br.m3u8",
    
}

# Default playlist ID if none is provided in the URL query
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

# Media player User-Agent signatures (explicitly includes OkHttp variants)
MEDIA_PLAYER_AGENTS = [
    "okhttp",
    "kodi",
    "iptv",
    "tivimate",
    "exoplayer",
]


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        # Fetch lowercased User-Agent header from incoming request
        user_agent = (self.headers.get("User-Agent") or "").lower()

        # 1. Player Verification & Browser Redirection Logic
        is_media_player = any(
            player in user_agent for player in MEDIA_PLAYER_AGENTS
        )
        is_browser = any(
            browser in user_agent for browser in BROWSER_USER_AGENTS
        )

        # Redirect standard web browsers (and non-players) to Telegram
        if is_browser and not is_media_player:
            self.send_response(302)
            self.send_header("Location", TELEGRAM_URL)
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            return

        # 2. Extract ?id= parameter from URL query string
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        playlist_id = query_params.get("id", [DEFAULT_PLAYLIST_ID])[0].lower()

        # Return 404 if requested playlist ID is missing from dictionary
        if playlist_id not in PLAYLISTS:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                f"#ERROR: Playlist key '{playlist_id}' not found.".encode("utf-8")
            )
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
                m3u_content = response.read()

            # 4. Output raw playlist data directly to player
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header(
                "Cache-Control", "no-cache, no-store, must-revalidate"
            )
            self.end_headers()
            self.wfile.write(m3u_content)

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            err_msg = f"#EXTM3U\n#ERROR: Failed to fetch target playlist: {str(e)}"
            self.wfile.write(err_msg.encode("utf-8"))


