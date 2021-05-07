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
        percentage = progress.find_one({"_id": 0})['progress']
        if current_p > percentage:
            if config.count_documents({}):
                progress.update_one({"_id": 0}, {"$set": {"progress": current_p}})
                for post in config.find():
                    if post['time'] == hour:
                        progress_str = draw_custom_bar(
                            *post['bar_args'], **post['bar_kwargs'])
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
    await ctx.message.delete()
    if config.find_one({"guild_id": guild_id}):
        config.update_one({"guild_id": guild_id}, {
            "$set": {"channel_id": channel_id, "time": hour}})
    else:
        post = {"guild_id": guild_id, "channel_id": channel_id, "time": hour, "bar_args": ('\u2591', '\u2593')}
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


@bot.command()
async def draw(ctx, empty, full, *, kwargs):
    cmd = kwargs.split()
    args = {}
    for c in cmd:
        if c.startswith("--"):
            args[c.lstrip("--")] = cmd[cmd.index(c) + 1]
    bar = draw_custom_bar(empty, full, **args)
    await ctx.send(f"{bar} {current_p}%")


@bot.command()
async def test(ctx):
    data = config.find_one({"channel_id": ctx.channel.id})
    await ctx.send(f"{draw_custom_bar(*data['bar_args'],**data['bar_kwargs'])} {current_p}%")


@bot.command()
async def apply(ctx, empty, full, *, kwargs=None):
    args = {}
    if kwargs:
        cmd = kwargs.split()
        for c in cmd:
            if c.startswith("--"):
                args[c.lstrip("--")] = cmd[cmd.index(c) + 1]
    config.update_one({"channel_id": ctx.channel.id},
                      {"$set": {"bar_args": (empty, full), "bar_kwargs": args}})


def draw_custom_bar(empty, full, *, st_em=None, st_fl=None, end_em=None, end_fl=None, left=None, right=None, length=20, critic=5):
    percentage = progress.find_one({"_id": 0})['progress']
    if st_em is None:
        st_em = empty
    if st_fl is None:
        st_fl = full
    if end_em is None:
        end_em = empty
    if end_fl is None:
        end_fl = full
    bar = [empty] * int(length)
    j = 0
    for i in range(5, percentage):
        if i % int(critic) == 0:
            j += 1
            bar[j] = full

    bar[0] = st_em if percentage < 5 else st_fl
    bar[-1] = end_em if percentage <= 99 else end_fl
    if left:
        bar.insert(0, left)
    if right:
        bar.append(right)
    return ''.join(bar)


bot.run(os.environ['TOKEN'])
