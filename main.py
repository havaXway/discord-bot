import discord
import yt_dlp
import datetime
import os

from discord import FFmpegPCMAudio
from discord.utils import get
from discord.ext import commands

settings = {
    'token': 'Ведите свой токен дискорд бота из лк Discord.dev',
    'bot': 'bot',
    'id': 825365074850873424,
    'prefix': '+'}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'noplaylist': True,
    'simulate': 'True',
    'preferredquality': '192',
    'preferredcodec': 'mp3',
    'key': 'FFmpegExtractAudio'}

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command("help")
loop_flag = False


class Queue:
    def __init__(self):
        self.__value = []
        self.__pt = 0

    def q_add(self, element):
        self.__value.append(element)

    def q_remove(self):
        if not self.is_empty():
            tmp = self.__value[self.__pt]
            self.__pt += 1
            if self.__pt > len(self.__value) / 2:
                self.__value = self.__value[self.__pt:]
                self.__pt = 0
            return tmp
        else:
            return -1

    def q_rem_by_index(self, arg):
        return self.__value.pop(self.__pt + arg)

    def get_value(self):
        return self.__value[self.__pt:]

    def is_empty(self):
        return not self.__value

    def __str__(self):
        return str(self.__value[self.__pt:])

    def __getitem__(self, item):
        return self.__value[item]

    def __len__(self):
        return len(self.__value)


songs_queue = Queue()

@bot.event
async def on_ready():
    print('Status: online')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, name='Yotube'))


@bot.command(aliases=['j'])
async def join(ctx):
    if ctx.message.author.voice:
        if not ctx.voice_client:
            await ctx.message.author.voice.channel.connect(reconnect=True)
        else:
            await ctx.voice_client.move_to(ctx.message.author.voice.channel)
    else:
        await ctx.message.reply('Вы должны находиться в голосовом канале !')


@bot.command(aliases=['d', 'dis'])
async def disconnect(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.message.reply('Вы попытались разбудить бота,\
 но он в отключке.')


@bot.command()
async def add(ctx, *url):
    url = ' '.join(url)
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except:
            info = ydl.extract_info(f"ytsearch:{url}",
                                    download=True)['entries'][0]

    URL = info['url']
    name = info['title']
    time = str(datetime.timedelta(seconds=info['duration']))
    songs_queue.q_add([name, time, URL])
    embed = discord.Embed(description=f'Записываю [{name}]({url}) в очередь',
                          colour=discord.Colour.red())
    await ctx.message.reply(embed=embed)


def step_and_remove(voice_client):
    if loop_flag:
        songs_queue.q_add(songs_queue.get_value()[0])
    songs_queue.q_remove()
    audio_player_task(voice_client)


def audio_player_task(voice_client):
    if not voice_client.is_playing() and songs_queue.get_value():
        voice_client.play(discord.FFmpegPCMAudio(
            executable="ffmpeg.exe",
            source=songs_queue.get_value()[0][2],
            **FFMPEG_OPTIONS),
            after=lambda e: step_and_remove(voice_client))


@bot.command(aliases=['p', 'pl'])
async def play(ctx, *url):
    await join(ctx)
    await add(ctx, ' '.join(url))
    voice_client = ctx.guild.voice_client
    audio_player_task(voice_client)


@bot.command()
async def loop(ctx):
    global loop_flag
    loop_flag = True
    await ctx.message.reply('Залуплено')


@bot.command()
async def unloop(ctx):
    global loop_flag
    loop_flag = False
    await ctx.message.reply('Отлуплено')


@bot.command(aliases=['list', 'q'])
async def queue(ctx):
    if len(songs_queue.get_value()) > 0:
        only_names_and_time_queue = []
        for i in songs_queue.get_value():
            name = i[0]
            if len(i[0]) > 30:
                name = i[0][:30] + '...'
            only_names_and_time_queue.append(f'`{name:<33}   {i[1]:>20}`\n')
        c = 0
        queue_of_queues = []
        while c < len(only_names_and_time_queue):
            queue_of_queues.append(only_names_and_time_queue[c:c + 10])
            c += 10

        embed = discord.Embed(title=f'ОЧЕРЕДЬ [LOOP: {loop_flag}]',
                              description=''.join(queue_of_queues[0]),
                              colour=discord.Colour.red())
        await ctx.send(embed=embed)

        for i in range(1, len(queue_of_queues)):
            embed = discord.Embed(description=''.join(queue_of_queues[i]),
                                  colour=discord.Colour.red())
            await ctx.send(embed=embed)
    else:
        await ctx.send('Очередь пуста')


@bot.command(aliases=['ps', 'wait', 'wt', 'stop'])
async def pause(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice:
        voice.pause()
        await ctx.message.reply('paused...')


@bot.command(aliases=['rs', 'continue', 'cnt', 'ct'])
async def resume(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice:
        if voice.is_paused():
            voice.resume()
            await ctx.message.reply('unpaused...')


@bot.command(aliases=['sk', 'next'])
async def skip(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice:
        voice.stop()


@bot.command(aliases=['cl', 'c'])
async def clear(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice:
        voice.stop()
        while not songs_queue.is_empty():
            songs_queue.q_remove()


bot.run(settings['token'])
