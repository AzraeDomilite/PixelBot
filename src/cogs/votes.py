# src/cogs/votes.py
import json
import discord
from discord import app_commands
from discord.ext import commands
from src.utils.logger import get_logger
from src.services.vote_service import VoteService

class VoteCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger(__name__)
        self.vote_service = VoteService(bot, bot.db.pool)

    @app_commands.command(name="create_vote")
    @app_commands.describe(
        title="Titre du vote",
        image_name="Nom de l'image",
        image="Image à voter",
        json_file="Fichier JSON avec les données complémentaires",
        coord_x="Coordonnée X",
        coord_z="Coordonnée Z"
    )
    async def create_vote(
        self,
        interaction: discord.Interaction,
        title: str,
        image_name: str,
        image: discord.Attachment,
        json_file: discord.Attachment,
        coord_x: int,
        coord_z: int
    ) -> None:
        """Crée un nouveau vote avec une image"""
        
        if not image.content_type.startswith('image/'):
            await interaction.response.send_message(
                "Le fichier doit être une image.", ephemeral=True
            )
            return

        if not json_file.filename.endswith('.json'):
            await interaction.response.send_message(
                "Le second fichier doit être un fichier JSON.", ephemeral=True
            )
            return

        try:
            # Lire le JSON
            json_content = await json_file.read()
            json_data = json.loads(json_content)

            await interaction.response.defer()

            # Créer le vote
            result = await self.vote_service.create_vote(
                guild=interaction.guild,
                title=title,
                image_name=image_name,
                image=image,
                json_data=json_data,
                coord_x=coord_x,
                coord_z=coord_z,
                created_by=interaction.user.id
            )

            if result:
                await interaction.followup.send(
                    f"Vote créé avec succès! ID: {result['id']}", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "Une erreur est survenue lors de la création du vote.", ephemeral=True
                )

        except json.JSONDecodeError:
            await interaction.followup.send(
                "Le fichier JSON n'est pas valide.", ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"Erreur lors de la création du vote: {e}")
            await interaction.followup.send(
                "Une erreur inattendue est survenue.", ephemeral=True
            )

    @app_commands.command(name="vote_stats")
    async def vote_stats(self, interaction: discord.Interaction):
        """Affiche les statistiques des votes en cours"""
        async with self.bot.db.pool.acquire() as conn:
            votes = await conn.fetch("""
                SELECT title, vote_count, created_at
                FROM votes
                WHERE is_active = true
                ORDER BY vote_count DESC
            """)

        if not votes:
            await interaction.response.send_message(
                "Aucun vote actif.", ephemeral=True
            )
            return

        embed = discord.Embed(title="Classement des votes", color=discord.Color.blue())
        for i, vote in enumerate(votes, 1):
            embed.add_field(
                name=f"#{i} {vote['title']}", 
                value=f"Votes: {vote['vote_count']}\nCréé le: {vote['created_at'].strftime('%d/%m/%Y')}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(VoteCommands(bot))