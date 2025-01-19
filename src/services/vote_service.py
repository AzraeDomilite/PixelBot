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

    async def create_vote(self, guild: discord.Guild, title: str, image_name: str, image: discord.Attachment, json_data: dict, coord_x: int, coord_z: int, created_by: int) -> Optional[dict]:
        try:
            # Vérifier/créer le salon de vote
            vote_channel = discord.utils.get(guild.text_channels, name="votes")
            if not vote_channel:
                vote_channel = await guild.create_text_channel("votes")

            # Sauvegarder l'image
            image_url = image.url

            # Créer l'embed avec le nom de l'image
            embed = discord.Embed(title=title, color=discord.Color.blue())
            embed.add_field(name="Image", value=image_name, inline=False)
            embed.set_image(url=image_url)
            embed.add_field(name="Coordonnées", value=f"X: {coord_x}, Z: {coord_z}", inline=False)
            message = await vote_channel.send(embed=embed)
            await message.add_reaction("✅")

            # Convertir le dictionnaire json_data en chaîne JSON
            json_str = json.dumps(json_data)

            # Sauvegarder en base avec le nom de l'image
            async with self.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                    INSERT INTO votes (title, image_name, image_url, json_data, channel_id, message_id, created_by, coord_x, coord_z)
                    VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)
                    RETURNING id
                """, title, image_name, image_url, json_str, vote_channel.id, message.id, created_by, coord_x, coord_z)
                
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