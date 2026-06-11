# -*- coding: utf-8 -*-
"""Configuration management"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

class Config:
    """Bot configuration"""

    def __init__(self):
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)

        # Bot token (set via environment or config file)
        self.bot_token = os.getenv('BOT_TOKEN', '')

        # API credentials for UserBot
        self.api_id = int(os.getenv('API_ID', '0'))
        self.api_hash = os.getenv('API_HASH', '')

        # Database
        self.db_path = self.data_dir / 'bot.db'

        # Settings
        self.max_keywords = 50
        self.max_groups = 100
        self.check_interval = 2  # seconds

        # Load saved config
        self._load_config()

    def _load_config(self):
        config_file = self.data_dir / 'config.json'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.bot_token = data.get('bot_token', self.bot_token)
                self.api_id = data.get('api_id', self.api_id)
                self.api_hash = data.get('api_hash', self.api_hash)

    def save(self):
        config_file = self.data_dir / 'config.json'
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({
                'bot_token': self.bot_token,
                'api_id': self.api_id,
                'api_hash': self.api_hash
            }, f, ensure_ascii=False, indent=2)

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.api_id and self.api_hash)
