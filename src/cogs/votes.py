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
        self.current_vote_number = 1

    def is_admin():
        """Vérifie si l'utilisateur est un administrateur"""
        async def predicate(interaction: discord.Interaction) -> bool:
            return interaction.user.guild_permissions.administrator
        return app_commands.check(predicate)

    @app_commands.command(name="create_vote")
    @app_commands.describe(
        title="Titre du vote",
        image_name="Nom de l'image",
        image="Image à voter",
        json_file="Fichier JSON du pattern",
        coord_x="Coordonnée X top-left",
        coord_z="Coordonnée Z top-left"
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
                "Le fichier doit être un fichier JSON.", ephemeral=True
            )
            return

        try:
            await interaction.response.defer(ephemeral=True)
            # Lire le JSON
            json_content = await json_file.read()
            json_data = json.loads(json_content)

            # Trouver le salon de vote actuel
            vote_channel = discord.utils.get(
                interaction.guild.text_channels,
                name=f"votes-{self.current_vote_number}"
            )
            
            if not vote_channel:
                # Créer un nouveau salon si nécessaire
                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(
                        send_messages=False,
                        read_messages=True,
                        add_reactions=True
                    ),
                    interaction.guild.me: discord.PermissionOverwrite(
                        send_messages=True,
                        read_messages=True,
                        add_reactions=True,
                        manage_messages=True
                    )
                }
                
                vote_channel = await interaction.guild.create_text_channel(
                    f"votes-{self.current_vote_number}",
                    overwrites=overwrites
                )

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

    @app_commands.command(name="end-vote")
    @is_admin()
    async def end_vote(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Récupérer le salon actuel
            current_session = await self.vote_service.get_current_session()
            current_channel = discord.utils.get(
                interaction.guild.text_channels,
                name=f"votes-{current_session}"
            )

            if current_channel:
                # Mise à jour finale des votes
                async with self.bot.db.pool.acquire() as conn:
                    async for message in current_channel.history(limit=None):
                        if message.author == self.bot.user:
                            for reaction in message.reactions:
                                # -1 pour ne pas compter le vote du bot
                                vote_count = reaction.count - 1 if reaction.count > 0 else 0
                                await conn.execute("""
                                    UPDATE votes 
                                    SET vote_count = $1 
                                    WHERE message_id = $2
                                """, vote_count, message.id)

                    # Récupérer le gagnant
                    winner = await self.vote_service.get_winning_vote(conn)
                    
                    if winner and winner['vote_count'] > 0:
                        # Sauvegarder dans votes_pattern
                        await self.vote_service.save_winning_pattern(conn, winner)

                        # Message de victoire dans le salon
                        embed = discord.Embed(
                            title="🏆 Vote terminé - Pattern Gagnant!",
                            description=f"**{winner['title']}** remporte le vote avec **{winner['vote_count']}** votes!",
                            color=discord.Color.gold()
                        )
                        embed.add_field(name="Coordonnées", value=f"X: {winner['coord_x']}, Z: {winner['coord_z']}")
                        embed.set_image(url=winner['image_url'])
                        
                        await current_channel.send(embed=embed)

                    # Désactiver les réactions
                    overwrites = current_channel.overwrites
                    overwrites[interaction.guild.default_role].update(add_reactions=False)
                    await current_channel.edit(overwrites=overwrites)

            # Incrémenter la session et créer nouveau salon
            new_session = await self.vote_service.increment_session()
            new_channel = await self.vote_service.get_or_create_vote_channel(interaction.guild)

            await interaction.followup.send(
                f"Session de vote terminée. Nouvelle session créée dans {new_channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            self.logger.error(f"Erreur lors de la fin de la session de vote: {e}")
            await interaction.followup.send(
                "Une erreur est survenue lors de la fin de la session de vote.",
                ephemeral=True
            )

    async def create_vote_channel(self, guild: discord.Guild, vote_number: int = None) -> discord.TextChannel:
        """Crée un nouveau salon de vote avec les permissions appropriées"""
        if vote_number is None:
            vote_number = await self.vote_service.get_current_vote_number()

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
            f"votes-{vote_number}",
            overwrites=overwrites
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

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(VoteCommands(bot))