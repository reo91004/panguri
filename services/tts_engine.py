import asyncio
import hashlib
import io
import logging
import os
import re
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Callable, Optional

import edge_tts
from gtts import gTTS

from config import (
    TEMP_DIR, DEFAULT_LANGUAGE, DEFAULT_SLOW,
    DEFAULT_VOICE, DEFAULT_RATE, DEFAULT_PITCH,
    KOREAN_ABBREVIATIONS, KOREAN_REPEATED_JAMO,
    KOREAN_JAMO_READINGS, AUDIO_CACHE_MAX_SIZE, AUDIO_CACHE_MAX_BYTES,
    STANDALONE_PUNCTUATION,
)

logger = logging.getLogger("tts-bot.engine")

# 같은 한글 자음이 2회 이상 반복되는 패턴
_REPEATED_JAMO_RE = re.compile(r"([ㄱ-ㅎ])\1+")
# 초성/중성만으로 구성된 시퀀스 패턴
_JAMO_SEQUENCE_RE = re.compile(r"[ㄱ-ㅎㅏ-ㅣ]+")


class AudioCache:
    """항목 수 및 바이트 크기 제한이 있는 LRU 오디오 캐시."""

    def __init__(
        self,
        max_size: int = AUDIO_CACHE_MAX_SIZE,
        max_bytes: int = AUDIO_CACHE_MAX_BYTES,
    ):
        self._cache: OrderedDict[str, bytes] = OrderedDict()
        self._total_bytes = 0
        self._max_size = max_size
        self._max_bytes = max_bytes

    @staticmethod
    def _key(text: str, voice: str, rate: str, pitch: str) -> str:
        raw = f"{text}|{voice}|{rate}|{pitch}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, text: str, voice: str, rate: str, pitch: str) -> Optional[bytes]:
        key = self._key(text, voice, rate, pitch)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, text: str, voice: str, rate: str, pitch: str, data: bytes) -> None:
        key = self._key(text, voice, rate, pitch)
        if key in self._cache:
            self._total_bytes -= len(self._cache[key])
            del self._cache[key]

        self._cache[key] = data
        self._total_bytes += len(data)
        self._cache.move_to_end(key)
        self._evict()

    def _evict(self) -> None:
        while len(self._cache) > self._max_size or self._total_bytes > self._max_bytes:
            if not self._cache:
                break
            _, evicted = self._cache.popitem(last=False)
            self._total_bytes -= len(evicted)

    def clear(self) -> None:
        self._cache.clear()
        self._total_bytes = 0


