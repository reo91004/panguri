import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger("tts-bot.voice")


class VoiceCog(commands.Cog):
    """음성 채널 관리 명령어."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="입장", description="판구리를 음성 채널에 참가시키고 현재 채널을 자동읽기로 설정합니다")
    async def join(self, interaction: discord.Interaction) -> None:
        """사용자의 음성 채널에 참가하고 현재 텍스트 채널을 자동읽기로 설정한다."""
        if not interaction.guild:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        member = interaction.guild.get_member(interaction.user.id)
        if not member or not member.voice or not member.voice.channel:
            await interaction.response.send_message(
                "먼저 음성 채널에 접속해주세요.",
                ephemeral=True,
            )
            return

        voice_channel = member.voice.channel

        # 이미 연결되어 있는지 확인
        voice_client = interaction.guild.voice_client
        if voice_client:
            if voice_client.channel == voice_channel:
                await interaction.response.send_message(
                    "이미 같은 음성 채널에 있습니다.",
                    ephemeral=True,
                )
                return
            # 다른 채널로 이동
            await voice_client.move_to(voice_channel)
        else:
            # 채널에 연결
            await voice_channel.connect()

        # 현재 텍스트 채널을 자동읽기로 등록
        user_settings = self.bot.user_settings
        channel_id = interaction.channel_id
        if channel_id:
            if not user_settings.is_auto_read_channel(interaction.guild.id, channel_id):
                user_settings.add_auto_read_channel(interaction.guild.id, channel_id)
                logger.info(f"자동읽기 등록: 채널 {channel_id} (서버 {interaction.guild.id})")

        await interaction.response.send_message(
            f"**{voice_channel.name}**에 참가했습니다.\n"
            f"이 채널의 메시지를 자동으로 읽습니다."
        )

    @app_commands.command(name="퇴장", description="판구리를 음성 채널에서 퇴장시킵니다")
    async def leave(self, interaction: discord.Interaction) -> None:
        """음성 채널에서 퇴장하고 자동읽기 채널을 초기화한다."""
        if not interaction.guild:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        voice_client = interaction.guild.voice_client
        if not voice_client:
            await interaction.response.send_message(
                "현재 음성 채널에 연결되어 있지 않습니다.",
                ephemeral=True,
            )
            return

        # 오디오 큐 정리
        audio_manager = self.bot.audio_manager
        await audio_manager.cleanup_guild(interaction.guild.id)

        # 해당 서버의 자동읽기 채널 전부 제거
        user_settings = self.bot.user_settings
        for cid in list(user_settings.get_auto_read_channels(interaction.guild.id)):
            user_settings.remove_auto_read_channel(interaction.guild.id, cid)

        await voice_client.disconnect()
        await interaction.response.send_message("음성 채널에서 퇴장했습니다.")

    @app_commands.command(name="채팅지정", description="이 채널을 지정하면 메시지가 올라올 때 판구리가 자동으로 음성 채널에 참가합니다")
    async def designate_channel(self, interaction: discord.Interaction) -> None:
        """텍스트 채널을 지정채널로 토글한다."""
        if not interaction.guild:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        channel_id = interaction.channel_id
        if not channel_id:
            await interaction.response.send_message(
                "채널 정보를 가져올 수 없습니다.",
                ephemeral=True,
            )
            return

        user_settings = self.bot.user_settings
        enabled = user_settings.toggle_designated_channel(interaction.guild.id, channel_id)

        if enabled:
            logger.info(f"지정채널 설정: 채널 {channel_id} (서버 {interaction.guild.id})")
            await interaction.response.send_message(
                "이 채널이 **지정채널**로 설정되었습니다.\n"
                "메시지를 보내면 판구리가 자동으로 음성 채널에 참가하여 읽어줍니다."
            )
        else:
            logger.info(f"지정채널 해제: 채널 {channel_id} (서버 {interaction.guild.id})")
            await interaction.response.send_message(
                "이 채널의 **지정채널** 설정이 해제되었습니다."
            )

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """음성 상태 변경 감지 — 사람이 모두 나가면 즉시 퇴장."""
        # 봇 자신의 상태 변경은 무시
        if member.id == self.bot.user.id:
            return

        voice_client = member.guild.voice_client
        if not voice_client:
            return

        # 봇이 혼자 남았는지 확인
        bot_channel = voice_client.channel
        members_in_channel = [m for m in bot_channel.members if not m.bot]

        if len(members_in_channel) == 0:
            # 즉시 정리 및 퇴장
            await self._auto_leave_now(member.guild.id, voice_client)

    async def _auto_leave_now(
        self,
        guild_id: int,
        voice_client: discord.VoiceClient,
    ) -> None:
        """오디오 큐를 정리하고 즉시 음성 채널에서 퇴장한다."""
        if not voice_client.is_connected():
            return

        # 오디오 큐 정리
        audio_manager = self.bot.audio_manager
        await audio_manager.cleanup_guild(guild_id)

        # 자동읽기 채널 제거
        user_settings = self.bot.user_settings
        for cid in list(user_settings.get_auto_read_channels(guild_id)):
            user_settings.remove_auto_read_channel(guild_id, cid)

        await voice_client.disconnect()
        logger.info(f"사람이 없어 즉시 퇴장 (서버 {guild_id})")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceCog(bot))
