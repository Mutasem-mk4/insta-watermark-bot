import os
import asyncio
import requests
import re
import uuid
import json
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
import yt_dlp

TOKEN = os.getenv('BOT_TOKEN', '8607432390:AAFCXj4h9XQ_VYQ2_7CCpNyg0IEP4ZR612k')
bot = Bot(token=TOKEN)
dp = Dispatcher()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


# ── Layer 1: FastDL ─────────────────────────────────────────────────────────────
def _download_url_fastdl(url: str) -> str | None:
    """استخراج رابط تنزيل من fastdl.app"""
    try:
        session = requests.Session()
        r = session.get('https://fastdl.app/instagram', headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        csrf = soup.find('meta', {'name': 'csrf-token'})
        csrf_token = csrf['content'] if csrf else ''

        post_headers = {
            **HEADERS,
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': csrf_token,
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://fastdl.app',
            'Referer': 'https://fastdl.app/instagram',
        }
        r2 = session.post(
            'https://fastdl.app/api/media/instagram',
            json={'url': url},
            headers=post_headers,
            timeout=30,
        )
        if r2.status_code == 200:
            data = r2.json()
            # Look for video url in various response formats
            if data.get('url'):
                return data['url']
            if isinstance(data.get('data'), list):
                for item in data['data']:
                    if isinstance(item, dict) and item.get('url'):
                        return item['url']
            if isinstance(data.get('data'), dict):
                return data['data'].get('url')
    except Exception as e:
        print(f'[fastdl] error: {e}')
    return None


# ── Layer 2: SSS Instagram ──────────────────────────────────────────────────────
def _download_url_sss(url: str) -> str | None:
    """استخراج رابط تنزيل من sssinstagram.com"""
    try:
        session = requests.Session()
        r = session.get('https://sssinstagram.com/', headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        token_el = soup.find('input', {'name': '_token'})
        token = token_el['value'] if token_el else ''

        post_headers = {
            **HEADERS,
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://sssinstagram.com',
            'Referer': 'https://sssinstagram.com/',
        }
        r2 = session.post(
            'https://sssinstagram.com/api/convert',
            json={'url': url, '_token': token},
            headers=post_headers,
            timeout=30,
        )
        if r2.status_code == 200:
            data = r2.json()
            # sssinstagram returns data.data[].url or data.url
            if data.get('url'):
                return data['url']
            items = data.get('data', [])
            if isinstance(items, list):
                for item in items:
                    if item.get('url'):
                        return item['url']
    except Exception as e:
        print(f'[sssinstagram] error: {e}')
    return None


# ── Layer 3: SnapInsta ──────────────────────────────────────────────────────────
def _download_url_snapinsta(url: str) -> str | None:
    """استخراج رابط تنزيل من snapinsta.app"""
    try:
        session = requests.Session()
        r = session.get('https://snapinsta.app/', headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        token_el = (
            soup.find('input', {'name': '_token'}) or
            soup.find('input', {'name': 'token'})
        )
        token = token_el['value'] if token_el else ''

        post_headers = {
            **HEADERS,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://snapinsta.app',
            'Referer': 'https://snapinsta.app/',
        }
        r2 = session.post(
            'https://snapinsta.app/action',
            data={'url': url, '_token': token},
            headers=post_headers,
            timeout=30,
        )
        if r2.status_code == 200:
            try:
                data = r2.json()
                if data.get('url'):
                    return data['url']
            except Exception:
                soup2 = BeautifulSoup(r2.text, 'html.parser')
                for a in soup2.find_all('a', href=True):
                    href = a['href']
                    if '.mp4' in href or 'cdn' in href:
                        return href
    except Exception as e:
        print(f'[snapinsta] error: {e}')
    return None


# ── Layer 4: yt-dlp ─────────────────────────────────────────────────────────────
def _download_url_ytdlp(url: str) -> str | None:
    """yt-dlp fallback — يحاول تنزيل الفيديو مباشرة"""
    fname = f'/tmp/{uuid.uuid4()}.mp4'
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': fname,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': HEADERS['User-Agent'],
        },
    }
    if os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            actual = ydl.prepare_filename(info)
            return actual if os.path.exists(actual) else None
    except Exception as e:
        print(f'[yt-dlp] error: {e}')
    return None


# ── Stream-download helper ──────────────────────────────────────────────────────
def _stream_download(video_url: str) -> str | None:
    """تنزيل الفيديو من رابط مباشر وحفظه مؤقتاً"""
    fname = f'/tmp/{uuid.uuid4()}.mp4'
    try:
        r = requests.get(video_url, stream=True, timeout=60, headers=HEADERS)
        r.raise_for_status()
        with open(fname, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        if os.path.getsize(fname) > 10_000:   # تحقق أن الملف ليس فارغاً
            return fname
    except Exception as e:
        print(f'[stream_download] error: {e}')
        if os.path.exists(fname):
            os.remove(fname)
    return None


# ── Master download (tries all layers) ─────────────────────────────────────────
async def download_reel(url: str) -> str | None:
    loop = asyncio.get_event_loop()

    # Layer 1
    print('[L1] Trying FastDL...')
    video_url = await loop.run_in_executor(None, _download_url_fastdl, url)
    if video_url:
        print(f'[L1] Got URL: {video_url[:60]}')
        fname = await loop.run_in_executor(None, _stream_download, video_url)
        if fname:
            return fname

    # Layer 2
    print('[L2] Trying SSS Instagram...')
    video_url = await loop.run_in_executor(None, _download_url_sss, url)
    if video_url:
        print(f'[L2] Got URL: {video_url[:60]}')
        fname = await loop.run_in_executor(None, _stream_download, video_url)
        if fname:
            return fname

    # Layer 3
    print('[L3] Trying SnapInsta...')
    video_url = await loop.run_in_executor(None, _download_url_snapinsta, url)
    if video_url:
        print(f'[L3] Got URL: {video_url[:60]}')
        fname = await loop.run_in_executor(None, _stream_download, video_url)
        if fname:
            return fname

    # Layer 4
    print('[L4] Trying yt-dlp direct...')
    fname = await loop.run_in_executor(None, _download_url_ytdlp, url)
    if fname:
        return fname

    return None


# ── URL validation ──────────────────────────────────────────────────────────────
def is_instagram_url(text: str) -> bool:
    return bool(re.search(r'https?://(www\.)?(instagram\.com|instagr\.am)/', text))


# ── Handlers ────────────────────────────────────────────────────────────────────
@dp.message(Command('start'))
async def send_welcome(message: types.Message):
    await message.reply(
        '👋 أهلاً بك في بوت تنزيل الريلز!\n\n'
        '📲 أرسل لي أي رابط من انستقرام وسأحمّله لك فوراً بدون علامة مائية ✨\n\n'
        'يدعم: Reels · Posts · IGTV\n\n'
        'للمساعدة اكتب /help'
    )


@dp.message(Command('help'))
async def send_help(message: types.Message):
    await message.reply(
        '📖 **كيفية الاستخدام:**\n\n'
        '1️⃣ افتح الريلز أو الفيديو في انستقرام\n'
        '2️⃣ اضغط على ••• ثم "نسخ الرابط"\n'
        '3️⃣ أرسل الرابط هنا\n\n'
        '✅ يعمل مع الحسابات العامة فقط\n'
        '⏱️ قد يستغرق حتى 30 ثانية\n\n'
        'مثال على رابط صحيح:\n'
        '`https://www.instagram.com/reel/ABC123/`',
        parse_mode='Markdown',
    )


@dp.message()
async def handle_message(message: types.Message):
    text = (message.text or '').strip()

    if not text:
        return

    if not is_instagram_url(text):
        await message.reply(
            '❌ الرابط غير صحيح!\n\n'
            'أرسل رابطاً من انستقرام مثل:\n'
            '`https://www.instagram.com/reel/...`',
            parse_mode='Markdown',
        )
        return

    status = await message.reply('⏳ جاري التحميل، انتظر قليلاً...')
    filename = None

    try:
        filename = await download_reel(text)

        if filename and os.path.exists(filename):
            size_mb = os.path.getsize(filename) / 1_048_576
            print(f'[send] {size_mb:.2f} MB → {filename}')
            video = FSInputFile(filename)
            await bot.send_video(
                chat_id=message.chat.id,
                video=video,
                caption='✅ تم التحميل بواسطة البوت ⚡️',
                supports_streaming=True,
            )
            await status.delete()
        else:
            await status.edit_text(
                '❌ لم أتمكن من تحميل الفيديو.\n\n'
                '**أسباب محتملة:**\n'
                '• الحساب خاص (private)\n'
                '• الرابط منتهي الصلاحية\n'
                '• انستقرام يحجب الطلبات مؤقتاً\n\n'
                'جرب مرة أخرى بعد دقيقة 🔄',
                parse_mode='Markdown',
            )
    except Exception as e:
        print(f'[handle_message] unexpected error: {e}')
        await status.edit_text(f'❌ حدث خطأ غير متوقع:\n`{str(e)[:200]}`', parse_mode='Markdown')
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)


# ── Web server (Render health-check) ───────────────────────────────────────────
from aiohttp import web


async def health_check(request):
    return web.Response(text='Bot is running! ✅')


async def main():
    print('🤖 Instagram Bot starting...')
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f'🌐 Health check running on port {port}')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
