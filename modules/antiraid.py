import discord
import pytz
from discord.ext import commands, tasks
from collections import defaultdict
import asyncio
from datetime import datetime, timedelta, timezone

GUILD_ID = 1186834450693234758
AUTHORIZED_USER_IDS = [792547313716690965, 497196352866877441, 1268956236074713088]  
LOG_CHANNEL_ID = 1342601425124851965  
TIMEOUT_DURATION = 3600  
COOLDOWN_TIME = 60  
EXCLUDED_CHANNELS = [1340865256271908884, 1340865258255810580, 1340865259644387419, 1340865274571657359, 1340865276199178331]  

class RaidProtection(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.join_counts = defaultdict(int)
        self.message_counts = defaultdict(int)
        self.mention_counts = defaultdict(int)
        self.role_change_counts = defaultdict(int)
        self.channel_change_counts = defaultdict(int)
        self.webhook_creation_counts = defaultdict(int)
        self.removed_roles = defaultdict(list)
        self.last_triggered = defaultdict(lambda: datetime.min)  
        self.reset_counters.start()

    def cog_unload(self):
        self.reset_counters.cancel()

    @tasks.loop(seconds=60)
    async def reset_counters(self):
        self.join_counts.clear()
        self.message_counts.clear()
        self.mention_counts.clear()
        self.role_change_counts.clear()
        self.channel_change_counts.clear()
        self.webhook_creation_counts.clear()

    async def send_log_message(self, embed, view=None):
        try:
            channel = self.bot.get_channel(LOG_CHANNEL_ID)
            if channel:
                await channel.send(embed=embed, view=view)  
                print(f"Log message sent to channel {channel.id} with buttons.")
            else:
                print(f"Channel with ID {LOG_CHANNEL_ID} not found.")
        except discord.Forbidden:
            print(f"Failed to send log message to channel ID {LOG_CHANNEL_ID}.")
        except discord.HTTPException as e:
            print(f"HTTPException while sending log message: {e}")

    async def timeout_and_remove_roles(self, user, reason):
        if user.bot:
            return  

        now = datetime.now(pytz.utc)  
        last_triggered_time = self.last_triggered.get(user.id)

        if last_triggered_time:
            last_triggered_time = last_triggered_time.replace(tzinfo=pytz.utc)  

            if now - last_triggered_time < timedelta(seconds=COOLDOWN_TIME):
                print("Cooldown active. Not timing out.")
                return

        self.last_triggered[user.id] = now

        try:
            await user.timeout(timedelta(seconds=TIMEOUT_DURATION), reason=reason)
        except discord.Forbidden:
            print(f"Failed to timeout user {user} due to missing permissions.")
        except discord.HTTPException as e:
            print(f"HTTPException while timing out user {user}: {e}")

        removed_roles = []
        for role in user.roles:
            if role != user.guild.default_role:  
                try:
                    await user.remove_roles(role, reason=reason)
                    removed_roles.append(role)
                    await asyncio.sleep(1)  
                except discord.Forbidden:
                    print(f"Failed to remove role {role.name} from user {user} due to missing permissions.")
                except discord.HTTPException as e:
                    print(f"HTTPException while removing role {role.name} from user {user}: {e}")
                    await asyncio.sleep(10)  
        self.removed_roles[user.id] = removed_roles

        embed = discord.Embed(
            title="You have been timed out",
            description=f"You have been timed out for {TIMEOUT_DURATION // 60} minutes and your roles have been removed. Reason: {reason}",
            color=discord.Color.red()
        )
        try:
            dm_channel = await user.create_dm()
            await dm_channel.send(embed=embed)
            print(f"DM sent to {user} about timeout.")
        except discord.Forbidden:
            print(f"Failed to send DM to user {user}. They might have DMs disabled or the bot might not have permission.")
        except discord.HTTPException as e:
            print(f"HTTPException while sending DM to user {user}: {e}")

        log_embed = discord.Embed(
            title="User Timed Out and Roles Removed",
            description=f"User {user} has been timed out for {TIMEOUT_DURATION // 60} minutes and their roles have been removed. Reason: {reason}",
            color=discord.Color.red()
        )
        await self.send_log_message(log_embed, view=self.ActionView(self, user))

    class ActionView(discord.ui.View):
        def __init__(self, cog, member):
            super().__init__()
            self.cog = cog
            self.member = member

        @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger)
        async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            try:
                await self.member.guild.ban(self.member, reason="Raid Protection: Manual Ban")
                await interaction.response.send_message(f"{self.member} has been banned.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message(f"Failed to ban {self.member}.", ephemeral=True)
            except discord.HTTPException as e:
                await interaction.response.send_message(f"HTTPException while banning {self.member}: {e}", ephemeral=True)

        @discord.ui.button(label="Ignore", style=discord.ButtonStyle.success)
        async def ignore_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            try:
                await self.member.edit(timed_out_until=None, reason="Raid Protection: Manual Ignore")  
            except discord.Forbidden:
                await interaction.response.send_message(f"Failed to remove timeout from {self.member}.", ephemeral=True)
                return
            except discord.HTTPException as e:
                await interaction.response.send_message(f"HTTPException while removing timeout from {self.member}: {e}", ephemeral=True)
                return

            roles = self.cog.removed_roles.pop(self.member.id, [])
            try:
                await self.member.add_roles(*roles)
                await asyncio.sleep(2)  
            except discord.Forbidden:
                print(f"Failed to add roles to {self.member} due to missing permissions.")
            except discord.HTTPException as e:
                print(f"HTTPException while adding roles to {self.member}: {e}")
                await asyncio.sleep(10)  

            await interaction.response.send_message(f"Roles restored to {self.member}.", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != GUILD_ID or member.bot:
            return
        if member.id in AUTHORIZED_USER_IDS or member.guild.owner_id == member.id:
            return
        self.join_counts[member.guild.id] += 1
        self.join_times[member.guild.id].append(member.joined_at)

        if self.join_counts[member.guild.id] > 5:  
            inviter = await self.find_inviter(member)
            if inviter:
                await self.timeout_and_remove_roles(inviter, "Mass Join Detected")

                invite_logs = await member.guild.audit_logs(action=discord.AuditLogAction.invite_create, user=inviter, limit=100).flatten()
                for log in invite_logs:
                    try:
                        await log.target.delete(reason="Mass Join Detected")
                    except discord.Forbidden:
                        print(f"Failed to delete invite due to missing permissions.")
                    except discord.HTTPException as e:
                        print(f"HTTPException while deleting invite: {e}")

            for m in self.join_times[member.guild.id]:
                if m.joined_at > datetime.now(timezone.utc) - timedelta(minutes=5):  
                    await self.timeout_and_remove_roles(m, "Mass Join Detected")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or message.guild.id != GUILD_ID or message.author.bot:
            return
        if message.author.id in AUTHORIZED_USER_IDS or message.guild.owner_id == message.author.id:
            return
        if message.channel.id in EXCLUDED_CHANNELS:
            return
        self.message_counts[message.author.id] += 1
        if self.message_counts[message.author.id] > 10:  
            await self.timeout_and_remove_roles(message.author, "Message Spam Detected")

        if len(message.mentions) > 5:  
            self.mention_counts[message.author.id] += 1
            if self.mention_counts[message.author.id] > 3:  
                await self.timeout_and_remove_roles(message.author, "Mention Spam Detected")

    @commands.Cog.listener()
    async def on_webhook_update(self, channel):
        if channel.guild.id != GUILD_ID:
            return
        if len(await channel.webhooks()) > 3:  
            self.webhook_creation_counts[channel.id] += 1
            if self.webhook_creation_counts[channel.id] > 1:  
                for webhook in await channel.webhooks():
                    try:
                        await webhook.delete(reason="Excessive Webhook Creation Detected")
                    except discord.Forbidden:
                        print(f"Failed to delete webhook due to missing permissions.")
                    except discord.HTTPException as e:
                        print(f"HTTPException while deleting webhook: {e}")
                    creator = webhook.user
                    if creator and not creator.bot:
                        await self.timeout_and_remove_roles(creator, "Excessive Webhook Creation Detected")

async def setup(bot):
    await bot.add_cog(RaidProtection(bot))