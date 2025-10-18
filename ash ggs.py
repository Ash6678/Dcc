Import discord
from discord.ext import commands
from datetime import timedelta
import json
import os
from collections import defaultdict
import time

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

warnings_data = {}
message_tracker = defaultdict(list)
join_tracker = defaultdict(list)
user_message_history = defaultdict(list)

SPAM_THRESHOLD = 5
SPAM_WINDOW = 10
BANNED_WORDS = ['spam', 'badword']

SWEAR_WORDS = [
    'fuck', 'shit', 'bitch', 'ass', 'damn', 'bastard', 'crap',
    'hell', 'dick', 'pussy', 'cock', 'fck', 'fuk', 'sht', 'btch'
]

RAID_JOIN_THRESHOLD = 5
RAID_JOIN_WINDOW = 10

CAPS_THRESHOLD = 0.7
MIN_CAPS_LENGTH = 10

EMOJI_THRESHOLD = 10

BOT_OWNER_ID = None

security_settings = {}

@bot.event
async def on_ready():
    global BOT_OWNER_ID
    app_info = await bot.application_info()
    BOT_OWNER_ID = app_info.owner.id
    
    print(f'✅ Bot is online as {bot.user}')
    print(f'Connected to {len(bot.guilds)} server(s)')
    print(f'Bot Owner: {app_info.owner}')
    print('Ready to moderate!')

@bot.command(name='kick')
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    """Kick a member from the server"""
    if member.top_role >= ctx.author.top_role:
        await ctx.send('❌ You cannot kick this member (higher or equal role)')
        return
    
    await member.kick(reason=reason)
    
    embed = discord.Embed(
        title='Member Kicked',
        description=f'{member.mention} has been kicked',
        color=discord.Color.orange()
    )
    embed.add_field(name='Moderator', value=ctx.author.mention)
    embed.add_field(name='Reason', value=reason or 'No reason provided')
    await ctx.send(embed=embed)

@bot.command(name='ban')
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    """Ban a member from the server"""
    if member.top_role >= ctx.author.top_role:
        await ctx.send('❌ You cannot ban this member (higher or equal role)')
        return
    
    await member.ban(reason=reason)
    
    embed = discord.Embed(
        title='Member Banned',
        description=f'{member.mention} has been banned',
        color=discord.Color.red()
    )
    embed.add_field(name='Moderator', value=ctx.author.mention)
    embed.add_field(name='Reason', value=reason or 'No reason provided')
    await ctx.send(embed=embed)

@bot.command(name='unban')
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    """Unban a user by their ID"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        
        embed = discord.Embed(
            title='Member Unbanned',
            description=f'{user.mention} has been unbanned',
            color=discord.Color.green()
        )
        embed.add_field(name='Moderator', value=ctx.author.mention)
        await ctx.send(embed=embed)
    except discord.NotFound:
        await ctx.send('❌ User not found or not banned')

@bot.command(name='timeout')
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason=None):
    """Timeout a member for specified minutes"""
    if member.top_role >= ctx.author.top_role:
        await ctx.send('❌ You cannot timeout this member (higher or equal role)')
        return
    
    if minutes < 1 or minutes > 40320:
        await ctx.send('❌ Timeout must be between 1 minute and 28 days')
        return
    
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    
    embed = discord.Embed(
        title='Member Timed Out',
        description=f'{member.mention} has been timed out',
        color=discord.Color.blue()
    )
    embed.add_field(name='Duration', value=f'{minutes} minutes')
    embed.add_field(name='Moderator', value=ctx.author.mention)
    embed.add_field(name='Reason', value=reason or 'No reason provided')
    await ctx.send(embed=embed)

@bot.command(name='untimeout')
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    """Remove timeout from a member"""
    await member.timeout(None)
    
    embed = discord.Embed(
        title='Timeout Removed',
        description=f'{member.mention} timeout has been removed',
        color=discord.Color.green()
    )
    embed.add_field(name='Moderator', value=ctx.author.mention)
    await ctx.send(embed=embed)

@bot.command(name='mute')
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    """Mute a member using the 'Muted' role"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    
    if not mute_role:
        await ctx.send('❌ No "Muted" role found. Creating one...')
        mute_role = await ctx.guild.create_role(name="Muted", reason="Auto-created for mute command")
        
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False, speak=False)
    
    if mute_role in member.roles:
        await ctx.send('❌ Member is already muted')
        return
    
    await member.add_roles(mute_role, reason=reason)
    
    embed = discord.Embed(
        title='Member Muted',
        description=f'{member.mention} has been muted',
        color=discord.Color.dark_grey()
    )
    embed.add_field(name='Moderator', value=ctx.author.mention)
    embed.add_field(name='Reason', value=reason or 'No reason provided')
    await ctx.send(embed=embed)

