import asyncio
from datetime import datetime
import calendar
import os
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from pymongo import MongoClient

bot = commands.Bot(command_prefix='!')
cluster = MongoClient(os.environ['CONNECT'])
db = cluster['year_progress']
config = db['config']
progress = db['progress']
percentage = progress.find_one({"_id": 0})['percentage']


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    bot.loop.create_task(my_task())


async def my_task():
    while True:
        date = datetime.now()
        hour = get_hour()
        day_of_year = int(date.strftime('%j'))
        total_days = 366 if calendar.isleap(date.year) else 356
        global current_p
        current_p = int(day_of_year / total_days * 100)
        days_left = total_days - day_of_year
        progress_str = draw_bar()
        if current_p > percentage:
            if config.count_documents({}):
                progress.update_one({"_id": 0}, {"$set": {"progress": current_p}})
                for post in config.find():
                    if post['time'] == hour:
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
        await asyncio.sleep(3600)


@bot.command()
async def setup(ctx):
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    hour = get_hour()
    if config.find_one({"guild_id": guild_id}):
        config.update_one({"guild_id": guild_id}, {
            "$set": {"channel_id": channel_id, "time": hour}})
    else:
        post = {"_id": config.count_documents(
            {}), "guild_id": guild_id, "channel_id": channel_id, "time": hour}
        config.insert_one(post)
    channel = bot.get_channel(ctx.channel.id)
    await channel.send(f"{draw_bar()} {current_p}%")


def get_hour():
    current_date = datetime.now()
    return current_date.strftime('%H')


def draw_bar():
    progress = ['\u2591'] * 20
    for i in range(0, int(current_p / 10) * 2):
        progress[i] = '\u2593'
    return ''.join(progress)


bot.run(os.environ['TOKEN'])
