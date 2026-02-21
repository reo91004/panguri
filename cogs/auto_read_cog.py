import asyncio
import io
import logging
import re

import discord
from discord.ext import commands

logger = logging.getLogger("tts-bot.autoread")

_USER_MENTION_RE = re.compile(r"<@!?(\d+)>")
_CUSTOM_EMOJI_RE = re.compile(r"<a?:\w+:\d+>")
_UNICODE_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # 이모티콘
    "\U0001F300-\U0001F5FF"  # 기호
    "\U0001F680-\U0001F6FF"  # 교통
    "\U0001F1E0-\U0001F1FF"  # 국기
    "\U0001F900-\U0001F9FF"  # 보충 기호
    "\U0001FA00-\U0001FAFF"  # 확장 기호
    "\U00002600-\U000027BF"  # 기타 기호
    "\U0000FE00-\U0000FE0F"  # 변형 선택자
    "\U0000200D"             # ZWJ
    "\U000020E3"             # 결합 기호
    "]+",
    flags=re.UNICODE,
)


class AutoReadCog(commands.Cog):
    """메시지 자동읽기 기능 (리스너 전용, 명령어 없음)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _preprocess_message(self, message: discord.Message) -> str | None:
        """메시지 내용을 TTS용으로 전처리한다.

        멘션 → 닉네임 치환, 이모지 제거, 이미지/이모지만 전송 시 안내 문구 반환.
        읽을 내용이 없으면 None을 반환한다.
        """
        text = message.content.strip()

        # 멘션 → 닉네임 치환
        def _replace_mention(m: re.Match) -> str:
            user_id = int(m.group(1))
            member = message.guild.get_member(user_id)
            return member.display_name if member else "알 수 없는 사용자"

        text = _USER_MENTION_RE.sub(_replace_mention, text)

        # 이모지 존재 여부 기록
        had_emoji = bool(_CUSTOM_EMOJI_RE.search(text) or _UNICODE_EMOJI_RE.search(text))

        # 이모지 제거
        text = _CUSTOM_EMOJI_RE.sub("", text)
        text = _UNICODE_EMOJI_RE.sub("", text)
        text = text.strip()

        # 빈 텍스트 처리
        if not text:
            has_image = any(
                a.content_type and a.content_type.startswith("image/")
                for a in message.attachments
            )
            if has_image:
                return "이미지를 보냈어요"
            if had_emoji:
                return "이모지를 보냈어요"
            return None

        return text

    async def _try_auto_join(self, message: discord.Message) -> discord.VoiceClient | None:
        """지정채널 메시지의 작성자 음성 채널에 자동 참가한다.

        성공 시 VoiceClient를 반환하고, 참가 불가 시 None을 반환한다.
        """
        member = message.guild.get_member(message.author.id)
        if not member or not member.voice or not member.voice.channel:
            return None

        voice_channel = member.voice.channel
        try:
            voice_client = await voice_channel.connect()
        except discord.ClientException:
            # 레이스 컨디션: 이미 연결됨
            voice_client = message.guild.voice_client
            if not voice_client or not voice_client.is_connected():
                return None

        # 세션 중 빠른 처리를 위해 자동읽기에도 등록
        user_settings = self.bot.user_settings
        if not user_settings.is_auto_read_channel(message.guild.id, message.channel.id):
            user_settings.add_auto_read_channel(message.guild.id, message.channel.id)

        logger.info(f"지정채널 자동참가: {voice_channel.name} (서버 {message.guild.id})")
        return voice_client

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """설정된 채널의 메시지를 자동으로 읽는다."""
        if message.author.bot:
            return

        if not message.guild:
            return

        user_settings = self.bot.user_settings
        is_auto_read = user_settings.is_auto_read_channel(message.guild.id, message.channel.id)
        is_designated = user_settings.is_designated_channel(message.guild.id, message.channel.id)

        if not is_auto_read and not is_designated:
            return

        voice_client = message.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            if is_designated:
                voice_client = await self._try_auto_join(message)
                if not voice_client:
                    return
            else:
                logger.debug("음성 클라이언트 미연결, 건너뜀")
                return

        text = self._preprocess_message(message)
        if text is None:
            return

        if text.startswith("/"):
            return

        if len(text) > 200:
            text = text[:200] + "..."

        logger.info(f"자동읽기: '{text[:30]}' (작성자: {message.author})")

        # 사용자 설정 가져오기
        lang = user_settings.get_user_language(message.author.id)
        slow = user_settings.get_user_slow(message.author.id)
        voice = user_settings.get_user_voice(message.author.id)
        rate = user_settings.get_user_rate(message.author.id)
        pitch = user_settings.get_user_pitch(message.author.id)
        effect = user_settings.get_user_effect(message.author.id)

        # TTS 생성
        tts_engine = self.bot.tts_engine
        try:
            source, cleanup_callback = await tts_engine.synthesize(
                text,
                lang=lang,
                slow=slow,
                voice=voice,
                rate=rate,
                pitch=pitch,
            )
            logger.info("TTS 소스 준비 완료")
        except Exception as e:
            logger.error(f"TTS 합성 실패: {e}")
            return

        # 큐가 사용 중이면 미리 버퍼링 (재생 간 텀 단축)
        audio_manager = self.bot.audio_manager
        guild_queue = audio_manager.get_queue(message.guild.id)
        if guild_queue.is_playing or len(guild_queue) > 0:
            try:
                loop = asyncio.get_running_loop()
                data = await loop.run_in_executor(None, source.read)
                cleanup_callback()
                source = io.BytesIO(data)
                cleanup_callback = lambda: None
            except Exception as e:
                logger.warning(f"프리버퍼링 실패, 스트리밍으로 폴백: {e}")

        # 큐에 추가 및 재생
        await audio_manager.add_to_queue(
            guild_id=message.guild.id,
            source=source,
            cleanup_callback=cleanup_callback,
            text=text,
            user_id=message.author.id,
            effect=effect,
        )
        await audio_manager.play_next(voice_client, message.guild.id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoReadCog(bot))
