import json
from typing import Optional
import discord
from discord.ext import tasks
from src.utils.logger import get_logger

class VoteService:
    def __init__(self, bot, db_pool):
        self.bot = bot
        self.db_pool = db_pool
        self.logger = get_logger(__name__)
        self.update_vote_counts.start()

    async def get_current_vote_number(self) -> int:
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT value->>'number'
                FROM bot_state
                WHERE key = 'vote_number'
            """)
            return int(result) if result else 1

    async def increment_vote_number(self) -> int:
        async with self.db_pool.acquire() as conn:
            new_number = await conn.fetchval("""
                UPDATE bot_state
                SET value = jsonb_build_object('number', (value->>'number')::int + 1)
                WHERE key = 'vote_number'
                RETURNING (value->>'number')::int
            """)
            return new_number

    async def get_or_create_vote_channel(self, guild: discord.Guild) -> discord.TextChannel:
        """Récupère ou crée le salon de vote pour la session actuelle"""
        session = await self.get_current_session()
        
        # Vérifier si le salon existe déjà
        vote_channel = discord.utils.get(
            guild.text_channels,
            name=f"votes-{session}"
        )
        
        if not vote_channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    send_messages=False,
                    read_messages=True,
                    add_reactions=True
                ),
                guild.me: discord.PermissionOverwrite(
                    send_messages=True,
                    read_messages=True,
                    add_reactions=True,
                    manage_messages=True
                )
            }
            vote_channel = await guild.create_text_channel(
                f"votes-{session}",
                overwrites=overwrites
            )
        
        return vote_channel

    async def create_vote(self, guild: discord.Guild, title: str, image_name: str, 
                         image: discord.Attachment, json_data: dict, coord_x: int, 
                         coord_z: int, created_by: int) -> Optional[dict]:
        try:
            session_id = await self.get_current_session_id()
            vote_channel = await self.get_or_create_vote_channel(guild)
            
            # Créer l'embed et envoyer le message
            embed = discord.Embed(title=title, color=discord.Color.blue())
            embed.add_field(name="Image", value=image_name, inline=False)
            embed.set_image(url=image.url)
            embed.add_field(name="Coordonnées", value=f"X: {coord_x}, Z: {coord_z}", inline=False)
            message = await vote_channel.send(embed=embed)
            await message.add_reaction("✅")

            # Sauvegarder en base
            async with self.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                    INSERT INTO votes (
                        title, image_name, image_url, json_data, 
                        channel_id, message_id, created_by,
                        coord_x, coord_z, session_id
                    )
                    VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10)
                    RETURNING id
                """, title, image_name, image.url, json.dumps(json_data),
                    vote_channel.id, message.id, created_by,
                    coord_x, coord_z, session_id)
                
            return {"id": record['id'], "channel_id": vote_channel.id, "message_id": message.id}

        except Exception as e:
            self.logger.error(f"Erreur lors de la création du vote: {e}")
            return None

    @tasks.loop(minutes=5.0)
    async def update_vote_counts(self):
        try:
            async with self.db_pool.acquire() as conn:
                active_votes = await conn.fetch("""
                    SELECT id, channel_id, message_id 
                    FROM votes 
                    WHERE is_active = true
                """)

                for vote in active_votes:
                    channel = self.bot.get_channel(vote['channel_id'])
                    if channel:
                        try:
                            message = await channel.fetch_message(vote['message_id'])
                            reaction = discord.utils.get(message.reactions, emoji="✅")
                            vote_count = reaction.count - 1 if reaction else 0

                            await conn.execute("""
                                UPDATE votes 
                                SET vote_count = $1, updated_at = CURRENT_TIMESTAMP
                                WHERE id = $2
                            """, vote_count, vote['id'])

                        except discord.NotFound:
                            continue

        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour des votes: {e}")

    @update_vote_counts.before_loop
    async def before_update_vote_counts(self):
        await self.bot.wait_until_ready()

    async def get_winning_vote(self, conn) -> Optional[dict]:
        """Récupère le vote gagnant de la session active"""
        try:
            winner = await conn.fetchrow("""
                SELECT id, title, image_name, image_url, json_data, 
                       coord_x, coord_z, vote_count
                FROM votes 
                WHERE is_active = true 
                ORDER BY vote_count DESC 
                LIMIT 1
            """)
            return winner
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération du gagnant: {e}")
            return None

    async def save_winning_pattern(self, conn, winner: dict) -> bool:
        """Sauvegarde le pattern gagnant"""
        try:
            await conn.execute("""
                INSERT INTO votes_pattern (
                    title, image_name, image_url, json_data,
                    coord_x, coord_z, vote_count, original_vote_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, winner['title'], winner['image_name'], 
                winner['image_url'], winner['json_data'],
                winner['coord_x'], winner['coord_z'], 
                winner['vote_count'], winner['id'])
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde du pattern: {e}")
            return False

    async def get_current_session(self) -> int:
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT (value->>'number')::int
                FROM bot_state
                WHERE key = 'vote_session'
            """)
            return result or 1

    async def increment_session(self) -> int:
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval("""
                UPDATE bot_state
                SET value = jsonb_build_object('number', (value->>'number')::int + 1)
                WHERE key = 'vote_session'
                RETURNING (value->>'number')::int
            """)
            return result

    async def create_vote_channel(self, guild: discord.Guild) -> discord.TextChannel:
        session = await self.get_current_session()
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                send_messages=False,
                read_messages=True,
                add_reactions=True
            ),
            guild.me: discord.PermissionOverwrite(
                send_messages=True,
                read_messages=True,
                add_reactions=True,
                manage_messages=True
            )
        }
        return await guild.create_text_channel(
            f"votes-{session}",
            overwrites=overwrites
        )

    async def get_current_session_id(self) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval("""
                SELECT id FROM vote_sessions
                WHERE is_active = true
                ORDER BY id DESC LIMIT 1
            """)

    async def create_new_session(self) -> int:
        async with self.db_pool.acquire() as conn:
            # Désactiver l'ancienne session
            await conn.execute("""
                UPDATE vote_sessions SET is_active = false
                WHERE is_active = true
            """)
            
            # Créer nouvelle session
            return await conn.fetchval("""
                INSERT INTO vote_sessions (number, is_active)
                SELECT COALESCE(MAX(number), 0) + 1, true
                FROM vote_sessions
                RETURNING id
            """)