@bot.command(name='unmute')
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    """Unmute a member"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    
    if not mute_role:
        await ctx.send('❌ No "Muted" role found')
        return
    
    if mute_role not in member.roles:
        await ctx.send('❌ Member is not muted')
        return
    
    await member.remove_roles(mute_role)
    
    embed = discord.Embed(
        title='Member Unmuted',
        description=f'{member.mention} has been unmuted',
        color=discord.Color.green()
    )
    embed.add_field(name='Moderator', value=ctx.author.mention)
    await ctx.send(embed=embed)

@bot.command(name='warn')
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason):
    """Warn a member"""
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    
    if guild_id not in warnings_data:
        warnings_data[guild_id] = {}
    
    if user_id not in warnings_data[guild_id]:
        warnings_data[guild_id][user_id] = []
    
    warnings_data[guild_id][user_id].append({
        'reason': reason,
        'moderator': str(ctx.author),
        'timestamp': time.time()
    })
    
    warn_count = len(warnings_data[guild_id][user_id])
    
    embed = discord.Embed(
        title='Member Warned',
        description=f'{member.mention} has been warned',
        color=discord.Color.yellow()
    )
    embed.add_field(name='Total Warnings', value=str(warn_count))
    embed.add_field(name='Moderator', value=ctx.author.mention)
    embed.add_field(name='Reason', value=reason)
    await ctx.send(embed=embed)
    
    if warn_count >= 3:
        await ctx.send(f'⚠️ {member.mention} has reached 3 warnings! Consider taking action.')

@bot.command(name='warnings')
@commands.has_permissions(manage_messages=True)
async def warnings(ctx, member: discord.Member):
    """Check warnings for a member"""
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    
    user_warnings = warnings_data.get(guild_id, {}).get(user_id, [])
    
    if not user_warnings:
        await ctx.send(f'{member.mention} has no warnings.')
        return
    
    embed = discord.Embed(
        title=f'Warnings for {member.display_name}',
        description=f'Total: {len(user_warnings)} warnings',
        color=discord.Color.yellow()
    )
    
    for i, warning in enumerate(user_warnings[-5:], 1):
        embed.add_field(
            name=f'Warning {i}',
            value=f"Reason: {warning['reason']}\nBy: {warning['moderator']}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='clearwarnings')
@commands.has_permissions(administrator=True)
async def clearwarnings(ctx, member: discord.Member):
    """Clear all warnings for a member"""
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    
    if guild_id in warnings_data and user_id in warnings_data[guild_id]:
        warnings_data[guild_id][user_id] = []
        await ctx.send(f'✅ Cleared all warnings for {member.mention}')
    else:
        await ctx.send(f'{member.mention} has no warnings to clear.')

@bot.command(name='purge')
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    """Delete multiple messages"""
    if amount < 1 or amount > 100:
        await ctx.send('❌ Amount must be between 1 and 100')
        return
    
    deleted = await ctx.channel.purge(limit=amount + 1)
    
    msg = await ctx.send(f'🗑️ Deleted {len(deleted) - 1} messages.')
    await msg.delete(delay=3)

@bot.command(name='clear')
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    """Alias for purge command"""
    await purge(ctx, amount)

@bot.command(name='slowmode')
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    """Set slowmode for the channel"""
    if seconds < 0 or seconds > 21600:
        await ctx.send('❌ Slowmode must be between 0 and 21600 seconds (6 hours)')
        return
    
    await ctx.channel.edit(slowmode_delay=seconds)
    
    if seconds == 0:
        await ctx.send('✅ Slowmode disabled')
    else:
        await ctx.send(f'⏱️ Slowmode set to {seconds} seconds')

@bot.command(name='lock')
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    """Lock the channel"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send('🔒 Channel locked')

