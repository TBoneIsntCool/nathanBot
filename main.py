import discord
from discord.ext import commands
import os
import importlib
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = 987057941020557332
REQUIRED_ROLE_ID = 1343002349291044984

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='.', intents=intents)

loaded_modules = []
maintenance_mode = True

async def load_modules():
    global loaded_modules
    loaded_modules = []
    for filename in os.listdir('./modules'):
        if filename.endswith('.py') and filename != 'main.py':
            module_name = f'modules.{filename[:-3]}'
            try:
                await bot.load_extension(module_name)
                loaded_modules.append(module_name)
                print(f'Loaded {filename}')
            except Exception as e:
                print(f'Failed to load {filename}: {e}')

async def reload_modules():
    reloaded = []
    for module in loaded_modules:
        try:
            await bot.reload_extension(module)
            reloaded.append(module.split('.')[-1])
        except Exception as e:
            print(f"Failed to reload {module}: {e}")
    
    return reloaded

def has_required_role(ctx):
    return ctx.author.id == OWNER_ID or any(role.id == REQUIRED_ROLE_ID for role in ctx.author.roles)

@bot.event
async def on_ready():
    if maintenance_mode:
        await bot.change_presence(status=discord.Status.idle, activity=discord.CustomActivity("MAINTENANCE MODE - Wating for a bot developer to start the bot."))
        print('Bot is in maintenance mode.')
    else:
        await load_modules()
        await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="San Diego Roleplay"))
        print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.content.startswith('.') and not message.content[1:].split()[0] in bot.all_commands:
        await message.channel.send("Command not found, please do `.help` for the command list.")
    await bot.process_commands(message)

@bot.command()
async def start(ctx):
    """Starts the bot and loads all modules."""
    if not has_required_role(ctx):
        await ctx.send("You do not have permission to use this command.")
        return

    global maintenance_mode
    if maintenance_mode:
        maintenance_mode = False
        await load_modules()
        await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="San Diego Roleplay"))

        embed = discord.Embed(title="Modules Loaded", color=discord.Color.green())
        embed.description = "The modules have been loaded, and the bot is online."
        await ctx.send(embed=embed)
    else:
        await ctx.send("Bot is already running.")

@bot.command()
async def stop(ctx):
    """Stops the bot and enters maintenance mode."""
    if not has_required_role(ctx):
        await ctx.send("You do not have permission to use this command.")
        return

    global maintenance_mode
    maintenance_mode = True
    await bot.change_presence(status=discord.Status.idle, activity=discord.CustomActivity("MAINTENANCE MODE"))

    for module in loaded_modules:
        try:
            await bot.unload_extension(module)
            print(f'Unloaded {module}')
        except Exception as e:
            print(f'Failed to unload {module}: {e}')

    loaded_modules.clear()

    embed = discord.Embed(title="Bot Stopped", color=discord.Color.red())
    embed.description = "All command modules have been unloaded. The bot is now in maintenance mode."
    await ctx.send(embed=embed)

@bot.command()
async def reload(ctx):
    """Reloads all modules."""
    if not has_required_role(ctx):
        await ctx.send("You do not have permission to use this command.")
        return

    if maintenance_mode:
        await ctx.send("Bot is in maintenance mode. Start it first using `.start` before reloading modules.")
        return

    embed = discord.Embed(title="Reloading Modules...", color=discord.Color.blue())
    message = await ctx.send(embed=embed)

    reloaded_modules = await reload_modules()

    if reloaded_modules:
        module_list = ', '.join([f"**{mod}**" for mod in reloaded_modules])
        embed.title = "Reload Complete"
        embed.description = f"Reloaded modules: {module_list}."
        embed.color = discord.Color.green()
    else:
        embed.title = "Reload Failed"
        embed.description = "No modules were reloaded."
        embed.color = discord.Color.red()

    await message.edit(embed=embed)

bot.run(TOKEN)
