from os import getenv
from typing import List
from dotenv import load_dotenv
import random

# Load environment variables from .env file (create one from sample.env)
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
        # Get these from https://my.telegram.org
        # Telegram API ID (numeric)
        self.API_ID: int = int(getenv("API_ID", "0"))
        # Telegram API Hash (hexadecimal)
        self.API_HASH: str = getenv("API_HASH", "")

        # ============ BOT CONFIGURATION ============
        # Bot token from @BotFather
        self.BOT_TOKEN: str = getenv("BOT_TOKEN", "")
        # Group/channel ID for logs (must be negative)
        self.LOGGER_ID: int = int(getenv("LOGGER_ID", "0"))
        # Your user ID (get from @userinfobot)
        self.OWNER_ID: int = int(getenv("OWNER_ID", "0"))

        # ============ DATABASE CONFIGURATION ============
        # MongoDB connection URL (mongodb+srv://...)
        self.MONGO_URL: str = getenv("MONGO_DB_URI", "")

        # ============ MUSIC BOT LIMITS ============
        # Convert minutes to seconds for duration limit
        # Max song duration (default: 300 min)
        self.DURATION_LIMIT: int = int(getenv("DURATION_LIMIT", "300")) * 60
        # Max songs in queue (default: 30)
        self.QUEUE_LIMIT: int = int(getenv("QUEUE_LIMIT", "30"))
        # Max songs from playlist (default: 20)
        self.PLAYLIST_LIMIT: int = int(getenv("PLAYLIST_LIMIT", "20"))

        # ============ ASSISTANT/USERBOT SESSIONS ============
        # Pyrogram session strings - get from @StringFatherBot
        # You can have up to 3 assistants for handling multiple groups
        # Primary assistant (required)
        self.SESSION1: str = getenv("STRING_SESSION", "")
        # Secondary assistant (optional)
        self.SESSION2: str = getenv("STRING_SESSION2", "")
        # Tertiary assistant (optional)
        self.SESSION3: str = getenv("STRING_SESSION3", "")

        # ============ SUPPORT LINKS ============
        self.SUPPORT_CHANNEL: str = getenv(
            "SUPPORT_CHANNEL", "https://t.me/galaxy_bots_update")
        self.SUPPORT_CHAT: str = getenv("SUPPORT_CHAT", "https://t.me/galaxysupportteam")

        # ============ EXCLUDED CHATS ============
        # Parse comma-separated chat IDs that assistants should never leave
        self.EXCLUDED_CHATS: List[int] = self._parse_excluded_chats()

        # ============ FEATURE FLAGS ============
        # Auto-end stream when queue is empty
        self.AUTO_END: bool = self._str_to_bool(getenv("AUTO_END", "False"))
        # Auto-leave inactive chats
        self.AUTO_LEAVE: bool = self._str_to_bool(getenv("AUTO_LEAVE", "False"))
        # Enable/disable thumbnail generation (set False to use default thumb)
        self.THUMB_GEN: bool = self._str_to_bool(getenv("THUMB_GEN", "True"))

        # ============ API CONFIGURATION ============
        # YouTube API URL for downloading (replaces cookies)
        self.YOUTUBE_API_URL: str = getenv("YOUTUBE_API_URL", "https://shrutibots.site")

        # ============ IMAGE URLS ============
        # URLs for various bot images
        # ============ IMAGE URLS ============
        _DEFAULT_THUMBS = [
            "https://i.pinimg.com/550x/fc/48/c6/fc48c6e50f85375fdaadb987b9aaca09.jpg",
            "https://i.pinimg.com/550x/fc/48/c6/fc48c6e50f85375fdaadb987b9aaca09.jpg",
        ]
        _PING_IMGS = [
            "https://i.pinimg.com/550x/fc/48/c6/fc48c6e50f85375fdaadb987b9aaca09.jpg",
            "https://i.pinimg.com/550x/fc/48/c6/fc48c6e50f85375fdaadb987b9aaca09.jpg",
        ]
        _START_IMGS = [
            "https://i.pinimg.com/550x/fc/48/c6/fc48c6e50f85375fdaadb987b9aaca09.jpg",
            "https://img.freepik.com/premium-photo/anime-girl-listening-music-while-sitting-table-with-drink-generative-ai_733139-40138.jpg",
            "https://motionbgs.com/media/5785/goth-anime-girl.jpg",
            "https://wallpaperbat.com/img/888697.jpg",
            "https://image.cdn2.seaart.ai/2023-07-19/46636105711685/3d49c1baa56ecf4223342600635dd79d5d7764cd_high.webp",
            "https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/83c3ac45-0de3-4f59-8dfe-a2379b3a3400/djp0q30-25e8b9ec-6fe2-4246-adbd-b51b6aafb88a.png/v1/fill/w_1182,h_676,q_70,strp/_second_charge__by_evlsound_djp0q30-pre.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7ImhlaWdodCI6Ijw9NzMyIiwicGF0aCI6IlwvZlwvODNjM2FjNDUtMGRlMy00ZjU5LThkZmUtYTIzNzliM2EzNDAwXC9kanAwcTMwLTI1ZThiOWVjLTZmZTItNDI0Ni1hZGJkLWI1MWI2YWFmYjg4YS5wbmciLCJ3aWR0aCI6Ijw9MTI4MCJ9XV0sImF1ZCI6WyJ1cm46c2VydmljZTppbWFnZS5vcGVyYXRpb25zIl19.TxMk8t3sbhfVyHHw0mSVQa3gM44_WAerlfgclzx8ZsA",
            "https://moewalls.com/wp-content/uploads/2024/09/anime-girl-watching-sunset-pixel-thumb.jpg",
        ]
        _RADIO_IMGS = [
            "https://i.pinimg.com/550x/fc/48/c6/fc48c6e50f85375fdaadb987b9aaca09.jpg",
            "https://i.pinimg.com/550x/fc/48/c6/fc48c6e50f85375fdaadb987b9aaca09.jpg",
        ]
        self.DEFAULT_THUMB: str = getenv("DEFAULT_THUMB", random.choice(_DEFAULT_THUMBS))
        self.PING_IMG: str = getenv("PING_IMG", random.choice(_PING_IMGS))
        self.START_IMG: str = getenv("START_IMG", random.choice(_START_IMGS))
        self.RADIO_IMG: str = getenv("RADIO_IMG", random.choice(_RADIO_IMGS))

        # ============ MODERATION ============
        # List of usernames to exclude from admin mentions
        self.EXCLUDED_USERNAMES: List[str] = getenv("EXCLUDED_USERNAMES", "").split()

    def _parse_excluded_chats(self) -> List[int]:
        """
        Parse excluded chat IDs from comma-separated string.

        Returns:
            List[int]: List of chat IDs to exclude from auto-leave.
        """
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
        """
        Convert string to boolean value.

        Args:
            value: String representation of boolean.

        Returns:
            bool: Converted boolean value.
        """
        return value.lower() in ("true", "1", "yes", "y", "on")

    def check(self) -> None:
        """
        Validate that all required environment variables are set.

        Raises:
            SystemExit: If any required variables are missing.
        """
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