@bot.command(name='unlock')
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    """Unlock the channel"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
    await ctx.send('🔓 Channel unlocked')

@bot.command(name='lockdown')
@commands.has_permissions(administrator=True)
async def lockdown(ctx):
    """Lock down the entire server (all channels)"""
    import asyncio
    
    confirm_msg = await ctx.send('⚠️ This will lock ALL channels! Type `CONFIRM` within 10 seconds to proceed.')
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content == 'CONFIRM'
    
    try:
        await bot.wait_for('message', check=check, timeout=10.0)
        
        locked_count = 0
        for channel in ctx.guild.channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=False, connect=False)
                locked_count += 1
            except:
                pass
        
        embed = discord.Embed(
            title='🚨 SERVER LOCKDOWN ACTIVATED',
            description=f'All channels have been locked down by {ctx.author.mention}',
            color=discord.Color.red()
        )
        embed.add_field(name='Channels Locked', value=str(locked_count))
        await ctx.send(embed=embed)
        
    except asyncio.TimeoutError:
        await ctx.send('❌ Lockdown cancelled.')

@bot.command(name='unlockdown')
@commands.has_permissions(administrator=True)
async def unlockdown(ctx):
    """Remove server-wide lockdown"""
    unlocked_count = 0
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=None, connect=None)
            unlocked_count += 1
        except:
            pass
    
    embed = discord.Embed(
        title='✅ SERVER LOCKDOWN REMOVED',
        description=f'All channels have been unlocked by {ctx.author.mention}',
        color=discord.Color.green()
    )
    embed.add_field(name='Channels Unlocked', value=str(unlocked_count))
    await ctx.send(embed=embed)

@bot.command(name='security')
async def security(ctx, setting: str = None, value: str = None):
    """Configure server security settings"""
    if not (is_bot_or_server_owner(ctx) or ctx.author.guild_permissions.administrator):
        await ctx.send('❌ You need Administrator permissions or be the bot/server owner to use this command.')
        return
    
    guild_id = str(ctx.guild.id)
    
    if guild_id not in security_settings:
        security_settings[guild_id] = {
            'anti_invite': True,
            'anti_link': True,
            'anti_caps': True,
            'anti_emoji_spam': True,
            'anti_mention_spam': True,
            'anti_raid': True
        }
    
    if setting is None:
        embed = discord.Embed(
            title='🔒 Security Settings',
            description='Current server security configuration',
            color=discord.Color.blue()
        )
        
        for key, val in security_settings[guild_id].items():
            status = '✅ Enabled' if val else '❌ Disabled'
            embed.add_field(name=key.replace('_', ' ').title(), value=status, inline=True)
        
        embed.set_footer(text='Use !security <setting> <on/off> to change')
        await ctx.send(embed=embed)
        return
    
    if value and value.lower() in ['on', 'off', 'true', 'false', 'enable', 'disable']:
        is_enabled = value.lower() in ['on', 'true', 'enable']
        
        if setting in security_settings[guild_id]:
            security_settings[guild_id][setting] = is_enabled
            status = '✅ enabled' if is_enabled else '❌ disabled'
            await ctx.send(f'Security setting `{setting}` has been {status}')
        else:
            await ctx.send(f'❌ Unknown setting. Available: {", ".join(security_settings[guild_id].keys())}')
    else:
        await ctx.send('❌ Usage: `!security <setting> <on/off>`')

@bot.command(name='nuke')
@commands.check(lambda ctx: ctx.author.id == BOT_OWNER_ID or ctx.author.id == ctx.guild.owner_id)
async def nuke(ctx):
    """Clone and delete the channel (removes all messages) - BOT/SERVER OWNER ONLY"""
    import random
    import asyncio
    
    confirmation_code = ''.join(random.choices('0123456789', k=4))
    
    warning_embed = discord.Embed(
        title='⚠️ CHANNEL NUKE WARNING',
        description='This will **DELETE** this entire channel and all its messages!',
        color=discord.Color.red()
    )
    warning_embed.add_field(
        name='Are you absolutely sure?',
        value=f'Type `{confirmation_code}` within 30 seconds to confirm.\nType anything else to cancel.',
        inline=False
    )
    warning_embed.set_footer(text='This action cannot be undone!')
    
    await ctx.send(embed=warning_embed)
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
        
        if msg.content == confirmation_code:
            await ctx.send('💥 Nuking channel in 3 seconds...')
            await asyncio.sleep(3)
            
            channel_position = ctx.channel.position
            new_channel = await ctx.channel.clone(reason=f"Nuked by {ctx.author}")
            await ctx.channel.delete()
            await new_channel.edit(position=channel_position)
            
            nuke_embed = discord.Embed(
                title='💥 Channel Nuked',
                description=f'Channel nuked by {ctx.author.mention}',
                color=discord.Color.red()
            )
            await new_channel.send(embed=nuke_embed)
        else:
            await ctx.send('❌ Nuke cancelled - incorrect confirmation code.')
    
    except asyncio.TimeoutError:
        await ctx.send('❌ Nuke cancelled - confirmation timeout.')

@bot.command(name='serverinfo')
async def serverinfo(ctx):
    """Display server information"""
    guild = ctx.guild
    
    embed = discord.Embed(
        title=guild.name,
        description=f'Server ID: {guild.id}',
        color=discord.Color.blue()
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name='Owner', value=guild.owner.mention)
    embed.add_field(name='Members', value=guild.member_count)
    embed.add_field(name='Channels', value=len(guild.channels))
    embed.add_field(name='Roles', value=len(guild.roles))
    embed.add_field(name='Created', value=guild.created_at.strftime('%Y-%m-%d'))
    
    await ctx.send(embed=embed)

@bot.command(name='userinfo')
async def userinfo(ctx, member: discord.Member = None):
    """Display user information"""
    target_member = member if member is not None else ctx.author
    
    embed = discord.Embed(
        title=f'{target_member.display_name}',
        description=f'User ID: {target_member.id}',
        color=target_member.color
    )
    
    embed.set_thumbnail(url=target_member.avatar.url if target_member.avatar else target_member.default_avatar.url)
    embed.add_field(name='Username', value=str(target_member))
    embed.add_field(name='Nickname', value=target_member.nick or 'None')
    
    joined_date = target_member.joined_at.strftime('%Y-%m-%d') if target_member.joined_at else 'Unknown'
    embed.add_field(name='Joined Server', value=joined_date)
    embed.add_field(name='Account Created', value=target_member.created_at.strftime('%Y-%m-%d'))
    embed.add_field(name='Top Role', value=target_member.top_role.mention)
    
    await ctx.send(embed=embed)

@bot.command(name='show')
async def show(ctx):
    """Display bot statistics and information"""
    guild = ctx.guild
    
    total_warnings = sum(len(warnings) for warnings in warnings_data.get(str(guild.id), {}).values())
    
    total_members = guild.member_count
    bot_count = sum(1 for member in guild.members if member.bot)
    human_count = total_members - bot_count
    
    embed = discord.Embed(
        title=f'🤖 Bot Status - {bot.user.name}',
        description='Current bot statistics and server information',
        color=discord.Color.blue()
    )
    
    if bot.user.avatar:
        embed.set_thumbnail(url=bot.user.avatar.url)
    
    bot_info = f"""
    **Bot:** {bot.user.mention}
    **Latency:** {round(bot.latency * 1000)}ms
    **Servers:** {len(bot.guilds)}
    **Prefix:** `!`
    """
    
    server_stats = f"""
    **Total Members:** {total_members}
    **Humans:** {human_count}
    **Bots:** {bot_count}
    **Roles:** {len(guild.roles)}
    **Channels:** {len(guild.channels)}
    """
    
    mod_stats = f"""
    **Total Warnings:** {total_warnings}
    **Banned Words:** {len(BANNED_WORDS)}
    **Spam Protection:** Active
    """
    
    embed.add_field(name='📊 Bot Information', value=bot_info, inline=False)
    embed.add_field(name='📈 Server Statistics', value=server_stats, inline=False)
    embed.add_field(name='🛡️ Moderation Stats', value=mod_stats, inline=False)
    
    embed.set_footer(text=f'Requested by {ctx.author}')
    
    await ctx.send(embed=embed)

def is_bot_or_server_owner(ctx):
    """Check if user is bot owner or server owner"""
    return ctx.author.id == BOT_OWNER_ID or ctx.author.id == ctx.guild.owner_id

@bot.command(name='help', aliases=['ggs'])
async def help_command(ctx):
    """Display all available commands"""
    embed = discord.Embed(
        title='🤖 Moderation Bot Commands',
        description='All available moderation commands\nUse `!help` or `!ggs` to see this menu',
        color=discord.Color.purple()
    )
    
    moderation = """
    `!kick @member [reason]` - Kick a member
    `!ban @member [reason]` - Ban a member
    `!unban <user_id>` - Unban a user
    `!timeout @member <minutes> [reason]` - Timeout a member
    `!untimeout @member` - Remove timeout
    `!mute @member [reason]` - Mute a member
    `!unmute @member` - Unmute a member
    """
    
    warnings = """
    `!warn @member <reason>` - Warn a member
    `!warnings @member` - View member warnings
    `!clearwarnings @member` - Clear warnings (Admin)
    """
    
    messages = """
    `!purge <amount>` - Delete messages (1-100)
    `!clear <amount>` - Same as purge
    `!nuke` - Clone and delete channel (Owner Only + Confirmation)
    """
    
    channel = """
    `!slowmode <seconds>` - Set slowmode (0-21600)
    `!lock` - Lock channel
    `!unlock` - Unlock channel
    `!lockdown` - Lock entire server (Admin + Confirmation)
    `!unlockdown` - Remove server lockdown (Admin)
    """
    
    security = """
    `!security` - View security settings
    `!security <setting> <on/off>` - Toggle security feature
    Available: anti_invite, anti_link, anti_caps, anti_emoji_spam, anti_mention_spam, anti_raid
    """
    
    info = """
    `!show` - Bot statistics and status
    `!serverinfo` - Server information
    `!userinfo [@member]` - User information
    `!help` or `!ggs` - Show this message
    """
    
    embed.add_field(name='👮 Moderation', value=moderation, inline=False)
    embed.add_field(name='⚠️ Warnings', value=warnings, inline=False)
    embed.add_field(name='💬 Messages', value=messages, inline=False)
    embed.add_field(name='🔧 Channel', value=channel, inline=False)
    embed.add_field(name='🔒 Security', value=security, inline=False)
    embed.add_field(name='ℹ️ Information', value=info, inline=False)
    
    owner_perms = ""
    if is_bot_or_server_owner(ctx):
        owner_perms = "✨ **You have full access** (Bot Owner or Server Owner)"
        embed.set_footer(text=owner_perms)
    
    await ctx.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    guild_id = str(message.guild.id) if message.guild else None
    if not guild_id:
        return
    
    if guild_id not in security_settings:
        security_settings[guild_id] = {
            'anti_invite': True,
            'anti_link': True,
            'anti_caps': True,
            'anti_emoji_spam': True,
            'anti_mention_spam': True,
            'anti_raid': True
        }
    
    settings = security_settings[guild_id]
    content_lower = message.content.lower()
    
    if any(word in content_lower for word in BANNED_WORDS):
        await message.delete()
        await message.channel.send(
            f'⚠️ {message.author.mention}, your message contained prohibited content.',
            delete_after=5
        )
        return
    
    if any(swear in content_lower for swear in SWEAR_WORDS):
        await message.delete()
        try:
            await message.author.timeout(timedelta(seconds=20), reason="Swearing/profanity")
            await message.channel.send(
                f'🚫 {message.author.mention}, no swearing allowed! You have been timed out for 20 seconds.',
                delete_after=5
            )
        except:
            await message.channel.send(
                f'⚠️ {message.author.mention}, no swearing allowed!',
                delete_after=5
            )
        return
    
    if settings['anti_invite']:
        import re
        invite_pattern = r'(discord\.gg|discord\.com/invite|discordapp\.com/invite)/[a-zA-Z0-9]+'
        if re.search(invite_pattern, message.content):
            await message.delete()
            await message.channel.send(
                f'🚫 {message.author.mention}, Discord invite links are not allowed!',
                delete_after=5
            )
            return
    
    if settings['anti_link']:
        import re
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        if re.search(url_pattern, message.content) and not message.author.guild_permissions.manage_messages:
            await message.delete()
            await message.channel.send(
                f'🚫 {message.author.mention}, links are not allowed! (Moderators can post links)',
                delete_after=5
            )
            return
    
    if settings['anti_mention_spam']:
        if message.mention_everyone or len(message.mentions) > 5:
            await message.delete()
            try:
                await message.author.timeout(timedelta(minutes=10), reason="Mention spam")
                await message.channel.send(
                    f'🚫 {message.author.mention} has been timed out for mention spam!',
                    delete_after=5
                )
            except:
                pass
            return
    
    if settings['anti_caps'] and len(message.content) >= MIN_CAPS_LENGTH:
        caps_count = sum(1 for c in message.content if c.isupper())
        if caps_count / len(message.content) >= CAPS_THRESHOLD:
            await message.delete()
            await message.channel.send(
                f'⚠️ {message.author.mention}, please don\'t use excessive caps!',
                delete_after=5
            )
            return
    
    if settings['anti_emoji_spam']:
        import re
        emojis = re.findall(r'<:[a-zA-Z0-9_]+:[0-9]+>|[\U00010000-\U0010ffff]', message.content)
        if len(emojis) > EMOJI_THRESHOLD:
            await message.delete()
            await message.channel.send(
                f'⚠️ {message.author.mention}, please don\'t spam emojis!',
                delete_after=5
            )
            return
    
    user_id = message.author.id
    current_time = time.time()
    
    user_message_history[user_id].append(message.content)
    if len(user_message_history[user_id]) > 10:
        user_message_history[user_id].pop(0)
    
    if len(user_message_history[user_id]) >= 3:
        if user_message_history[user_id][-1] == user_message_history[user_id][-2] == user_message_history[user_id][-3]:
            await message.delete()
            await message.channel.send(
                f'⚠️ {message.author.mention}, please don\'t repeat the same message!',
                delete_after=5
            )
            return
    
    message_tracker[user_id].append(current_time)
    message_tracker[user_id] = [
        t for t in message_tracker[user_id] 
        if current_time - t < SPAM_WINDOW
    ]
    
    if len(message_tracker[user_id]) >= SPAM_THRESHOLD:
        try:
            await message.author.timeout(timedelta(minutes=5), reason="Message spam detected")
            await message.channel.send(
                f'🚫 {message.author.mention} has been timed out for 5 minutes (spam detected).',
                delete_after=5
            )
            message_tracker[user_id].clear()
        except:
            pass
    
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    """Welcome new members and detect raids"""
    guild_id = str(member.guild.id)
    
    if guild_id not in security_settings:
        security_settings[guild_id] = {
            'anti_invite': True,
            'anti_link': True,
            'anti_caps': True,
            'anti_emoji_spam': True,
            'anti_mention_spam': True,
            'anti_raid': True
        }
    
    if security_settings[guild_id]['anti_raid']:
        current_time = time.time()
        join_tracker[guild_id].append(current_time)
        join_tracker[guild_id] = [
            t for t in join_tracker[guild_id] 
            if current_time - t < RAID_JOIN_WINDOW
        ]
        
        if len(join_tracker[guild_id]) >= RAID_JOIN_THRESHOLD:
            log_channel = discord.utils.get(member.guild.channels, name='mod-logs')
            if log_channel:
                embed = discord.Embed(
                    title='🚨 POSSIBLE RAID DETECTED',
                    description=f'{RAID_JOIN_THRESHOLD}+ members joined in {RAID_JOIN_WINDOW} seconds!',
                    color=discord.Color.red()
                )
                embed.add_field(name='Latest Join', value=member.mention)
                embed.add_field(name='Action Recommended', value='Consider using `!lockdown` to prevent further joins')
                await log_channel.send(embed=embed)
    
    channel = discord.utils.get(member.guild.channels, name='general')
    if channel:
        embed = discord.Embed(
            title='Welcome!',
            description=f'Welcome to the server, {member.mention}!',
            color=discord.Color.green()
        )
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    """Log member leaves"""
    log_channel = discord.utils.get(member.guild.channels, name='mod-logs')
    if log_channel:
        embed = discord.Embed(
            title='Member Left',
            description=f'{member.mention} has left the server',
            color=discord.Color.red()
        )
        await log_channel.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ You do not have permission to use this command.')
    elif isinstance(error, commands.CheckFailure):
        if ctx.command and ctx.command.name == 'nuke':
            await ctx.send('❌ Only the **server owner** can use the nuke command!')
        else:
            await ctx.send('❌ You do not have permission to use this command.')
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send('❌ Member not found.')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'❌ Missing required argument. Use `!help` for command usage.')
    elif isinstance(error, commands.BadArgument):
        await ctx.send('❌ Invalid argument provided.')
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f'Error: {error}')

if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        print('❌ ERROR: DISCORD_BOT_TOKEN not found in environment variables!')
        print('Please add your Discord bot token to the Secrets.')
    else:
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f'❌ Failed to start bot: {e}')