class TTSEngine:
    """멀티 TTS 엔진 (edge-tts, gTTS) + LRU 캐시."""

    def __init__(self):
        self.temp_dir = TEMP_DIR
        self._cache = AudioCache()
        self._abbreviations = sorted(
            KOREAN_ABBREVIATIONS.items(), key=lambda kv: len(kv[0]), reverse=True
        )

    @staticmethod
    def _convert_standalone_punctuation(text: str) -> str:
        """단독 특수문자(같은 문자 반복 포함)를 읽기 형태로 치환한다.

        예: '?' → '물음표', '!!!' → '느낌표'
        문장 속 특수문자('안녕?')는 그대로 유지한다.
        """
        stripped = text.strip()
        if not stripped:
            return text
        char = stripped[0]
        if char in STANDALONE_PUNCTUATION and all(c == char for c in stripped):
            return STANDALONE_PUNCTUATION[char]
        return text

    @staticmethod
    def _normalize_repeated_jamo(text: str) -> str:
        """같은 한글 자음이 2회 이상 반복되면 읽기 형태로 치환한다.

        예: ㅋㅋㅋㅋㅋ → 크크크, ㅎㅎ → 흐흐흐
        1글자(ㅋ)는 변환하지 않는다.
        """
        def _replace(m: re.Match) -> str:
            jamo = m.group(1)
            return KOREAN_REPEATED_JAMO.get(jamo, jamo * 3)

        return _REPEATED_JAMO_RE.sub(_replace, text)

    def _apply_korean_abbreviations(self, text: str) -> str:
        for abbr, reading in self._abbreviations:
            text = text.replace(abbr, reading)
        return text

    @staticmethod
    def _convert_jamo_sequences(text: str) -> str:
        """남아있는 초성/중성 시퀀스를 읽기 형태로 변환한다.

        예: ㄲㅂ -> 쌍기역 비읍, ㅗㅐ -> 오 애
        """
        def _replace(m: re.Match) -> str:
            seq = m.group(0)
            readings = [KOREAN_JAMO_READINGS.get(ch, ch) for ch in seq]
            return " ".join(readings)

        return _JAMO_SEQUENCE_RE.sub(_replace, text)

    async def synthesize(
        self,
        text: str,
        lang: str = DEFAULT_LANGUAGE,
        slow: bool = DEFAULT_SLOW,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
    ) -> tuple[io.IOBase, Callable]:
        """텍스트를 음성으로 변환한다.

        voice ID 접두사로 엔진을 선택한다:
        - 접두사 없음 → edge-tts (기본, 하위 호환)
        - "gtts:"     → gTTS

        반환값:
            (source, cleanup_callback) — source는 FFmpegOpusAudio(pipe=True)로
            읽을 수 있는 파일류 객체이고, cleanup_callback은 리소스를 정리하는 함수.
        """
        # 단독 특수문자 → 반복 자음 정규화 (정규식) → 약어 치환 (사전) 순서로 처리
        text = self._convert_standalone_punctuation(text)
        text = self._normalize_repeated_jamo(text)
        text = self._apply_korean_abbreviations(text)
        text = self._convert_jamo_sequences(text)
        voice = voice or DEFAULT_VOICE
        rate = rate or DEFAULT_RATE
        pitch = pitch or DEFAULT_PITCH

        # 접두사 기반 엔진 디스패치
        if voice.startswith("gtts:"):
            return await self._synthesize_gtts_primary(text, lang=voice[5:])

        # edge-tts (기본)
        # 1) 캐시 히트 — 즉시 반환
        cached = self._cache.get(text, voice, rate, pitch)
        if cached is not None:
            logger.info("캐시 히트, BytesIO 반환")
            buf = io.BytesIO(cached)
            return buf, lambda: None

        # 2) edge-tts 스트리밍 (os.pipe 사용)
        try:
            source, cleanup = await self._synthesize_edge_streaming(
                text, voice, rate, pitch,
            )
            return source, cleanup
        except Exception as e:
            logger.warning(f"edge-tts 스트리밍 실패, gTTS로 폴백: {e}")

        # 3) gTTS 파일 기반 폴백
        return await self._gtts_file_fallback(text, lang, slow)

    async def _synthesize_edge_streaming(
        self,
        text: str,
        voice: str,
        rate: str,
        pitch: str,
    ) -> tuple[io.IOBase, Callable]:
        """edge-tts 오디오를 OS 파이프를 통해 스트리밍한다.

        백그라운드 태스크가 파이프의 쓰기 끝에 오디오 청크를 쓰고,
        읽기 끝은 FFmpeg가 소비할 수 있도록 즉시 반환된다.
        """
        read_fd, write_fd = os.pipe()

        writer_task: asyncio.Task | None = None
        has_audio = asyncio.Event()
        writer_done = asyncio.Event()
        writer_error: Exception | None = None

        async def _writer():
            nonlocal writer_error
            collected = bytearray()
            loop = asyncio.get_event_loop()
            success = False
            try:
                communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        data = chunk["data"]
                        if data and not has_audio.is_set():
                            has_audio.set()
                        collected.extend(data)
                        await loop.run_in_executor(None, os.write, write_fd, data)
                success = True
            except Exception as e:
                writer_error = e
                logger.error(f"edge-tts 스트리밍 작성 오류: {e}")
            finally:
                try:
                    os.close(write_fd)
                except OSError:
                    pass
                if success and collected:
                    self._cache.put(text, voice, rate, pitch, bytes(collected))
                writer_done.set()

        writer_task = asyncio.create_task(_writer())
        read_file = os.fdopen(read_fd, "rb")

        # 재생 시작 전에 최소 1개 오디오 청크 수신 여부를 확인한다.
        wait_audio_task = asyncio.create_task(has_audio.wait())
        wait_done_task = asyncio.create_task(writer_done.wait())
        done, pending = await asyncio.wait(
            {wait_audio_task, wait_done_task},
            return_when=asyncio.FIRST_COMPLETED,
            timeout=5,
        )
        for task in pending:
            task.cancel()

        if wait_audio_task not in done:
            try:
                read_file.close()
            except OSError:
                pass
            if writer_task and not writer_task.done():
                writer_task.cancel()
            if wait_done_task in done and writer_error is not None:
                raise RuntimeError(str(writer_error)) from writer_error
            raise RuntimeError("No audio was received from edge-tts.")

        def _cleanup():
            try:
                read_file.close()
            except OSError:
                pass
            if writer_task and not writer_task.done():
                writer_task.cancel()

        return read_file, _cleanup

    async def _gtts_file_fallback(
        self, text: str, lang: str, slow: bool,
    ) -> tuple[io.IOBase, Callable]:
        """gTTS 파일 기반 폴백."""
        filepath = self.temp_dir / f"{uuid.uuid4()}.mp3"
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self._synthesize_gtts, text, lang, slow, filepath,
        )
        fh = open(filepath, "rb")

        def _cleanup():
            try:
                fh.close()
            except OSError:
                pass
            try:
                filepath.unlink(missing_ok=True)
            except OSError:
                pass

        return fh, _cleanup

    async def _synthesize_gtts_primary(
        self, text: str, lang: str,
    ) -> tuple[io.IOBase, Callable]:
        """gTTS를 기본 엔진으로 사용 (구글 번역기 음성)."""
        cache_voice = f"gtts:{lang}"
        cached = self._cache.get(text, cache_voice, "", "")
        if cached is not None:
            logger.info("gTTS 캐시 히트")
            return io.BytesIO(cached), lambda: None

        try:
            filepath = self.temp_dir / f"{uuid.uuid4()}.mp3"
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._synthesize_gtts, text, lang, False, filepath,
            )
            data = filepath.read_bytes()
            filepath.unlink(missing_ok=True)
            self._cache.put(text, cache_voice, "", "", data)
            return io.BytesIO(data), lambda: None
        except Exception as e:
            logger.warning(f"gTTS 실패, edge-tts 기본 음성으로 폴백: {e}")
            return await self._edge_fallback(text)

    async def _edge_fallback(
        self, text: str,
    ) -> tuple[io.IOBase, Callable]:
        """다른 엔진 실패 시 edge-tts 기본 음성으로 폴백."""
        voice = DEFAULT_VOICE
        rate = DEFAULT_RATE
        pitch = DEFAULT_PITCH

        cached = self._cache.get(text, voice, rate, pitch)
        if cached is not None:
            return io.BytesIO(cached), lambda: None

        try:
            return await self._synthesize_edge_streaming(text, voice, rate, pitch)
        except Exception as e:
            logger.warning(f"edge-tts 폴백도 실패, gTTS 최종 폴백: {e}")
            return await self._gtts_file_fallback(text, DEFAULT_LANGUAGE, False)

    def _synthesize_gtts(
        self,
        text: str,
        lang: str,
        slow: bool,
        filepath: Path,
    ) -> None:
        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(str(filepath))

    def cleanup_all(self) -> None:
        """모든 임시 오디오 파일을 삭제하고 캐시를 초기화한다."""
        for file in self.temp_dir.glob("*.mp3"):
            try:
                file.unlink()
            except OSError:
                pass
        self._cache.clear()
