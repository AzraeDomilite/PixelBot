import os
from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands
from src.database import Database
from src.utils.logger import get_logger
from src.utils.config import Config


class PixelBot(commands.Bot):
    """Classe principale du bot Discord"""
    
    def __init__(self, config: Config):
        # Configuration des intents Discord
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.guild_messages = True
        intents.dm_messages = True
        
        # Initialisation du bot parent
        super().__init__(
            command_prefix=config.bot.prefix,
            description=config.bot.description,
            intents=intents
        )
        
        # Configuration initiale
        self.config = config
        self.logger = get_logger(__name__)
        self.db: Optional[Database] = None

    async def setup_hook(self) -> None:
        """Configuration initiale du bot"""
        self.logger.info("Initializing bot...")
        
        try:
            # Initialiser la base de données
            self.db = await Database.create(self.config)
            self.logger.info("Database initialized successfully")
            
            # Charger les extensions
            await self.load_extensions()
            self.logger.info("Extensions loaded successfully")
        except Exception as e:
            self.logger.error(f"Error during bot initialization: {e}")
            raise

    async def on_ready(self) -> None:
        """Événement appelé quand le bot est prêt"""
        self.logger.info(f"Logged in as {self.user.name} ({self.user.id})")
        
        # Configurer l'activité du bot
        activity = discord.Game(name=self.config.bot.activity_name)
        await self.change_presence(activity=activity)
        
        # Afficher les informations sur les serveurs
        guilds = [f"- {guild.name} (ID: {guild.id})" for guild in self.guilds]
        self.logger.info(f"Connected to {len(guilds)} guilds:\n" + "\n".join(guilds))
        
        # Synchroniser les commandes slash
        try:
            synced = await self.tree.sync()
            self.logger.info(f"Slash commands synchronized: {len(synced)} commands")
        except Exception as e:
            self.logger.error(f"Failed to sync slash commands: {e}")

    async def load_extensions(self) -> None:
        """Charge toutes les extensions (cogs) du bot"""
        try:
            extensions = [
                "src.cogs.tokens",
                "src.cogs.chat",
                "src.cogs.admin",
                "src.cogs.votes"
            ]
            
            for extension in extensions:
                try:
                    await self.load_extension(extension)
                    self.logger.info(f"Loaded extension: {extension}")
                except Exception as e:
                    self.logger.error(
                        f"Failed to load extension {extension}: {e}",
                        exc_info=True
                    )
        except Exception as e:
            self.logger.error(f"Error loading extensions: {e}")
            raise

    async def close(self) -> None:
        """Nettoyage lors de la fermeture du bot"""
        self.logger.info("Shutting down bot...")
        try:
            if self.db and hasattr(self.db, 'close'):
                await self.db.close()
                self.logger.info("Database connection closed")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        finally:
            await super().close()

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """Gestionnaire global des erreurs d'événements"""
        self.logger.error(
            f"Error in {event_method}",
            exc_info=True,
            extra={
                'args': args,
                'kwargs': kwargs
            }
        )

    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError
    ) -> None:
        """Gestionnaire global des erreurs de commandes"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "❌ Vous n'avez pas la permission d'utiliser cette commande.",
                delete_after=10
            )
            return
            
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send(
                "❌ Cette commande ne peut pas être utilisée en message privé.",
                delete_after=10
            )
            return
        
        # Log les autres erreurs
        self.logger.error(
            f"Command error in {ctx.command}: {error}",
            exc_info=error
        )
        
        # Informer l'utilisateur
        await ctx.send(
            "❌ Une erreur est survenue lors de l'exécution de la commande. "
            "Les administrateurs ont été informés.",
            delete_after=10
        )

    async def on_application_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        """Gestionnaire d'erreurs pour les commandes slash"""
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original

        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "❌ Vous n'avez pas la permission d'utiliser cette commande.",
                ephemeral=True
            )
            return

        # Log les autres erreurs
        self.logger.error(
            f"Slash command error in {interaction.command}: {error}",
            exc_info=error
        )
        
        # Informer l'utilisateur
        try:
            await interaction.response.send_message(
                "❌ Une erreur est survenue lors de l'exécution de la commande. "
                "Les administrateurs ont été informés.",
                ephemeral=True
            )
        except:
            # Si la réponse a déjà été envoyée
            await interaction.followup.send(
                "❌ Une erreur est survenue lors de l'exécution de la commande. "
                "Les administrateurs ont été informés.",
                ephemeral=True
            )

    @property
    def is_ready_and_db_connected(self) -> bool:
        """Vérifie si le bot est prêt et connecté à la base de données"""
        return self.is_ready() and self.db is not None