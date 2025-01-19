import pytest
import asyncpg
from datetime import datetime
from src.database.database import Database
from src.utils.config import Config

@pytest.fixture
async def config():
    return {
        'database': {
            'host': 'db',
            'port': 5432,
            'user': 'botuser',
            'password': 'botpassword',
            'name': 'botdb'
        }
    }

@pytest.fixture
async def test_db(config):
    db = await Database.create(Config(config))
    yield db
    await db.close()

@pytest.mark.asyncio
async def test_create_vote(test_db):
    # Préparer les données de test
    vote_data = {
        'title': 'Test Vote',
        'image_name': 'test.png',
        'image_url': 'http://test.com/image.png',
        'json_data': {'width': 42, 'height': 30},
        'channel_id': 123456789,
        'message_id': 987654321,
        'created_by': 111222333,
        'coord_x': 100,
        'coord_z': 200
    }

    # Tester la création du vote
    async with test_db.pool.acquire() as conn:
        record = await conn.fetchrow("""
            INSERT INTO votes (
                title, image_name, image_url, json_data, 
                channel_id, message_id, created_by,
                coord_x, coord_z
            )
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)
            RETURNING id
        """, 
            vote_data['title'],
            vote_data['image_name'],
            vote_data['image_url'],
            vote_data['json_data'],
            vote_data['channel_id'],
            vote_data['message_id'],
            vote_data['created_by'],
            vote_data['coord_x'],
            vote_data['coord_z']
        )

        assert record is not None
        assert record['id'] > 0

    # Vérifier l'insertion
    assert record is not None
    assert record['id'] > 0

    # Récupérer et vérifier le vote
    async with test_db.pool.acquire() as conn:
        vote = await conn.fetchrow(
            'SELECT * FROM votes WHERE id = $1',
            record['id']
        )
        
    assert vote['title'] == vote_data['title']
    assert vote['image_name'] == vote_data['image_name']
    assert vote['coord_x'] == vote_data['coord_x']
    assert vote['coord_z'] == vote_data['coord_z']

@pytest.mark.asyncio
async def test_update_vote_count(test_db):
    # Créer un vote de test
    async with test_db.pool.acquire() as conn:
        vote_id = await conn.fetchval("""
            INSERT INTO votes (
                title, image_name, image_url, created_by,
                coord_x, coord_z, vote_count
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """, 'Test Vote', 'test.png', 'http://test.com/image.png',
            111222333, 100, 200, 0)

        # Mettre à jour le compte
        await conn.execute("""
            UPDATE votes 
            SET vote_count = $1
            WHERE id = $2
        """, 5, vote_id)

        # Vérifier la mise à jour
        updated_count = await conn.fetchval(
            'SELECT vote_count FROM votes WHERE id = $1',
            vote_id
        )
        
    assert updated_count == 5

@pytest.mark.asyncio
async def test_get_vote_stats(test_db):
    # Créer plusieurs votes de test
    async with test_db.pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO votes (
                title, image_name, image_url, created_by,
                coord_x, coord_z, vote_count
            )
            VALUES 
                ($1, $2, $3, $4, $5, $6, $7),
                ($8, $9, $10, $11, $12, $13, $14)
        """,
            'Vote 1', 'test1.png', 'http://test.com/1.png', 111, 100, 200, 5,
            'Vote 2', 'test2.png', 'http://test.com/2.png', 222, 300, 400, 3
        )

        # Récupérer les stats
        stats = await conn.fetch("""
            SELECT title, vote_count, created_at
            FROM votes
            WHERE is_active = true
            ORDER BY vote_count DESC
        """)

    assert len(stats) == 2
    assert stats[0]['vote_count'] == 5
    assert stats[1]['vote_count'] == 3
