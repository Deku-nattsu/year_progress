import asyncio
from datetime import datetime
import calendar
import os
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from pymongo import MongoClient

bot = commands.Bot(command_prefix='!')
persentage = 0
cluster = MongoClient(os.environ['CONNECT'])
db = cluster['year_progress']
collection = db['config']


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    bot.loop.create_task(my_task())


async def my_task():
    while True:
        current_date = datetime.now()
        day_of_year = int(current_date.strftime('%j'))
        total_days = 366 if calendar.isleap(current_date.year) else 356
        current_p = int(day_of_year / total_days * 100)
        days_left = total_days - day_of_year
        progress = ['\u2591'] * 20
        for i in range(0, int(current_p / 10) * 2):
            progress[i] = '\u2593'
        progress_str = ''.join(progress)
        if current_p > persentage:
            if collection.count_documents({}):
                persentage = current_p
                for post in collection.find():
                    channel = bot.get_channel(post['channel_id'])
                    await channel.send(f"{progress_str} {current_p}%")
            W, H = (512, 512)
            img = Image.new("RGB", (W, H), (0, 0, 0))
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype("digital-7.ttf", 300)
            w, h = draw.textsize(str(days_left), font)
            draw.text(((W - w) / 2, 150),
                      str(days_left), (255, 255, 255), font=font)
            img.save("pfp.jpg")
            with open("pfp.jpg", 'rb') as pfp:
                await bot.user.edit(avatar=pfp.read())
        await asyncio.sleep(86400)


@bot.command()
async def setup(ctx):
    if collection.find_one({"guild_id": ctx.guild.id}):
        collection.update_one({"guild_id": ctx.guild.id}, {"$set": {"channel_id": ctx.channel.id}})
    else:
        post = {"_id": collection.count_documents({}), "guild_id": ctx.guild.id, "channel_id": ctx.channel.id}
        collection.insert_one(post)


bot.run(os.environ['TOKEN'])
