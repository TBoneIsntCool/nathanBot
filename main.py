import discord
from discord.ext import commands
import os
import importlib
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='-', intents=intents)

loaded_modules = []

def load_modules():
    global loaded_modules
    for filename in os.listdir('./modules'):
        if filename.endswith('.py') and filename != 'main.py':
            module_name = f'modules.{filename[:-3]}'
            try:
                module = importlib.import_module(module_name)
                loaded_modules.append(module)
            except Exception as e:
                print(f"Error loading {module_name}: {e}")

def reload_modules():
    global loaded_modules
    for module in loaded_modules:
        importlib.reload(module)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    load_modules()

@bot.command()
async def reload(ctx):
    reload_modules()
    await ctx.send("Modules reloaded!")

bot.run(TOKEN)