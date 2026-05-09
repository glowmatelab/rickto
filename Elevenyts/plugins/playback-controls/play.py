from pyrogram import filters
from pyrogram import types
from pyrogram.errors import FloodWait, MessageIdInvalid, MessageDeleteForbidden, ChatSendPlainForbidden, ChatWriteForbidden

from Elevenyts import tune, app, config, db, lang, queue, tg, yt
from Elevenyts.core.spotify import is_spotify, get_track, get_playlist
from Elevenyts.helpers import buttons, utils
from Elevenyts.helpers._play import checkUB
import asyncio
import logging

logger = logging.getLogger(__name__)


async def safe_edit(message, text, **kwargs):
    try:
        await message.edit_text(text, **kwargs)
        return True
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            await message.edit_text(text, **kwargs)
            return True
        except (MessageIdInvalid, MessageDeleteForbidden, Exception):
            return False
    except (MessageIdInvalid, MessageDeleteForbidden):
        return False
    except Exception:
        return False


async def safe_reply(message, text, **kwargs):
    try:
        return await message.reply_text(text, **kwargs)
    except (ChatSendPlainForbidden, ChatWriteForbidden):
        logger.warning(f"Cannot send text in chat {message.chat.id} (chat write forbidden)")
        return None
    except Exception as e:
        logger.error(f"Failed to send reply: {e}")
        return None


def playlist_to_queue(chat_id: int, tracks: list) -> str:
    text = "<blockquote expandable>"
    for track in tracks:
        pos = queue.add(chat_id, track)
        text += f"<b>{pos}.</b> {track.title}\n"
    text = text[:1948] + "</blockquote>"
    return text

