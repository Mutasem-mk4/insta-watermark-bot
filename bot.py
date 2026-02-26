import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
import yt_dlp
import uuid

# Token: Priority to Environment Variable, fallback to hardcoded (for local test)
TOKEN = os.getenv('BOT_TOKEN', '8607432390:AAFCXj4h9XQ_VYQ2_7CCpNyg0IEP4ZR612k')
bot = Bot(token=TOKEN)
dp = Dispatcher()

# yt-dlp options for best quality, no watermark
ydl_opts = {
    'format': 'best',
    'outtmpl': '%(id)s.%(ext)s',
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-us,en;q=0.5',
        'Sec-Fetch-Mode': 'navigate',
    }
}

# If cookies.txt exists, use it
if os.path.exists('cookies.txt'):
    ydl_opts['cookiefile'] = 'cookies.txt'

async def download_with_cobalt(url):
    """Fallback downloader using public Cobalt API instances."""
    instances = [
        "https://cobalt.canine.tools/api/json",
        "https://cobalt.meowing.de/api/json",
        "https://api.cobalt.tools/api/json"
    ]
    filename = f"{uuid.uuid4()}.mp4"
    
    for api_url in instances:
        try:
            payload = {"url": url}
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            response = requests.post(api_url, json=payload, headers=headers, timeout=20)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") in ["stream", "redirect"]:
                    video_url = data.get("url")
                    v_resp = requests.get(video_url, stream=True, timeout=30)
                    if v_resp.status_code == 200:
                        with open(filename, 'wb') as f:
                            for chunk in v_resp.iter_content(chunk_size=8192):
                                f.write(chunk)
                        return filename
        except Exception:
            continue
    return None

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("أهلاً بك! أرسل لي رابط فيديو/ريلز من الانستقرام وسأقوم بتحميله بدون علامة مائية وبأعلى جودة ⚡️")

@dp.message()
async def handle_message(message: types.Message):
    url = message.text
    if not url:
        return
    
    INSTAGRAM_DOMAINS = ('instagram.com', 'instagr.am', 'instagram')
    if not any(domain in url.lower() for domain in INSTAGRAM_DOMAINS):
        await message.reply("❌ الرابط غير مدعوم.\nأرسل لي رابط من الانستقرام مثل:\nhttps://www.instagram.com/reel/...")
        return
        
    status_msg = await message.reply("جاري التحميل... ⏳")
    filename = None
    
    try:
        # Step 1: Try Primary (yt-dlp)
        try:
            temp_filename = f'{uuid.uuid4()}.mp4'
            ydl_opts['outtmpl'] = temp_filename
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
        except Exception as e:
            # Step 2: Try Fallback (Cobalt)
            print(f"yt-dlp failed, trying Cobalt: {e}")
            filename = await download_with_cobalt(url)
            
        if filename and os.path.exists(filename):
            video = FSInputFile(filename)
            await bot.send_video(chat_id=message.chat.id, video=video, caption="تم التحميل بواسطة البوت ⚡️")
            os.remove(filename)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ عذراً، لم أتمكن من تحميل الفيديو. قد يكون الحساب خاصاً أو هناك حظر مؤقت من انستقرام.")
        
    except Exception as e:
        await status_msg.edit_text(f"عذراً، حدث خطأ أثناء التحميل: {str(e)}")

from aiohttp import web

async def health_check(request):
    return web.Response(text="Bot is running!")

async def main():
    print("Bot is starting...")
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    asyncio.create_task(site.start())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
