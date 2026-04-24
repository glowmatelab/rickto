from pyrogram import types

from Elevenyts import app, config, lang


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm([[self.ikb(text=f"✕  {text}", callback_data=f"cancel_dl")]])

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []
        if status:
            keyboard.append(
                [self.ikb(text=f"◈  {status}", callback_data=f"controls status {chat_id}")]
            )
        elif timer:
            keyboard.append(
                [self.ikb(text=f"◈  {timer}", callback_data=f"controls status {chat_id}")]
            )

        if not remove:
            # Seek + Play/Pause row
            keyboard.append(
                [
                    self.ikb(text="«  ⁻¹⁰ˢ", callback_data=f"controls seekback {chat_id}"),
                    self.ikb(text="▷  ᴘʟᴀʏ", callback_data=f"controls resume {chat_id}"),
                    self.ikb(text="❙❙  ᴘᴀᴜꜱᴇ", callback_data=f"controls pause {chat_id}"),
                    self.ikb(text="⁺¹⁰ˢ  »", callback_data=f"controls seekfwd {chat_id}"),
                ]
            )
            # Loop, Replay, Skip row
            keyboard.append(
                [
                    self.ikb(text="↺  ʟᴏᴏᴘ", callback_data=f"controls loop {chat_id}"),
                    self.ikb(text="↻  ʀᴇᴘʟᴀʏ", callback_data=f"controls replay {chat_id}"),
                    self.ikb(text="⊲⊳  ꜱᴋɪᴘ", callback_data=f"controls skip {chat_id}"),
                ]
            )
            # Stop full width
            keyboard.append(
                [
                    self.ikb(text="⊗  ꜱᴛᴏᴘ", callback_data=f"controls stop {chat_id}"),
                ]
            )
            # Close full width
            keyboard.append(
                [
                    self.ikb(text="✕  ᴄʟᴏꜱᴇ", callback_data=f"controls close {chat_id}"),
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
                    self.ikb(text="↩  ʙᴀᴄᴋ", callback_data="help_main"),
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
                    self.ikb(text="↩  ʙᴀᴄᴋ", callback_data="start"),
                ]
            ]
        return self.ikm(rows)

    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm([
            [
                self.ikb(text="◈  ᴄʜᴀɴɴᴇʟ", url=config.SUPPORT_CHANNEL),
                self.ikb(text="◈  ꜱᴜᴘᴘᴏʀᴛ", url=config.SUPPORT_CHAT),
            ],
            [
                self.ikb(text="⊕  ᴀᴅᴅ ᴛᴏ ɢʀᴏᴜᴘ", url=f"https://t.me/{app.username}?startgroup=true"),
            ]
        ])

    def play_queued(
        self, chat_id: int, item_id: str, _text: str
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                # Queue info row
                [
                    self.ikb(text=f"⟨  {_text}  ⟩", callback_data=f"controls status {chat_id}"),
                ],
                # Basic controls row
                [
                    self.ikb(text="▷  ᴘʟᴀʏ", callback_data=f"controls resume {chat_id}"),
                    self.ikb(text="⊲⊳  ꜱᴋɪᴘ", callback_data=f"controls skip {chat_id}"),
                    self.ikb(text="⊗  ꜱᴛᴏᴘ", callback_data=f"controls stop {chat_id}"),
                ],
                # Close full width
                [
                    self.ikb(text="✕  ᴄʟᴏꜱᴇ", callback_data=f"controls close {chat_id}"),
                ],
            ]
        )

    def queue_markup(
        self, chat_id: int, _text: str, playing: bool
    ) -> types.InlineKeyboardMarkup:
        _action = "pause" if playing else "resume"
        _icon = "❙❙  ᴘᴀᴜꜱᴇ" if playing else "▷  ᴘʟᴀʏ"
        return self.ikm(
            [[self.ikb(
                text=_icon, callback_data=f"controls {_action} {chat_id} q")]]
        )

    def settings_markup(
        self, lang: dict, admin_only: bool, language: str, chat_id: int
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=lang["play_mode"] + "  ➜",
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
                    text="⊕  " + lang["add_me"],
                    url=f"https://t.me/{app.username}?startgroup=true",
                )
            ],
            [self.ikb(text="◈  " + lang["help"], callback_data="help")],
            [
                self.ikb(text="◈  " + lang["support"], url=config.SUPPORT_CHAT),
                self.ikb(text="◈  " + lang["channel"], url=config.SUPPORT_CHANNEL),
            ],
        ]
        return self.ikm(rows)

    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(text="⊕  ᴄᴏᴘʏ ʟɪɴᴋ", copy_text=link),
                    self.ikb(text="↗  ʏᴏᴜᴛᴜʙᴇ", url=link),
                ],
            ]
        )
