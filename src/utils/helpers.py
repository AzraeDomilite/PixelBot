import re
from typing import Optional
import discord
from discord.ext import commands

def normalize_channel_name(name: str) -> str:
    """Normalise le nom d'un canal en retirant les caractères spéciaux"""
    name = name.lower().replace(' ', '-')
    name = re.sub(r'[^a-z0-9-]', '', name)
    name = re.sub(r'-+', '-', name)
    return name

def is_private_chat(channel: discord.TextChannel) -> bool:
    """Vérifie si le canal est un chat privé créé par le bot"""
    return (
        isinstance(channel, discord.TextChannel) and
        channel.category and
        channel.category.name == "Chats Privés" and
        channel.name.startswith("chat-")
    )

async def get_private_category(guild: discord.Guild) -> discord.CategoryChannel:
    """Obtient ou crée la catégorie des chats privés"""
    category = discord.utils.get(guild.categories, name="Chats Privés")
    if not category:
        category = await guild.create_category("Chats Privés")
    return category

async def create_private_channel(
    guild: discord.Guild,
    member: discord.Member,
    bot_member: discord.Member
) -> Optional[discord.TextChannel]:
    """Crée un canal privé pour un membre"""
    try:
        category = await get_private_category(guild)
        channel_name = f"chat-{normalize_channel_name(member.display_name)}"
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            bot_member: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )
        
        return channel
    except discord.Forbidden:
        return None
    except Exception as e:
        print(f"Erreur lors de la création du canal : {e}")
        return None