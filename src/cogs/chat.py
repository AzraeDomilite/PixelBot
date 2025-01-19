import discord
from discord import app_commands
from discord.ext import commands
from src.utils.logger import get_logger
from src.utils.helpers import (
    is_private_chat,
    create_private_channel,
    get_private_category
)

class ChatCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger(__name__)

    @app_commands.command(name="chat")
    async def chat_command(self, interaction: discord.Interaction) -> None:
        """Crée un chat privé pour l'utilisateur"""
        try:
            guild = interaction.guild
            member = interaction.user

            # Vérifier si l'utilisateur a déjà un chat privé
            category = await get_private_category(guild)
            if category:
                for channel in category.text_channels:
                    if channel.permissions_for(member).read_messages:
                        await interaction.response.send_message(
                            f"Vous avez déjà un canal privé : {channel.mention}",
                            ephemeral=True
                        )
                        return

            # Créer un nouveau canal privé
            channel = await create_private_channel(
                guild=guild,
                member=member,
                bot_member=guild.me
            )

            if channel:
                welcome_message = (
                    f"Bienvenue dans votre chat privé, {member.mention} !\n"
                    "Ce canal n'est visible que par vous et le bot.\n"
                    "Commandes disponibles :\n"
                    "• `/token <access_token>` - Enregistrer un access token\n"
                    "• `/view-tokens` - Voir vos tokens enregistrés et leur status\n"
                    "• `/remove-token` - Supprimer vos tokens"
                )
                await channel.send(welcome_message)

                await interaction.response.send_message(
                    f"J'ai créé un canal privé pour vous : {channel.mention}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Je n'ai pas pu créer de canal privé. Vérifiez mes permissions.",
                    ephemeral=True
                )

        except discord.Forbidden:
            await interaction.response.send_message(
                "Je n'ai pas les permissions nécessaires pour créer un canal.",
                ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"Erreur lors de la création du canal: {e}")
            await interaction.response.send_message(
                "Une erreur est survenue lors de la création du canal.",
                ephemeral=True
            )

    @app_commands.command(name="close")
    async def close_command(self, interaction: discord.Interaction) -> None:
        """Ferme le chat privé actuel"""
        if not is_private_chat(interaction.channel):
            await interaction.response.send_message(
                "Cette commande ne peut être utilisée que dans un chat privé.",
                ephemeral=True
            )
            return

        try:
            channel = interaction.channel
            await interaction.response.send_message(
                "Fermeture du canal dans 5 secondes...",
                ephemeral=True
            )
            await channel.delete(reason="Canal fermé par l'utilisateur")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "Je n'ai pas la permission de supprimer ce canal.",
                ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"Erreur lors de la fermeture du canal: {e}")
            await interaction.response.send_message(
                "Une erreur est survenue lors de la fermeture du canal.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(ChatCommands(bot))