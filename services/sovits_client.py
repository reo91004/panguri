import json
import logging
from pathlib import Path

import aiohttp

from config import DATA_DIR, SOVITS_API_URL, SOVITS_REQUEST_TIMEOUT

logger = logging.getLogger("tts-bot.sovits")


class SoVITSClient:
    """GPT-SoVITS HTTP API 클라이언트."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._characters: dict[str, dict] = {}
        self._load_characters()

    def _load_characters(self) -> None:
        """data/characters.json에서 캐릭터 설정을 로드한다."""
        characters_file = DATA_DIR / "characters.json"
        if not characters_file.exists():
            return
        try:
            with open(characters_file, "r", encoding="utf-8") as f:
                self._characters = json.load(f)
            logger.info(f"캐릭터 {len(self._characters)}개 로드됨")
        except Exception as e:
            logger.warning(f"characters.json 로드 실패: {e}")

    def _get_session(self) -> aiohttp.ClientSession:
        """aiohttp 세션을 lazy 생성한다."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=SOVITS_REQUEST_TIMEOUT)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def get_character(self, character_id: str) -> dict | None:
        """캐릭터 ID로 설정을 반환한다."""
        return self._characters.get(character_id)

    def get_all_characters(self) -> dict[str, dict]:
        """모든 캐릭터 설정을 반환한다."""
        return self._characters

    async def health_check(self) -> bool:
        """GPT-SoVITS 서버 가용성을 확인한다."""
        try:
            session = self._get_session()
            async with session.get(SOVITS_API_URL, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200 or resp.status == 400
        except Exception:
            return False

    async def synthesize(self, text: str, character_id: str) -> bytes:
        """텍스트를 GPT-SoVITS로 합성하여 WAV 바이트를 반환한다.

        실패 시 RuntimeError를 raise한다.
        """
        char = self._characters.get(character_id)
        if not char:
            raise RuntimeError(f"알 수 없는 캐릭터: {character_id}")

        params = {
            "refer_wav_path": char["refer_wav_path"],
            "prompt_text": char["prompt_text"],
            "prompt_language": char.get("prompt_language", "ko"),
            "text": text,
            "text_language": char.get("text_language", "ko"),
        }

        try:
            session = self._get_session()
            async with session.get(SOVITS_API_URL, params=params) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(
                        f"GPT-SoVITS 오류 (HTTP {resp.status}): {body[:200]}"
                    )
                data = await resp.read()
                if not data:
                    raise RuntimeError("GPT-SoVITS가 빈 응답을 반환했습니다")
                logger.info(f"SoVITS 합성 완료: {character_id} ({len(data)} bytes)")
                return data
        except aiohttp.ClientError as e:
            raise RuntimeError(f"GPT-SoVITS 연결 실패: {e}") from e

    async def close(self) -> None:
        """aiohttp 세션을 정리한다."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
