#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تجميع طلبات التوصيل - Delivery Order Aggregator Bot
Telegram Bot + UserBot for monitoring delivery groups
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from bot.bot_manager import BotManager
from bot.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point"""
    config = Config()
    manager = BotManager(config)

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal, stopping...")
        asyncio.create_task(manager.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await manager.start()
        # Keep running
        while manager.running:
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await manager.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
