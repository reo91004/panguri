import asyncio
import io
import logging
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional

import discord

logger = logging.getLogger("tts-bot.audio")


@dataclass
class AudioItem:
    """큐에 들어가는 오디오 항목."""

    source: io.IOBase
    cleanup_callback: Callable
    text: str
    user_id: int
    guild_id: int
    effect: str = "none"


class GuildAudioQueue:
    """서버별 오디오 큐."""

    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.queue: deque[AudioItem] = deque()
        self.current: Optional[AudioItem] = None
        self.is_playing = False
        self._lock = asyncio.Lock()

    async def add(self, item: AudioItem) -> int:
        async with self._lock:
            self.queue.append(item)
            return len(self.queue)

    async def next(self) -> Optional[AudioItem]:
        async with self._lock:
            if self.queue:
                self.current = self.queue.popleft()
                return self.current
            self.current = None
            return None

    async def skip(self) -> bool:
        async with self._lock:
            if self.current:
                self.current = None
                return True
            return False

    async def clear(self) -> list[AudioItem]:
        async with self._lock:
            items = list(self.queue)
            if self.current:
                items.append(self.current)
            self.queue.clear()
            self.current = None
            return items

    def __len__(self) -> int:
        return len(self.queue)


class AudioManager:
    """모든 서버의 오디오 큐와 재생을 관리한다."""

    def __init__(self):
        self.queues: dict[int, GuildAudioQueue] = {}
        self._playback_tasks: dict[int, asyncio.Task] = {}

    def get_queue(self, guild_id: int) -> GuildAudioQueue:
        if guild_id not in self.queues:
            self.queues[guild_id] = GuildAudioQueue(guild_id)
        return self.queues[guild_id]

    async def add_to_queue(
        self,
        guild_id: int,
        source: io.IOBase,
        cleanup_callback: Callable,
        text: str,
        user_id: int,
        effect: str = "none",
    ) -> int:
        queue = self.get_queue(guild_id)
        item = AudioItem(
            source=source,
            cleanup_callback=cleanup_callback,
            text=text,
            user_id=user_id,
            guild_id=guild_id,
            effect=effect,
        )
        return await queue.add(item)

    async def play_next(
        self,
        voice_client: discord.VoiceClient,
        guild_id: int,
    ) -> None:
        queue = self.get_queue(guild_id)

        if queue.is_playing:
            logger.debug("이미 재생 중, 큐에 추가됨")
            return

        item = await queue.next()
        if not item:
            logger.debug("큐가 비어있음, 재생할 항목 없음")
            return

        if not voice_client or not voice_client.is_connected():
            logger.warning("음성 클라이언트 미연결, 항목 폐기")
            item.cleanup_callback()
            return

        queue.is_playing = True
        logger.info(f"재생: '{item.text[:30]}'")

        def after_playing(error):
            if error:
                logger.error(f"재생 오류: {error}")
            else:
                logger.info("재생 완료")

            item.cleanup_callback()
            queue.is_playing = False

            if voice_client and voice_client.is_connected():
                asyncio.run_coroutine_threadsafe(
                    self.play_next(voice_client, guild_id),
                    voice_client.loop,
                )

        try:
            ffmpeg_options = None
            if item.effect != "none":
                ffmpeg_options = f"-af {item.effect}"
            audio_source = discord.FFmpegOpusAudio(
                item.source,
                pipe=True,
                options=ffmpeg_options,
            )
            voice_client.play(audio_source, after=after_playing)
        except Exception as e:
            logger.error(f"재생 시작 실패: {type(e).__name__}: {e}")
            item.cleanup_callback()
            queue.is_playing = False

    async def skip(self, voice_client: discord.VoiceClient, guild_id: int) -> bool:
        queue = self.get_queue(guild_id)

        if voice_client and voice_client.is_playing():
            voice_client.stop()  # after_playing 콜백이 호출됨
            return True
        return False

    async def clear_queue(self, guild_id: int) -> None:
        if guild_id in self.queues:
            queue = self.queues[guild_id]
            items = await queue.clear()
            for item in items:
                item.cleanup_callback()

    async def cleanup_guild(self, guild_id: int) -> None:
        await self.clear_queue(guild_id)
        if guild_id in self.queues:
            del self.queues[guild_id]
