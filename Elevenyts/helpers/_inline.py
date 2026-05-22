from pyrogram import enums, types
from Elevenyts import app, config, lang

class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm([[self.ikb(text=text, callback_data=f"cancel_dl", style=enums.ButtonStyle.DANGER)]])

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []
        if status:
            # Status button ko Red (DANGER) kiya
            keyboard.append(
                [self.ikb(text=status, callback_data=f"controls status {chat_id}", style=enums.ButtonStyle.PRIMARY)]
            )
        elif timer:
            # Timer button ko Red (DANGER) kiya
            keyboard.append(
                [self.ikb(text=timer, callback_data=f"controls status {chat_id}", style=enums.ButtonStyle.DANGER)]
            )

        if not remove:
            # Main control buttons row
            keyboard.append(
                [
                    self.ikb(text="▷", callback_data=f"controls resume {chat_id}"),
                    self.ikb(text="II", callback_data=f"controls pause {chat_id}"), # style=enums.ButtonStyle.PRIMARY),
                    self.ikb(text="↻", callback_data=f"controls replay {chat_id}"), #,style=enums.ButtonStyle.SUCCESS),
                    self.ikb(text="‣‣I", callback_data=f"controls skip {chat_id}"), # style=enums.ButtonStyle.PRIMARY),
                    self.ikb(text="▢", callback_data=f"controls stop {chat_id}"),
                ]
            )
            # Delete button as full-width button at bottom
            keyboard.append(
                [
                    self.ikb(text="ᴅᴇʟᴇᴛᴇ", callback_data=f"controls close {chat_id}", style=enums.ButtonStyle.DANGER),
                ]
            )
        return self.ikm(keyboard)

    def help_markup(
        self, _lang: dict, back: bool = False
    ) -> types.InlineKeyboardMarkup:
        """Create help menu with categorized buttons."""
        if back:
            rows = [
                [
                    self.ikb(text="ʙᴀᴄᴋ", callback_data="help_main", style=enums.ButtonStyle.SUCCESS),
                ]
            ]
        else:
            rows = [
                [
                    self.ikb(text="ᴀᴅᴍɪɴꜱ", callback_data="help_admins"),
                    self.ikb(text="ᴀᴜᴛʜ", callback_data="help_auth"),
                    self.ikb(text="ʙʀᴏᴀᴅᴄᴀꜱᴛ", callback_data="help_broadcast"),
                ],
                [
                    self.ikb(text="ʙʟ-ᴄʜᴀᴛ", callback_data="help_blchat"),
                    self.ikb(text="ʙʟ-ᴜꜱᴇʀ", callback_data="help_bluser"),
                    self.ikb(text="ɢ-ʙᴀɴ", callback_data="help_gban"),
                ],
                [
                    self.ikb(text="ʟᴏᴏᴘ", callback_data="help_loop"),
                    self.ikb(text="ᴘʟᴀʏ", callback_data="help_play"),
                    self.ikb(text="ǫᴜᴇᴜᴇ", callback_data="help_queue"),
                ],
                [
                    self.ikb(text="ꜱᴇᴇᴋ", callback_data="help_seek"),
                    self.ikb(text="ꜱʜᴜꜰꜰʟᴇ", callback_data="help_shuffle"),
                    self.ikb(text="ᴘɪɴɢ", callback_data="help_ping"),
                ],
                [
                    self.ikb(text="ꜱᴛᴀᴛꜱ", callback_data="help_stats"),
                    self.ikb(text="ꜱᴜᴅᴏ", callback_data="help_sudo"),
                    self.ikb(text="ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ", callback_data="help_maintenance"),
                ],
                [
                # ✅ Naya button
                    self.ikb(text="⚡  ᴀᴅᴠᴀɴᴄᴇ", callback_data="help_advance", style=enums.ButtonStyle.DANGER),
                    self.ikb(text="⚙️ ᴏᴘᴛɪᴏɴꜱ", callback_data="help_options", style=enums.ButtonStyle.PRIMARY),
                ],
                [
                    self.ikb(text="ʙᴀᴄᴋ", callback_data="start"),
                ]
            ]
        return self.ikm(rows)

    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
            return self.ikm([
                [
                    # Channel aur Support ko Blue (PRIMARY) color diya
                    self.ikb(text="📢 Channel", url=config.SUPPORT_CHANNEL, style=enums.ButtonStyle.PRIMARY),
                    self.ikb(text="🆘 Support", url=config.SUPPORT_CHAT, style=enums.ButtonStyle.PRIMARY),
                ],
                [
                    # Add Me button ko Green (SUCCESS) color diya
                    self.ikb(
                        text="➕ Add Me to Your Group", 
                        url=f"https://t.me/{app.username}?startgroup=true",
                        style=enums.ButtonStyle.SUCCESS
                    ),
                ]
            ])
    def play_queued(
        self, chat_id: int, item_id: str, _text: str
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(text="▷", callback_data=f"controls resume {chat_id}", style=enums.ButtonStyle.SUCCESS),
                    self.ikb(text="∣ ∣", callback_data=f"controls pause {chat_id}", style=enums.ButtonStyle.PRIMARY),
                    self.ikb(text=">>", callback_data=f"controls skip {chat_id}", style=enums.ButtonStyle.PRIMARY),
                    self.ikb(text="▣", callback_data=f"controls stop {chat_id}", style=enums.ButtonStyle.DANGER),
                ],
                [
                    self.ikb(text="ᴅᴇʟᴇᴛᴇ", callback_data=f"controls close {chat_id}", style=enums.ButtonStyle.DANGER),
                ]
            ]
        )

    def queue_markup(
        self, chat_id: int, _text: str, playing: bool
    ) -> types.InlineKeyboardMarkup:
        _action = "pause" if playing else "resume"
        return self.ikm(
            [[self.ikb(
                text=_text, callback_data=f"controls {_action} {chat_id} q")]]
        )

    def settings_markup(
        self, lang: dict, admin_only: bool, language: str, chat_id: int
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=lang["play_mode"] + " ➜",
                        callback_data=f"controls status {chat_id}",
                    ),
                    self.ikb(text=admin_only, callback_data="playmode"),
                ],
            ]
        )

    def start_key(
        self, lang: dict, private: bool = False
    ) -> types.InlineKeyboardMarkup:
        rows = [
            [
                self.ikb(
                    text=lang["add_me"],
                    url=f"https://t.me/{app.username}?startgroup=true",
                    style=enums.ButtonStyle.SUCCESS, # Isse "Add Me" Green ho jayega
                )
            ],
            [self.ikb(text=lang["help"], callback_data="help")],
            [
                self.ikb(text=lang["support"], url=config.SUPPORT_CHAT, style=enums.ButtonStyle.PRIMARY), # Blue
                self.ikb(text=lang["channel"], url=config.SUPPORT_CHANNEL, style=enums.ButtonStyle.PRIMARY), # Blue
            ],
        ]
        return self.ikm(rows)

    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(text="ᴄᴏᴘʏ ʟɪɴᴋ", copy_text=link),
                    self.ikb(text="ᴏᴘᴇɴ ɪɴ ʏᴏᴜᴛᴜʙᴇ", url=link),
                ],
            ]
        )
