import json
from pathlib import Path
from typing import Optional

from config import (
    DATA_DIR, DEFAULT_LANGUAGE, DEFAULT_SLOW,
    DEFAULT_VOICE, DEFAULT_RATE, DEFAULT_PITCH, DEFAULT_EFFECT,
    VOICE_PRESETS, AUDIO_EFFECT_PRESETS,
)


class UserSettings:
    """사용자 및 서버 TTS 설정을 관리한다."""

    def __init__(self):
        self.settings_file = DATA_DIR / "user_settings.json"
        self.auto_read_file = DATA_DIR / "auto_read.json"
        self.designated_file = DATA_DIR / "designated_channels.json"
        self._user_settings: dict = {}
        self._auto_read_channels: dict = {}
        self._designated_channels: dict = {}
        self._load()

    def _load(self) -> None:
        """JSON 파일에서 설정을 불러온다."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    self._user_settings = json.load(f)
            except json.JSONDecodeError:
                self._user_settings = {}

        if self.auto_read_file.exists():
            try:
                with open(self.auto_read_file, "r", encoding="utf-8") as f:
                    self._auto_read_channels = json.load(f)
            except json.JSONDecodeError:
                self._auto_read_channels = {}

        if self.designated_file.exists():
            try:
                with open(self.designated_file, "r", encoding="utf-8") as f:
                    self._designated_channels = json.load(f)
            except json.JSONDecodeError:
                self._designated_channels = {}

    def _save_user_settings(self) -> None:
        """사용자 설정을 JSON에 저장한다."""
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(self._user_settings, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _normalize_voice(voice: str) -> str:
        """지원하지 않는 음성 ID를 기본값으로 정규화한다."""
        if voice in VOICE_PRESETS.values():
            return voice
        return DEFAULT_VOICE

    @staticmethod
    def _normalize_effect(effect: str) -> str:
        """지원하지 않는 효과 ID를 기본값으로 정규화한다."""
        valid_effects = set(AUDIO_EFFECT_PRESETS.values())
        if effect in valid_effects:
            return effect
        return DEFAULT_EFFECT

    def _save_auto_read(self) -> None:
        """자동읽기 설정을 JSON에 저장한다."""
        with open(self.auto_read_file, "w", encoding="utf-8") as f:
            json.dump(self._auto_read_channels, f, ensure_ascii=False, indent=2)

    # --- 사용자 언어/느린말 설정 ---

    def get_user_language(self, user_id: int) -> str:
        """사용자의 선호 언어를 반환한다."""
        user_key = str(user_id)
        if user_key in self._user_settings:
            return self._user_settings[user_key].get("language", DEFAULT_LANGUAGE)
        return DEFAULT_LANGUAGE

    def get_user_slow(self, user_id: int) -> bool:
        """사용자의 느린말 설정을 반환한다."""
        user_key = str(user_id)
        if user_key in self._user_settings:
            return self._user_settings[user_key].get("slow", DEFAULT_SLOW)
        return DEFAULT_SLOW

    # --- 사용자 음성/속도/피치 설정 ---

    def get_user_voice(self, user_id: int) -> str:
        """사용자의 선호 edge-tts 음성을 반환한다."""
        user_key = str(user_id)
        if user_key in self._user_settings:
            voice = self._user_settings[user_key].get("voice", DEFAULT_VOICE)
            normalized = self._normalize_voice(voice)
            if normalized != voice:
                self._user_settings[user_key]["voice"] = normalized
                self._save_user_settings()
            return normalized
        return DEFAULT_VOICE

    def get_user_rate(self, user_id: int) -> str:
        """사용자의 선호 말하기 속도를 반환한다."""
        user_key = str(user_id)
        if user_key in self._user_settings:
            return self._user_settings[user_key].get("rate", DEFAULT_RATE)
        return DEFAULT_RATE

    def get_user_pitch(self, user_id: int) -> str:
        """사용자의 선호 피치를 반환한다."""
        user_key = str(user_id)
        if user_key in self._user_settings:
            return self._user_settings[user_key].get("pitch", DEFAULT_PITCH)
        return DEFAULT_PITCH

    def get_user_effect(self, user_id: int) -> str:
        """사용자의 음성 효과를 반환한다."""
        user_key = str(user_id)
        if user_key in self._user_settings:
            effect = self._user_settings[user_key].get("effect", DEFAULT_EFFECT)
            normalized = self._normalize_effect(effect)
            if normalized != effect:
                self._user_settings[user_key]["effect"] = normalized
                self._save_user_settings()
            return normalized
        return DEFAULT_EFFECT

    def set_user_voice(
        self,
        user_id: int,
        language: Optional[str] = None,
        slow: Optional[bool] = None,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        effect: Optional[str] = None,
    ) -> dict:
        """사용자 음성 설정을 저장한다."""
        user_key = str(user_id)

        if user_key not in self._user_settings:
            self._user_settings[user_key] = {
                "language": DEFAULT_LANGUAGE,
                "slow": DEFAULT_SLOW,
                "voice": DEFAULT_VOICE,
                "rate": DEFAULT_RATE,
                "pitch": DEFAULT_PITCH,
                "effect": DEFAULT_EFFECT,
            }

        if language is not None:
            self._user_settings[user_key]["language"] = language
        if slow is not None:
            self._user_settings[user_key]["slow"] = slow
        if voice is not None:
            self._user_settings[user_key]["voice"] = self._normalize_voice(voice)
        if rate is not None:
            self._user_settings[user_key]["rate"] = rate
        if pitch is not None:
            self._user_settings[user_key]["pitch"] = pitch
        if effect is not None:
            self._user_settings[user_key]["effect"] = self._normalize_effect(effect)

        self._save_user_settings()
        return self._user_settings[user_key]

    def get_user_settings(self, user_id: int) -> dict:
        """사용자의 전체 설정을 반환한다."""
        user_key = str(user_id)
        settings = self._user_settings.get(
            user_key,
            {
                "language": DEFAULT_LANGUAGE,
                "slow": DEFAULT_SLOW,
                "voice": DEFAULT_VOICE,
                "rate": DEFAULT_RATE,
                "pitch": DEFAULT_PITCH,
                "effect": DEFAULT_EFFECT,
            },
        ).copy()

        normalized_voice = self._normalize_voice(settings.get("voice", DEFAULT_VOICE))
        normalized_effect = self._normalize_effect(settings.get("effect", DEFAULT_EFFECT))
        updated = False

        if normalized_voice != settings.get("voice"):
            settings["voice"] = normalized_voice
            updated = True
        if normalized_effect != settings.get("effect"):
            settings["effect"] = normalized_effect
            updated = True

        if user_key in self._user_settings and updated:
            self._user_settings[user_key].update(settings)
            self._save_user_settings()

        return settings

    # --- 자동읽기 채널 관리 ---

    def is_auto_read_channel(self, guild_id: int, channel_id: int) -> bool:
        """해당 채널이 자동읽기로 설정되어 있는지 확인한다."""
        guild_key = str(guild_id)
        if guild_key in self._auto_read_channels:
            return channel_id in self._auto_read_channels[guild_key]
        return False

    def add_auto_read_channel(self, guild_id: int, channel_id: int) -> None:
        """자동읽기 채널을 추가한다."""
        guild_key = str(guild_id)
        if guild_key not in self._auto_read_channels:
            self._auto_read_channels[guild_key] = []

        if channel_id not in self._auto_read_channels[guild_key]:
            self._auto_read_channels[guild_key].append(channel_id)
            self._save_auto_read()

    def remove_auto_read_channel(self, guild_id: int, channel_id: int) -> bool:
        """자동읽기 채널을 제거한다. 제거된 경우 True 반환."""
        guild_key = str(guild_id)
        if guild_key in self._auto_read_channels:
            if channel_id in self._auto_read_channels[guild_key]:
                self._auto_read_channels[guild_key].remove(channel_id)
                self._save_auto_read()
                return True
        return False

    def get_auto_read_channels(self, guild_id: int) -> list[int]:
        """서버의 모든 자동읽기 채널을 반환한다."""
        guild_key = str(guild_id)
        return self._auto_read_channels.get(guild_key, [])

    def toggle_auto_read_channel(self, guild_id: int, channel_id: int) -> bool:
        """자동읽기를 토글한다. 활성화되면 True 반환."""
        if self.is_auto_read_channel(guild_id, channel_id):
            self.remove_auto_read_channel(guild_id, channel_id)
            return False
        else:
            self.add_auto_read_channel(guild_id, channel_id)
            return True

    # --- 지정채널 관리 ---

    def _save_designated(self) -> None:
        """지정채널 설정을 JSON에 저장한다."""
        with open(self.designated_file, "w", encoding="utf-8") as f:
            json.dump(self._designated_channels, f, ensure_ascii=False, indent=2)

    def is_designated_channel(self, guild_id: int, channel_id: int) -> bool:
        """해당 채널이 지정채널로 설정되어 있는지 확인한다."""
        guild_key = str(guild_id)
        if guild_key in self._designated_channels:
            return channel_id in self._designated_channels[guild_key]
        return False

    def add_designated_channel(self, guild_id: int, channel_id: int) -> None:
        """지정채널을 추가한다."""
        guild_key = str(guild_id)
        if guild_key not in self._designated_channels:
            self._designated_channels[guild_key] = []

        if channel_id not in self._designated_channels[guild_key]:
            self._designated_channels[guild_key].append(channel_id)
            self._save_designated()

    def remove_designated_channel(self, guild_id: int, channel_id: int) -> bool:
        """지정채널을 제거한다. 제거된 경우 True 반환."""
        guild_key = str(guild_id)
        if guild_key in self._designated_channels:
            if channel_id in self._designated_channels[guild_key]:
                self._designated_channels[guild_key].remove(channel_id)
                self._save_designated()
                return True
        return False

    def get_designated_channels(self, guild_id: int) -> list[int]:
        """서버의 모든 지정채널을 반환한다."""
        guild_key = str(guild_id)
        return self._designated_channels.get(guild_key, [])

    def toggle_designated_channel(self, guild_id: int, channel_id: int) -> bool:
        """지정채널을 토글한다. 활성화되면 True 반환."""
        if self.is_designated_channel(guild_id, channel_id):
            self.remove_designated_channel(guild_id, channel_id)
            return False
        else:
            self.add_designated_channel(guild_id, channel_id)
            return True
