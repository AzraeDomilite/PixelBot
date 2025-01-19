from typing import Optional, Callable
import discord
from discord import app_commands
from discord.ext import commands
from src.utils.logger import get_logger
from src.utils.helpers import is_private_chat
from src.services.token_service import TokenService

# Messages constants
PRIVATE_CHAT_REQUIRED = "Cette commande ne peut être utilisée que dans un chat privé. Utilisez /chat pour créer un chat privé."
TOKEN_UPDATED = "Access token enregistré avec succès."
TOKEN_ERROR = "Une erreur est survenue lors de l'enregistrement de l'access token."
TOKEN_REMOVED = "Les tokens ont été supprimés avec succès."
TOKEN_REMOVE_ERROR = "Une erreur est survenue lors de la suppression des tokens."

class TokenCommands(commands.Cog):
    """Commandes de gestion des tokens d'accès"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger(__name__)
        self.token_service = TokenService(bot.db.pool)

    @app_commands.command(name="token")
    @app_commands.describe(
        token="Le token d'accès à enregistrer",
        refresh_token="Le refresh token à enregistrer"
    )
    async def token_command(
        self,
        interaction: discord.Interaction,
        token: str,
        refresh_token: str
    ) -> None:
        """Commande pour enregistrer les tokens"""
        if not is_private_chat(interaction.channel):
            await interaction.response.send_message(
                PRIVATE_CHAT_REQUIRED,
                ephemeral=True
            )
            return

        try:
            success = await self.token_service.update_tokens(
                discord_user_id=interaction.user.id,
                access_token=token,
                refresh_token=refresh_token
            )
            
            if success:
                await interaction.response.send_message(
                    TOKEN_UPDATED,
                    ephemeral=True
                )
                await interaction.channel.send(
                    f"Tokens mis à jour pour {interaction.user.mention}"
                )
            else:
                await interaction.response.send_message(
                    TOKEN_ERROR,
                    ephemeral=True
                )
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'enregistrement des tokens: {e}")
            await interaction.response.send_message(
                TOKEN_ERROR,
                ephemeral=True
            )

    @app_commands.command(name="remove-token")
    async def remove_token_command(self, interaction: discord.Interaction) -> None:
        """Supprime les tokens de l'utilisateur"""
        if not is_private_chat(interaction.channel):
            await interaction.response.send_message(
                PRIVATE_CHAT_REQUIRED,
                ephemeral=True
            )
            return

        try:
            success = await self.token_service.remove_user_tokens(
                discord_user_id=interaction.user.id
            )
            
            if success:
                await interaction.response.send_message(
                    TOKEN_REMOVED,
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    TOKEN_REMOVE_ERROR,
                    ephemeral=True
                )
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la suppression des tokens: {e}")
            await interaction.response.send_message(
                TOKEN_REMOVE_ERROR,
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(TokenCommands(bot))