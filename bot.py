import os
import asyncio
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
}

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("أهلاً بك! أرسل لي رابط فيديو/ريلز من الانستقرام وسأقوم بتحميله بدون علامة مائية وبأعلى جودة ⚡️")

@dp.message()
async def handle_message(message: types.Message):
    url = message.text
    if not url:
        return
    
    INSTAGRAM_DOMAINS = ('instagram.com', 'instagr.am', 'instagram')
    if not any(domain in url for domain in INSTAGRAM_DOMAINS):
        await message.reply("❌ الرابط غير مدعوم.\nأرسل لي رابط من الانستقرام مثل:\nhttps://www.instagram.com/reel/...")
        return
        
    status_msg = await message.reply("جاري التحميل... ⏳")
    
    try:
        # Use yt-dlp to download the video
        ydl_opts['outtmpl'] = f'{uuid.uuid4()}.mp4'
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
        # Send the video back
        video = FSInputFile(filename)
        await bot.send_video(chat_id=message.chat.id, video=video, caption="تم التحميل بواسطة البوت ⚡️")
        
        # Cleanup
        if os.path.exists(filename):
            os.remove(filename)
            
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"عذراً، حدث خطأ أثناء التحميل: {str(e)}")

from aiohttp import web

async def health_check(request):
    return web.Response(text="Bot is running!")

async def main():
    print("Bot is starting...")
    
    # Setup web server for Render health checks
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    asyncio.create_task(site.start())
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
