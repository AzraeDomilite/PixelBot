import asyncio
from src.bot import PixelBot
from src.utils.config import load_config
from src.utils.logger import setup_logging

def main():
    setup_logging()
    config = load_config()
    bot = PixelBot(config)
    asyncio.run(bot.start(bot.config.bot.token))

if __name__ == "__main__":
    main()