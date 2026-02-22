import discord
from discord import app_commands
from discord.ext import commands

from config import (
    VOICE_PRESETS, AUDIO_EFFECT_PRESETS,
    DEFAULT_VOICE, DEFAULT_RATE, DEFAULT_PITCH, DEFAULT_EFFECT,
)


# --- 속도 / 피치 프리셋 ---

SPEED_PRESETS = [
    ("-50%", "-50%"),
    ("-25%", "-25%"),
    ("+0% (기본)", "+0%"),
    ("+25%", "+25%"),
    ("+50%", "+50%"),
    ("+75%", "+75%"),
    ("+100%", "+100%"),
]

PITCH_PRESETS = [
    ("-50Hz", "-50Hz"),
    ("-25Hz", "-25Hz"),
    ("+0Hz (기본)", "+0Hz"),
    ("+10Hz", "+10Hz"),
    ("+25Hz", "+25Hz"),
    ("+50Hz", "+50Hz"),
]

EFFECT_PRESETS = list(AUDIO_EFFECT_PRESETS.items())


# --- UI 컴포넌트 ---

class VoiceSelect(discord.ui.Select):
    """음성 선택 드롭다운."""

    def __init__(self, current_voice: str):
        options = []
        for name, voice_id in VOICE_PRESETS.items():
            if voice_id.startswith("sovits:"):
                desc = "캐릭터 음성"
            elif voice_id.startswith("gtts:"):
                desc = "구글 번역기"
            else:
                desc = "Edge TTS"
            options.append(
                discord.SelectOption(
                    label=name,
                    description=desc,
                    value=voice_id,
                    default=(voice_id == current_voice),
                )
            )
        super().__init__(
            placeholder="음성 선택",
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.selected_voice = self.values[0]
        await interaction.response.defer()


class SpeedSelect(discord.ui.Select):
    """속도 선택 드롭다운."""

    def __init__(self, current_rate: str):
        options = []
        for label, value in SPEED_PRESETS:
            options.append(
                discord.SelectOption(
                    label=label,
                    value=value,
                    default=(value == current_rate),
                )
            )
        super().__init__(
            placeholder="속도 선택",
            options=options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.selected_rate = self.values[0]
        await interaction.response.defer()


class PitchSelect(discord.ui.Select):
    """피치 선택 드롭다운."""

    def __init__(self, current_pitch: str):
        options = []
        for label, value in PITCH_PRESETS:
            options.append(
                discord.SelectOption(
                    label=label,
                    value=value,
                    default=(value == current_pitch),
                )
            )
        super().__init__(
            placeholder="피치 선택",
            options=options,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.selected_pitch = self.values[0]
        await interaction.response.defer()


class ConfirmButton(discord.ui.Button):
    """음성 설정 저장 버튼."""

    def __init__(self):
        super().__init__(
            label="저장",
            style=discord.ButtonStyle.primary,
            row=4,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view: VoiceSettingsView = self.view
        user_settings = view.bot.user_settings

        user_settings.set_user_voice(
            user_id=interaction.user.id,
            voice=view.selected_voice,
            rate=view.selected_rate,
            pitch=view.selected_pitch,
            effect=view.selected_effect,
        )

        # 음성 표시 이름 찾기
        voice_name = view.selected_voice
        for name, vid in VOICE_PRESETS.items():
            if vid == view.selected_voice:
                voice_name = f"{name} ({vid})"
                break

        await interaction.response.edit_message(
            content=(
                f"**음성 설정이 저장되었습니다**\n"
                f"• 음성: {voice_name}\n"
                f"• 속도: {view.selected_rate}\n"
                f"• 피치: {view.selected_pitch}\n"
                f"• 효과: {view.effect_label_map.get(view.selected_effect, view.selected_effect)}"
            ),
            view=None,
        )
        view.stop()


class EffectSelect(discord.ui.Select):
    """효과 선택 드롭다운."""

    def __init__(self, current_effect: str):
        options = []
        for label, value in EFFECT_PRESETS:
            options.append(
                discord.SelectOption(
                    label=label,
                    value=value,
                    default=(value == current_effect),
                )
            )
        super().__init__(
            placeholder="효과 선택",
            options=options,
            row=3,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.selected_effect = self.values[0]
        await interaction.response.defer()


class VoiceSettingsView(discord.ui.View):
    """음성, 속도, 피치 드롭다운이 있는 설정 뷰."""

    def __init__(self, bot: commands.Bot, user_id: int):
        super().__init__(timeout=120)
        self.bot = bot

        settings = bot.user_settings.get_user_settings(user_id)
        self.selected_voice = settings.get("voice", DEFAULT_VOICE)
        self.selected_rate = settings.get("rate", DEFAULT_RATE)
        self.selected_pitch = settings.get("pitch", DEFAULT_PITCH)
        self.selected_effect = settings.get("effect", DEFAULT_EFFECT)
        self.effect_label_map = {value: label for label, value in EFFECT_PRESETS}

        self.add_item(VoiceSelect(self.selected_voice))
        self.add_item(SpeedSelect(self.selected_rate))
        self.add_item(PitchSelect(self.selected_pitch))
        self.add_item(EffectSelect(self.selected_effect))
        self.add_item(ConfirmButton())

    async def on_timeout(self) -> None:
        pass


# --- Cog ---

class TTSCog(commands.Cog):
    """TTS 재생 명령어."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="스킵", description="현재 재생 중인 TTS를 건너뜁니다")
    async def skip(self, interaction: discord.Interaction) -> None:
        """현재 TTS 재생을 건너뛴다."""
        if not interaction.guild:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        voice_client = interaction.guild.voice_client
        if not voice_client:
            await interaction.response.send_message(
                "판구리가 음성 채널에 연결되어 있지 않습니다.",
                ephemeral=True,
            )
            return

        audio_manager = self.bot.audio_manager
        skipped = await audio_manager.skip(voice_client, interaction.guild.id)

        if skipped:
            await interaction.response.send_message("건너뛰었습니다.")
        else:
            await interaction.response.send_message(
                "현재 재생 중인 항목이 없습니다.",
                ephemeral=True,
            )

    @app_commands.command(name="목소리", description="TTS 음성/속도/피치/효과를 설정합니다")
    async def voice_settings(self, interaction: discord.Interaction) -> None:
        """음성 설정 UI를 표시한다."""
        view = VoiceSettingsView(self.bot, interaction.user.id)

        settings = self.bot.user_settings.get_user_settings(interaction.user.id)
        voice_id = settings.get("voice", DEFAULT_VOICE)
        effect_id = settings.get("effect", DEFAULT_EFFECT)
        voice_name = voice_id
        effect_name = effect_id
        for name, vid in VOICE_PRESETS.items():
            if vid == voice_id:
                voice_name = f"{name} ({vid})"
                break
        for name, value in EFFECT_PRESETS:
            if value == effect_id:
                effect_name = name
                break

        await interaction.response.send_message(
            f"**현재 음성 설정**\n"
            f"• 음성: {voice_name}\n"
            f"• 속도: {settings.get('rate', DEFAULT_RATE)}\n"
            f"• 피치: {settings.get('pitch', DEFAULT_PITCH)}\n"
            f"• 효과: {effect_name}\n\n"
            f"아래 메뉴에서 변경 후 **저장** 버튼을 눌러주세요.",
            view=view,
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TTSCog(bot))
