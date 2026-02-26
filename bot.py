import os
import asyncio
import requests
import re
import uuid
import instaloader
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, BufferedInputFile
import yt_dlp

TOKEN = os.getenv('BOT_TOKEN', '8607432390:AAFCXj4h9XQ_VYQ2_7CCpNyg0IEP4ZR612k')
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ── Shared instaloader context (reuse across requests) ─────────────────────────
_loader = instaloader.Instaloader(
    download_videos=False,        # we'll stream manually
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
    quiet=True,
)

# If a session file exists (e.g. uploaded as env var) use it
_SESSION = os.getenv("INSTALOADER_SESSION", "")
if _SESSION:
    import tempfile, base64
    _sf = tempfile.NamedTemporaryFile(delete=False, suffix=".session")
    _sf.write(base64.b64decode(_SESSION))
    _sf.close()
    try:
        _loader.load_session_from_file("session", _sf.name)
    except Exception:
        pass

# ── Helpers ────────────────────────────────────────────────────────────────────
def _shortcode(url: str):
    for pat in [r'instagram\.com/reel/([A-Za-z0-9_-]+)',
                r'instagram\.com/p/([A-Za-z0-9_-]+)',
                r'instagram\.com/tv/([A-Za-z0-9_-]+)']:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None

async def _download_instaloader(url: str) -> str | None:
    """Primary: use instaloader to get video_url then stream-download."""
    sc = _shortcode(url)
    if not sc:
        return None
    try:
        post = instaloader.Post.from_shortcode(_loader.context, sc)
        if not post.is_video:
            return None
        video_url = post.video_url       # direct CDN URL – no auth needed for public posts
        fname = f"{uuid.uuid4()}.mp4"
        resp = requests.get(video_url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(fname, 'wb') as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return fname
    except Exception as e:
        print(f"[instaloader] failed: {e}")
        return None

async def _download_ytdlp(url: str) -> str | None:
    """Fallback: yt-dlp."""
    fname = f"{uuid.uuid4()}.mp4"
    ydl_opts = {
        'format': 'best',
        'outtmpl': fname,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }
    }
    if os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            actual = ydl.prepare_filename(info)
            return actual
    except Exception as e:
        print(f"[yt-dlp] failed: {e}")
        return None

# ── Handlers ───────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply(
        "أهلاً! 👋\nأرسل لي رابط ريلز أو فيديو من انستقرام وسأحمّله لك مباشرة بدون علامة مائية ⚡️"
    )

@dp.message()
async def handle_message(message: types.Message):
    url = (message.text or "").strip()
    if not url:
        return

    if not any(d in url.lower() for d in ('instagram.com', 'instagr.am')):
        await message.reply("❌ أرسل رابط انستقرام مثل:\nhttps://www.instagram.com/reel/...")
        return

    status = await message.reply("⏳ جاري التحميل...")
    filename = None

    try:
        # Layer 1: instaloader (fastest, most reliable for public posts)
        filename = await _download_instaloader(url)

        # Layer 2: yt-dlp fallback
        if not filename or not os.path.exists(filename):
            print("Trying yt-dlp fallback...")
            filename = await _download_ytdlp(url)

        if filename and os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"Sending {size} bytes")
            video = FSInputFile(filename)
            await bot.send_video(
                chat_id=message.chat.id,
                video=video,
                caption="✅ تم التحميل بواسطة البوت ⚡️",
            )
            os.remove(filename)
            await status.delete()
        else:
            await status.edit_text(
                "❌ لم أتمكن من تحميل الفيديو.\n"
                "تأكد أن الحساب عام وأن الرابط صحيح."
            )
    except Exception as e:
        print(f"[handle_message] unexpected error: {e}")
        await status.edit_text(f"❌ حدث خطأ: {str(e)}")
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)

# ── Web server for Render health-check ─────────────────────────────────────────
from aiohttp import web

async def health_check(request):
    return web.Response(text="Bot is running!")

async def main():
    print("Bot starting...")
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    asyncio.create_task(site.start())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
