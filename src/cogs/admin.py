import discord
from discord import app_commands
from discord.ext import commands
from src.utils.logger import get_logger
from datetime import datetime, timedelta

class AdminCommands(commands.Cog):
    """Commandes réservées aux administrateurs"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger(__name__)

    def is_admin():
        """Vérifie si l'utilisateur est un administrateur"""
        async def predicate(interaction: discord.Interaction) -> bool:
            return interaction.user.guild_permissions.administrator
        return app_commands.check(predicate)

    @app_commands.command(name="clean-chats")
    @is_admin()
    async def clean_chats_command(self, interaction: discord.Interaction) -> None:
        """Nettoie les chats privés inutilisés (Admin uniquement)"""
        try:
            category = discord.utils.get(interaction.guild.categories, name="Chats Privés")
            if not category:
                await interaction.response.send_message(
                    "Aucune catégorie de chats privés trouvée.",
                    ephemeral=True
                )
                return

            channels_deleted = 0
            for channel in category.text_channels:
                # Vérifier si le canal est vide depuis 24h
                async for message in channel.history(limit=1):
                    # Si le dernier message date de plus de 24h
                    if (discord.utils.utcnow() - message.created_at).days >= 1:
                        await channel.delete(reason="Canal inactif")
                        channels_deleted += 1

            await interaction.response.send_message(
                f"{channels_deleted} canaux inactifs ont été supprimés.",
                ephemeral=True
            )

        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage des canaux: {e}")
            await interaction.response.send_message(
                "Une erreur est survenue lors du nettoyage des canaux.",
                ephemeral=True
            )

    @app_commands.command(name="list-tokens")
    @is_admin()
    async def list_tokens_command(self, interaction: discord.Interaction) -> None:
        """Liste tous les tokens enregistrés (Admin uniquement)"""
        try:
            async with self.bot.db.pool.acquire() as conn:
                tokens = await conn.fetch("""
                    SELECT 
                        discord_user_id,
                        valid_token,
                        updated_at,
                        created_at
                    FROM user_tokens
                    ORDER BY updated_at DESC
                """)

            if not tokens:
                await interaction.response.send_message(
                    "Aucun token enregistré dans la base de données.",
                    ephemeral=True
                )
                return

            # Créer un message formaté avec les informations sur les tokens
            response = "```\nListe des tokens enregistrés:\n\n"
            response += f"{'Utilisateur':<20} {'Statut':<10} {'Mis à jour':<20} {'Créé le':<20}\n"
            response += "-" * 70 + "\n"

            for token in tokens:
                user = self.bot.get_user(token['discord_user_id'])
                username = user.name if user else f"User {token['discord_user_id']}"
                status = "✅ Valide" if token['valid_token'] else "❌ Invalide"
                updated = token['updated_at'].strftime("%Y-%m-%d %H:%M")
                created = token['created_at'].strftime("%Y-%m-%d %H:%M")
                
                response += f"{username:<20} {status:<10} {updated:<20} {created:<20}\n"

            response += "```"

            await interaction.response.send_message(response, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Erreur lors du listage des tokens: {e}")
            await interaction.response.send_message(
                "Une erreur est survenue lors de la récupération des tokens.",
                ephemeral=True
            )

    @app_commands.command(name="invalidate-all")
    @app_commands.describe(confirmation="Tapez 'CONFIRMER' pour invalider tous les tokens")
    @is_admin()
    async def invalidate_all_command(
        self,
        interaction: discord.Interaction,
        confirmation: str
    ) -> None:
        """Invalide tous les tokens (Admin uniquement)"""
        if confirmation != "CONFIRMER":
            await interaction.response.send_message(
                "Pour invalider tous les tokens, utilisez la commande avec le paramètre confirmation='CONFIRMER'",
                ephemeral=True
            )
            return

        try:
            async with self.bot.db.pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE user_tokens 
                    SET valid_token = false,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE valid_token = true
                """)
                
                # Récupérer le nombre de lignes affectées
                affected = int(result.split()[-1])
                
                await interaction.response.send_message(
                    f"{affected} tokens ont été invalidés avec succès.",
                    ephemeral=True
                )

        except Exception as e:
            self.logger.error(f"Erreur lors de l'invalidation des tokens: {e}")
            await interaction.response.send_message(
                "Une erreur est survenue lors de l'invalidation des tokens.",
                ephemeral=True
            )

    @app_commands.command(name="stats")
    @is_admin()
    async def stats_command(self, interaction: discord.Interaction) -> None:
        """Affiche les statistiques des tokens (Admin uniquement)"""
        try:
            async with self.bot.db.pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_tokens,
                        SUM(CASE WHEN valid_token THEN 1 ELSE 0 END) as valid_tokens,
                        SUM(CASE WHEN NOT valid_token THEN 1 ELSE 0 END) as invalid_tokens,
                        COUNT(DISTINCT discord_user_id) as unique_users,
                        MAX(updated_at) as last_update
                    FROM user_tokens
                """)

                recent_activity = await conn.fetch("""
                    SELECT discord_user_id, updated_at, valid_token
                    FROM user_tokens
                    WHERE updated_at > NOW() - INTERVAL '24 hours'
                    ORDER BY updated_at DESC
                """)

            response = "```\nStatistiques des tokens:\n\n"
            response += f"Total des tokens: {stats['total_tokens']}\n"
            response += f"Tokens valides: {stats['valid_tokens']}\n"
            response += f"Tokens invalides: {stats['invalid_tokens']}\n"
            response += f"Utilisateurs uniques: {stats['unique_users']}\n"
            response += f"Dernière mise à jour: {stats['last_update']}\n\n"

            if recent_activity:
                response += "Activité récente (24h):\n"
                for activity in recent_activity:
                    user = self.bot.get_user(activity['discord_user_id'])
                    username = user.name if user else f"User {activity['discord_user_id']}"
                    status = "✅" if activity['valid_token'] else "❌"
                    time = activity['updated_at'].strftime("%H:%M:%S")
                    response += f"{time} - {status} {username}\n"
            else:
                response += "Aucune activité dans les dernières 24h\n"

            response += "```"

            await interaction.response.send_message(response, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des statistiques: {e}")
            await interaction.response.send_message(
                "Une erreur est survenue lors de la récupération des statistiques.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))