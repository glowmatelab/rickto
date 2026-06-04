from os import getenv
from typing import List
from dotenv import load_dotenv
import random

load_dotenv()


class Config:
    """
    Configuration class for managing bot settings.

    All settings are loaded from environment variables with sensible defaults where applicable.
    Required variables are validated on initialization through the check() method.
    """

    def __init__(self):
        """Initialize configuration by loading all environment variables."""

        # ============ TELEGRAM API CREDENTIALS ============
        self.API_ID: int = int(getenv("API_ID", "0"))
        self.API_HASH: str = getenv("API_HASH", "")

        # ============ BOT CONFIGURATION ============
        self.BOT_TOKEN: str = getenv("BOT_TOKEN", "")
        self.LOGGER_ID: int = int(getenv("LOGGER_ID", "0"))
        self.OWNER_ID: int = int(getenv("OWNER_ID", "0"))

        # ============ DATABASE CONFIGURATION ============
        self.MONGO_URL: str = getenv("MONGO_DB_URI", "")
        #------------------dplay------------------------------
        self.DIRECT_PLAY_CHANNEL: int = int(getenv("DIRECT_PLAY_CHANNEL", "0"))
        # ============ MUSIC BOT LIMITS ============
        self.DURATION_LIMIT: int = int(getenv("DURATION_LIMIT", "300")) * 60
        self.QUEUE_LIMIT: int = int(getenv("QUEUE_LIMIT", "30"))
        self.PLAYLIST_LIMIT: int = int(getenv("PLAYLIST_LIMIT", "20"))

        # ============ ASSISTANT/USERBOT SESSIONS ============
        self.SESSION1: str = getenv("STRING_SESSION", "")
        self.SESSION2: str = getenv("STRING_SESSION2", "")
        self.SESSION3: str = getenv("STRING_SESSION3", "")

        # ============ SUPPORT LINKS ============
        self.SUPPORT_CHANNEL: str = getenv(
            "SUPPORT_CHANNEL", "https://t.me/galaxy_bots_update")
        self.SUPPORT_CHAT: str = getenv(
            "SUPPORT_CHAT", "https://t.me/galaxysupportteam")

        # ============ EXCLUDED CHATS ============
        self.EXCLUDED_CHATS: List[int] = self._parse_excluded_chats()

        # ============ FEATURE FLAGS ============
        self.AUTO_END: bool = self._str_to_bool(getenv("AUTO_END", "False"))
        self.AUTO_LEAVE: bool = self._str_to_bool(getenv("AUTO_LEAVE", "False"))
        self.THUMB_GEN: bool = self._str_to_bool(getenv("THUMB_GEN", "True"))
        # ============ ASK AI ============
        self.ASKAI_API_KEY: str = getenv("ASKAI_API_KEY", "")
        # ============ API CONFIGURATION ============
        self.YOUTUBE_API_URL: str = getenv(
            "YOUTUBE_API_URL", "https://api.shrutibots.site")
        self.SHRUTI_API_KEY: str = getenv("SHRUTI_API_KEY", "")
        # ============ SPOTIFY CONFIGURATION ============
        #self.SPOTIFY_CLIENT_ID: str = getenv("SPOTIFY_CLIENT_ID", "")
        #self.SPOTIFY_CLIENT_SECRET: str = getenv("SPOTIFY_CLIENT_SECRET", "")

        # ============ IMAGE URLS — ALL LISTS FOR RANDOM ============
        self.DEFAULT_THUMBS: List[str] = [
            "https://drive.google.com/uc?id=165bJ_UImzvD6Xn5_ndrjpL6OdxWS5HYS",
            
        ]

        self.PING_IMGS: List[str] = [
            "https://drive.google.com/uc?id=165bJ_UImzvD6Xn5_ndrjpL6OdxWS5HYS",
            
        ]

        self.START_IMGS: List[str] = [
            "https://drive.google.com/uc?id=165bJ_UImzvD6Xn5_ndrjpL6OdxWS5HYS",
            "https://drive.google.com/uc?id=1y4KnINZ7MMM6DG2tMrcysI_pTGCdKhsc",
            "https://drive.google.com/uc?id=1RMcGcEL-ta_3L0CloFJeUbarT7GsU-B4",
            "https://drive.google.com/uc?id=1ADYcCBdN_qazu2J9CtZjgkw0g5CeIF3R",
            "https://drive.google.com/uc?id=16xIZgMc3dPWBie48Ui-RDm35fyhjLTMG",
            "https://drive.google.com/uc?id=1j8p2bp0fldppSMTRMeMPGip2m-i3z8S4",
            "https://drive.google.com/uc?id=1HAC5Ng_JCIZxRH3NtkocnrLOZtbYAD1b",
            "https://drive.google.com/uc?id=1oOBPDjHAGGmxPsJSYf9HE82z_ZyKR2Aw",
            "https://drive.google.com/uc?id=1XzJUUHhLnWwi3x8vmiunbhWZCm56w-x4",
            
        ]

        self.RADIO_IMGS: List[str] = [
            "https://drive.google.com/uc?id=165bJ_UImzvD6Xn5_ndrjpL6OdxWS5HYS",
        ]

        # Single values — random pick karo (DEFAULT_THUMB ke liye)
        self.DEFAULT_THUMB: str = getenv(
            "DEFAULT_THUMB", random.choice(self.DEFAULT_THUMBS))

        # ============ MODERATION ============
        self.EXCLUDED_USERNAMES: List[str] = getenv(
            "EXCLUDED_USERNAMES", "").split()

    def _parse_excluded_chats(self) -> List[int]:
        excluded = getenv("EXCLUDED_CHATS", "")
        if not excluded:
            return []
        chat_ids = []
        for chat_id in excluded.split(","):
            chat_id = chat_id.strip()
            if chat_id.lstrip('-').isdigit():
                chat_ids.append(int(chat_id))
        return chat_ids

    @staticmethod
    def _str_to_bool(value: str) -> bool:
        return value.lower() in ("true", "1", "yes", "y", "on")

    def check(self) -> None:
        required_vars = {
            "API_ID": self.API_ID,
            "API_HASH": self.API_HASH,
            "BOT_TOKEN": self.BOT_TOKEN,
            "MONGO_DB_URI": self.MONGO_URL,
            "LOGGER_ID": self.LOGGER_ID,
            "OWNER_ID": self.OWNER_ID,
            "STRING_SESSION": self.SESSION1,
        }
        missing = [
            name for name, value in required_vars.items()
            if not value or (isinstance(value, int) and value == 0)
        ]
        if missing:
            raise SystemExit(
                f"❌ Missing required environment variables: {', '.join(missing)}\n"
                f"Please check your .env file and ensure all required variables are set."
            )
