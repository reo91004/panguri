import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import DISCORD_BOT_TOKEN
from services import TTSEngine, AudioManager, UserSettings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("tts-bot")


class TTSBot(commands.Bot):
    """판구리 — 디스코드 TTS 봇."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True

        super().__init__(
            command_prefix="!",
            intents=intents,
        )

        # 서비스 초기화
        self.user_settings = UserSettings()
        self.tts_engine = TTSEngine()
        self.audio_manager = AudioManager()
        self._synced = False

    async def setup_hook(self) -> None:
        """Cog 로드 및 오류 핸들러 설정."""
        cogs = [
            "cogs.voice_cog",
            "cogs.tts_cog",
            "cogs.auto_read_cog",
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Cog 로드 완료: {cog}")
            except Exception as e:
                logger.error(f"Cog 로드 실패 {cog}: {e}")

        # 오래된 캐시 명령어를 안전하게 처리
        @self.tree.error
        async def on_app_command_error(
            interaction: discord.Interaction,
            error: app_commands.AppCommandError,
        ):
            if isinstance(error, app_commands.CommandNotFound):
                await interaction.response.send_message(
                    "명령어가 업데이트되었습니다. 새 명령어를 사용해주세요:\n"
                    "`/입장` — 음성 채널 참가 + 자동읽기\n"
                    "`/퇴장` — 음성 채널 퇴장\n"
                    "`/채팅지정` — 지정채널 설정 (자동 참가)\n"
                    "`/스킵` — 현재 재생 건너뛰기\n"
                    "`/목소리` — 음성/속도/피치/효과 설정",
                    ephemeral=True,
                )
            else:
                logger.error(f"앱 명령어 오류: {error}")

    async def _sync_guild(self, guild: discord.Guild) -> None:
        """특정 서버에 슬래시 명령어를 동기화하여 즉시 사용 가능하게 한다."""
        try:
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info(f"명령어 {len(synced)}개 동기화 완료: {guild.name} ({guild.id})")
        except Exception as e:
            logger.error(f"명령어 동기화 실패 ({guild.name}): {e}")

    async def on_ready(self) -> None:
        """봇 준비 완료 시 호출."""
        logger.info(f"로그인 완료: {self.user} (ID: {self.user.id})")
        logger.info(f"연결된 서버: {len(self.guilds)}개")

        if not self._synced:
            # 각 서버에 명령어 동기화 (즉시 사용 가능)
            for guild in self.guilds:
                await self._sync_guild(guild)

            # 오래된 전역 명령어 제거
            # (트리 상태 저장 → 초기화 → 빈 상태 동기화 → 복원)
            global_cmds = self.tree.get_commands()
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
            for cmd in global_cmds:
                self.tree.add_command(cmd)

            self._synced = True

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/입장",
            )
        )

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """새 서버 참가 시 명령어 동기화."""
        await self._sync_guild(guild)

    async def close(self) -> None:
        """종료 시 정리."""
        logger.info("종료 중...")

        for vc in self.voice_clients:
            await vc.disconnect()

        self.tts_engine.cleanup_all()
        await super().close()


async def main() -> None:
    """메인 진입점."""
    if not DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN이 .env 파일에 설정되지 않았습니다")
        return

    bot = TTSBot()

    try:
        await bot.start(DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        await bot.close()
    except Exception as e:
        logger.error(f"봇 오류: {e}")
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
