from discord.ext import commands

OWNER_ID = 987057941020557332

class DiscordCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='ping')
    async def ping(self, ctx):
        """Responds with latency in milliseconds."""
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"Pong! Latency: `{latency}ms`")

    @commands.command(name='say')
    async def say(self, ctx, *, message: str):
        """Repeats the message in the channel. Restricted to specific roles."""
        if ctx.author.id == OWNER_ID or any(role.id == 1340895656755204136 for role in ctx.author.roles):
            await ctx.send(message)
        else:
            await ctx.send("You do not have permission to use this command.")

async def setup(bot):
    await bot.add_cog(DiscordCommands(bot))