@app.on_message(
    filters.command(["play", "playforce", "vplay", "vplayforce", "cplay", "cplayforce"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
@checkUB
async def play_hndlr(
    _,
    m: types.Message,
    force: bool = False,
    url: str = None,
    cplay: bool = False,
    video: bool = False,
) -> None:
    try:
        await m.delete()
    except Exception:
        pass
    
    command = m.command[0].lower()
    if command in ["vplay", "vplayforce"]:
        video = True
        if "force" in command:
            force = True
    
    chat_id = m.chat.id
    message_chat_id = m.chat.id
    if cplay:
        channel_id = await db.get_cmode(m.chat.id)
        if channel_id is None:
            return await safe_reply(m,
                "<blockquote>❌ Channel play is not enabled.\n\n"
                "To enable for linked channel:\n"
                "`/channelplay linked`\n\n"
                "To enable for any channel:\n"
                "`/channelplay [channel_id]`</blockquote>"
            )
        try:
            chat = await app.get_chat(channel_id)
            chat_id = channel_id
        except:
            await db.set_cmode(m.chat.id, None)
            return await safe_reply(m,
                "<blockquote>❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ɢᴇᴛ ᴄʜᴀɴɴᴇʟ.\n\n"
                "ᴍᴀᴋᴇ ꜱᴜʀᴇ ɪ'ᴍ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ᴄʜᴀɴɴᴇʟ ᴘʟᴀʏ ɪꜱ ꜱᴇᴛ ᴄᴏʀʀᴇᴄᴛʟʏ.</blockquote>"
            )
        
        client = await db.get_client(channel_id)
        try:
            await app.get_chat_member(channel_id, client.id)
        except Exception:
            try:
                if chat.username:
                    invite_link = chat.username
                else:
                    try:
                        invite_link = chat.invite_link
                        if not invite_link:
                            invite_link = await app.export_chat_invite_link(channel_id)
                    except Exception:
                        return await safe_reply(m,
                            f"<blockquote>❌ ᴀꜱꜱɪꜱᴛᴀɴᴛ ɴᴏᴛ ɪɴ ᴄʜᴀɴɴᴇʟ!\n\n"
                            f"ᴘʟᴇᴀꜱᴇ ᴀᴅᴅ @{client.username if client.username else client.mention} "
                            f"ᴛᴏ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ᴀꜱ ᴀᴅᴍɪɴ ᴡɪᴛʜ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ.</blockquote>"
                        )
                
                join_msg = await safe_reply(m,
                    f"<blockquote>🔄 ᴊᴏɪɴɪɴɢ ᴀꜱꜱɪꜱᴛᴀɴᴛ ᴛᴏ ᴄʜᴀɴɴᴇʟ...</blockquote>"
                )
                
                await client.join_chat(invite_link)
                await asyncio.sleep(1)
                
                try:
                    await join_msg.delete()
                except:
                    pass
                    
            except Exception as e:
                error_str = str(e)
                return await safe_reply(m,
                    f"<blockquote>❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ᴊᴏɪɴ ᴀꜱꜱɪꜱᴛᴀɴᴛ ᴛᴏ ᴄʜᴀɴɴᴇʟ!\n\n"
                    f"ᴘʟᴇᴀꜱᴇ ᴍᴀɴᴜᴀʟʟʏ ᴀᴅᴅ @{client.username if client.username else client.mention} "
                    f"ᴛᴏ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ᴀꜱ ᴀᴅᴍɪɴ ᴡɪᴛʜ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ.\n\n"
                    f"Error: {error_str}</blockquote>"
                )

    play_emoji = m.lang["play_emoji"]
    
    try:
        sent = await safe_reply(m, m.lang["play_searching"].format(play_emoji))
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            sent = await safe_reply(m, m.lang["play_searching"].format(play_emoji))
        except FloodWait as e2:
            await asyncio.sleep(e2.value)
            return
        except Exception:
            return
    except Exception:
        return
    
    mention = m.from_user.mention
    media = tg.get_media(m.reply_to_message) if m.reply_to_message else None
    tracks = []
    file = None

    if media:
        setattr(sent, "lang", m.lang)
        file = await tg.download(m.reply_to_message, sent)

    elif url:
        if is_spotify(url):
            if "playlist" in url or "album" in url:
                await safe_edit(sent, "🎵 Spotify playlist fetch ho rahi hai...")
                queries = await get_playlist(url)
                if not queries:
                    await safe_edit(sent, "❌ Spotify playlist nahi mili!")
                    return
                spotify_tracks = []
                for query in queries[:config.PLAYLIST_LIMIT]:
                    track = await yt.search(query, sent.id)
                    if track:
                        track.user = mention
                        spotify_tracks.append(track)
                if not spotify_tracks:
                    await safe_edit(sent, "❌ Koi track nahi mila YouTube pe!")
                    return
                file = spotify_tracks[0]
                tracks = spotify_tracks[1:]
                file.message_id = sent.id
            else:
                await safe_edit(sent, "🎵 Spotify se song dhundh raha hoon...")
                query = await get_track(url)
                if not query:
                    await safe_edit(sent, "❌ Spotify track nahi mila!")
                    return
                file = await yt.search(query, sent.id, video=video)

        elif "playlist" in url:
            await safe_edit(sent, m.lang["playlist_fetch"])
            try:
                tracks = await yt.playlist(
                    config.PLAYLIST_LIMIT, mention, url
                )
            except Exception as e:
                await safe_edit(
                    sent,
                    f"<blockquote>❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ꜰᴇᴛᴄʜ ᴘʟᴀʏʟɪꜱᴛ.\n\n"
                    f"ʏᴏᴜᴛᴜʙᴇ ᴘʟᴀʏʟɪꜱᴛꜱ ᴀʀᴇ ᴄᴜʀʀᴇɴᴛʟʏ ᴇxᴘᴇʀɪᴇɴᴄɪɴɢ ɪꜱꜱᴜᴇꜱ. "
                    f"ᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴘʟᴀʏɪɴɢ ɪɴᴅɪᴠɪᴅᴜᴀʟ ꜱᴏɴɢꜱ ɪɴꜱᴛᴇᴀᴅ.</blockquote>"
                )
                return

            if not tracks:
                await safe_edit(sent, m.lang["playlist_error"])
                return

            file = tracks[0]
            tracks.remove(file)
            file.message_id = sent.id
        else:
            file = await yt.search(url, sent.id, video=video)

        if not file:
            await safe_edit(
                sent,
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )
            return

    elif len(m.command) >= 2:
        query = " ".join(m.command[1:])
        file = await yt.search(query, sent.id, video=video)
        if not file:
            await safe_edit(
                sent,
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )
            return

    if not file:
        return

    file.video = video

    if not file.is_live and file.duration_sec > config.DURATION_LIMIT:
        await safe_edit(
            sent,
            m.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60)
        )
        return

    if await db.is_logger():
        await utils.play_log(m, file.title, file.duration)

    file.user = mention
    if force:
        queue.force_add(chat_id, file)
    else:
        position = queue.add(chat_id, file)

        if await db.get_call(chat_id):
            await safe_edit(
                sent,
                m.lang["play_queued"].format(
                    position,
                    file.url,
                    file.title,
                    file.duration,
                    m.from_user.mention,
                ),
                reply_markup=buttons.play_queued(
                    chat_id, file.id, m.lang["play_now"]
                ),
            )
            if tracks:
                added = playlist_to_queue(chat_id, tracks)
                try:
                    await app.send_message(
                        chat_id=m.chat.id,
                        text=m.lang["playlist_queued"].format(len(tracks)) + added,
                    )
                except Exception:
                    pass
            
            try:
                from Elevenyts import preload
                asyncio.create_task(preload.start_preload(chat_id, count=2))
            except Exception:
                pass
            
            return

    if not file.file_path:
        file.file_path = await yt.download(file.id, is_live=file.is_live, video=video)
        if not file.file_path:
            await safe_edit(
                sent,
                "<blockquote>❌ Failed to download media.\n\n"
                "Possible reasons:\n"
                "• YouTube detected bot activity (update cookies)\n"
                "• Video is region-blocked or private\n"
                "• Age-restricted content (requires cookies)</blockquote>"
            )

    try:
        await tune.play_media(
            chat_id=chat_id, 
            message=sent, 
            media=file, 
            message_chat_id=message_chat_id if chat_id != message_chat_id else None
        )
        try:
            emoji = m.lang["play_emoji"]
            await m.react(emoji)
        except Exception:
            pass
    except Exception as e:
        error_msg = str(e)
        if "bot" in error_msg.lower() or "sign in" in error_msg.lower():
            await safe_edit(
                sent,
                "<blockquote>❌ YouTube bot detection triggered.\n\n"
                "Solution:\n"
                "• Update YouTube cookies in `Elevenyts/cookies/` folder\n"
                "• Wait a few minutes before trying again\n"
                "• Try /radio for uninterrupted music\n\n"
                f"Support: {config.SUPPORT_CHAT}</blockquote>"
            )
        else:
            await safe_edit(
                sent,
                f"<blockquote>❌ Playback error:\n{error_msg}\n\n"
                f"Support: {config.SUPPORT_CHAT}</blockquote>"
            )
        return

    if not tracks:
        return
    added = playlist_to_queue(chat_id, tracks)
    try:
        await app.send_message(
            chat_id=m.chat.id,
            text=m.lang["playlist_queued"].format(len(tracks)) + added,
        )
    except Exception:
        pass
