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

        # ============ API CONFIGURATION ============
        self.YOUTUBE_API_URL: str = getenv(
            #"YOUTUBE_API_URL", "https://shrutibots.site")
            YOUTUBE_API_URL", "https://yt-api-q7w6.onrender.com")
    
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
            "https://i.pinimg.com/550x/fc/48/c6/fc48c6e50f85375fdaadb987b9aaca09.jpg",
            "https://img.freepik.com/premium-photo/anime-girl-listening-music-while-sitting-table-with-drink-generative-ai_733139-40138.jpg",
            "https://motionbgs.com/media/5785/goth-anime-girl.jpg",
            "https://wallpaperbat.com/img/888697.jpg",
            "https://image.cdn2.seaart.ai/2023-07-19/46636105711685/3d49c1baa56ecf4223342600635dd79d5d7764cd_high.webp",
            "https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/83c3ac45-0de3-4f59-8dfe-a2379b3a3400/djp0q30-25e8b9ec-6fe2-4246-adbd-b51b6aafb88a.png/v1/fill/w_1182,h_676,q_70,strp/_second_charge__by_evlsound_djp0q30-pre.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7ImhlaWdodCI6Ijw9NzMyIiwicGF0aCI6IlwvZlwvODNjM2FjNDUtMGRlMy00ZjU5LThkZmUtYTIzNzliM2EzNDAwXC9kanAwcTMwLTI1ZThiOWVjLTZmZTItNDI0Ni1hZGJkLWI1MWI2YWFmYjg4YS5wbmciLCJ3aWR0aCI6Ijw9MTI4MCJ9XV0sImF1ZCI6WyJ1cm46c2VydmljZTppbWFnZS5vcGVyYXRpb25zIl19.TxMk8t3sbhfVyHHw0mSVQa3gM44_WAerlfgclzx8ZsA",
            "https://moewalls.com/wp-content/uploads/2024/09/anime-girl-watching-sunset-pixel-thumb.jpg",
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
