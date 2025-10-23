import os
from dataclasses import dataclass

@dataclass
class AppConfig:
    debug: bool = bool(os.getenv('OPSPILOT_DEBUG', '').lower() == 'true')
    data_dir: str = os.getenv('OPSPILOT_DATA_DIR', 'ai_shell_agent/data')

CONFIG = AppConfig()
