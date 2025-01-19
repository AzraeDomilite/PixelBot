import pytest
import discord
import asyncio
from unittest.mock import Mock, AsyncMock
from src.services.vote_service import VoteService
from src.cogs.votes import VoteCommands
from src.services.token_service import TokenService

@pytest.fixture
async def mock_bot():
    bot = Mock()
    bot.db = Mock()
    bot.db.pool = Mock()
    bot.db.pool.acquire = AsyncMock()
    return bot

@pytest.fixture
async def mock_guild():
    guild = Mock(spec=discord.Guild)
    guild.text_channels = []
    guild.create_text_channel = AsyncMock()
    return guild

@pytest.fixture
async def mock_vote_service(mock_bot):
    return VoteService(mock_bot, mock_bot.db.pool)

@pytest.mark.asyncio
async def test_create_vote(mock_bot, mock_guild, mock_vote_service):
    # Préparer les données de test
    title = "Test Vote"
    image_name = "test_image.png"
    image = Mock(spec=discord.Attachment)
    image.url = "http://test.com/image.png"
    json_data = {"width": 42, "height": 30}
    coord_x = 100
    coord_z = 200
    created_by = 123456789

    # Configurer le mock du channel
    mock_channel = Mock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock(return_value=Mock(id=1))
    mock_guild.create_text_channel.return_value = mock_channel

    # Configurer le mock de la base de données
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={"id": 1})
    mock_bot.db.pool.acquire.return_value.__aenter__.return_value = mock_conn

    # Exécuter le test
    result = await mock_vote_service.create_vote(
        mock_guild, title, image_name, image, json_data,
        coord_x, coord_z, created_by
    )

    # Vérifier les résultats
    assert result is not None
    assert result["id"] == 1
    mock_guild.create_text_channel.assert_called_once_with("votes")
    mock_channel.send.assert_called_once()

@pytest.mark.asyncio
async def test_vote_stats(mock_bot):
    # Préparer les données de mock
    mock_votes = [
        {
            "title": "Vote 1",
            "vote_count": 5,
            "created_at": "2024-01-19 12:00:00"
        },
        {
            "title": "Vote 2",
            "vote_count": 3,
            "created_at": "2024-01-19 13:00:00"
        }
    ]

    # Configurer le mock de la base de données
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=mock_votes)
    mock_bot.db.pool.acquire.return_value.__aenter__.return_value = mock_conn

    # Créer une instance de VoteCommands
    cog = VoteCommands(mock_bot)

    # Créer un mock pour l'interaction Discord
    interaction = Mock(spec=discord.Interaction)
    interaction.response = Mock()
    interaction.response.send_message = AsyncMock()

    # Exécuter le test
    await cog.vote_stats(interaction)

    # Vérifier que la réponse a été envoyée
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert kwargs["ephemeral"] is True
    assert isinstance(kwargs["embed"], discord.Embed)

@pytest.mark.asyncio
async def test_update_vote_counts(mock_bot, mock_vote_service):
    # Préparer les données de mock
    mock_votes = [
        {"id": 1, "channel_id": 123, "message_id": 456}
    ]

    # Configurer le mock du channel et du message
    mock_channel = Mock(spec=discord.TextChannel)
    mock_message = Mock(spec=discord.Message)
    mock_reaction = Mock()
    mock_reaction.count = 6  # 5 votes + 1 pour le bot
    mock_message.reactions = [mock_reaction]

    mock_bot.get_channel.return_value = mock_channel
    mock_channel.fetch_message = AsyncMock(return_value=mock_message)

    # Configurer le mock de la base de données
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=mock_votes)
    mock_bot.db.pool.acquire.return_value.__aenter__.return_value = mock_conn

    # Exécuter le test
    await mock_vote_service.update_vote_counts()

    # Vérifier que la mise à jour a été effectuée
    mock_conn.execute.assert_called_once()
    args, kwargs = mock_conn.execute.call_args
    assert args[1] == 5  # vote_count (6 - 1 pour le bot)
    assert args[2] == 1  # vote_id
