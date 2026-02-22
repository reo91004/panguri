import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 봇 설정
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# GPT-SoVITS 설정
SOVITS_API_URL = os.getenv("SOVITS_API_URL", "http://localhost:9880")
SOVITS_REQUEST_TIMEOUT = float(os.getenv("SOVITS_REQUEST_TIMEOUT", "30"))

# 경로
BASE_DIR = Path(__file__).parent
TEMP_DIR = BASE_DIR / "temp"
DATA_DIR = BASE_DIR / "data"

# 디렉토리 생성
TEMP_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# TTS 설정
DEFAULT_LANGUAGE = "ko"
DEFAULT_SLOW = False

# edge-tts 기본값
DEFAULT_VOICE = "ko-KR-SunHiNeural"
DEFAULT_RATE = "+0%"
DEFAULT_PITCH = "+0Hz"
DEFAULT_EFFECT = "none"

# 음성 프리셋 (표시 이름 → 엔진 접두사:음성 ID)
# 접두사 없음 = edge-tts, "gtts:" = gTTS
VOICE_PRESETS = {
    # ── 한국어 (Edge TTS) ──
    "선희": "ko-KR-SunHiNeural",
    "인준": "ko-KR-InJoonNeural",
    "현수": "ko-KR-HyunsuMultilingualNeural",

    # ── 구글 번역기 ──
    "구글 번역기": "gtts:ko",
}

# 오디오 효과 프리셋 (FFmpeg -af 옵션)
# "none"은 원본 음성(효과 없음)
AUDIO_EFFECT_PRESETS = {
    "기본": "none",
    "하이톤": "asetrate=44100*1.25,atempo=0.90",
    "저음": "asetrate=44100*0.85,atempo=1.10",
    "라디오": "highpass=f=250,lowpass=f=3200,acompressor=threshold=-18dB:ratio=3",
    "메가폰": "highpass=f=500,lowpass=f=2400,volume=1.6",
    "에코": "aecho=0.8:0.88:60:0.4",
}

# 지원 언어
SUPPORTED_LANGUAGES = {
    "ko": "한국어",
}

# 오디오 캐시 설정
AUDIO_CACHE_MAX_SIZE = 100                  # 최대 캐시 항목 수
AUDIO_CACHE_MAX_BYTES = 10 * 1024 * 1024    # 최대 캐시 크기 (10 MB)

# 단독 특수문자 → 읽기 형태 매핑 (단독 전송 시만 적용)
STANDALONE_PUNCTUATION = {
    "?": "물음표",
    "!": "느낌표",
}

# 한글 반복 자음 → 읽기 형태 매핑 (정규식으로 처리)
KOREAN_REPEATED_JAMO = {
    "ㅋ": "크크크",
    "ㅎ": "흐흐흐",
    "ㅇ": "응응응",
    "ㄷ": "덜덜덜",
    "ㄱ": "기기기",
    "ㅂ": "비비비",
    "ㅈ": "지지지",
    "ㅅ": "시시시",
}

# 단독 초성/중성을 안전하게 읽기 위한 매핑
KOREAN_JAMO_READINGS = {
    "ㄱ": "기역",
    "ㄲ": "쌍기역",
    "ㄴ": "니은",
    "ㄷ": "디귿",
    "ㄸ": "쌍디귿",
    "ㄹ": "리을",
    "ㅁ": "미음",
    "ㅂ": "비읍",
    "ㅃ": "쌍비읍",
    "ㅅ": "시옷",
    "ㅆ": "쌍시옷",
    "ㅇ": "이응",
    "ㅈ": "지읒",
    "ㅉ": "쌍지읒",
    "ㅊ": "치읓",
    "ㅋ": "키읔",
    "ㅌ": "티읕",
    "ㅍ": "피읖",
    "ㅎ": "히읗",
    "ㅏ": "아",
    "ㅐ": "애",
    "ㅑ": "야",
    "ㅒ": "얘",
    "ㅓ": "어",
    "ㅔ": "에",
    "ㅕ": "여",
    "ㅖ": "예",
    "ㅗ": "오",
    "ㅘ": "와",
    "ㅙ": "왜",
    "ㅚ": "외",
    "ㅛ": "요",
    "ㅜ": "우",
    "ㅝ": "워",
    "ㅞ": "웨",
    "ㅟ": "위",
    "ㅠ": "유",
    "ㅡ": "으",
    "ㅢ": "의",
    "ㅣ": "이",
}

# 한국어 줄임말 사전 (긴 것부터 정렬하여 안전하게 치환)
KOREAN_ABBREVIATIONS: dict[str, str] = {
    "ㅇㅋ": "오케이",
    "ㄱㅅ": "감사",
    "ㅈㅅ": "죄송",
    "ㅈㄱ": "조용",
    "ㅎㅇ": "하이",
    "ㅊㅋ": "축하",
    "ㄱㄷ": "기다려",
    "ㅇㄷ": "어디",
    "ㅁㅊ": "미쳤",
    "ㄹㅇ": "리얼",
    "ㅇㅈ": "인정",
    "ㅈㅂ": "잠봐",
    "ㄱㅊ": "괜찮아",
    "ㅅㄱ": "수고",
    "ㅂㅅ": "뻘소리",
    "ㅇㄱㄹㅇ": "이거레알",
    "ㅇㅈㄹㄱ": "어쩌라고",
    "ㅇㅉㄹㄱ": "어쩌라고",
    "ㄱㅅㄱㅅ": "감사감사",
    "ㅂㄷㅂㄷ": "부들부들",
    "ㅈㄹ": "지랄",
    "ㄷㅊ": "닥쳐",
    "ㅁㄹ": "몰라",
}


def _load_sovits_presets() -> None:
    """data/characters.json에서 캐릭터 음성을 VOICE_PRESETS에 추가."""
    characters_file = DATA_DIR / "characters.json"
    if not characters_file.exists():
        return
    try:
        import json as _json
        with open(characters_file, "r", encoding="utf-8") as f:
            characters = _json.load(f)
        for char_id, char_data in characters.items():
            display_name = char_data.get("display_name", char_id)
            VOICE_PRESETS[display_name] = f"sovits:{char_id}"
    except Exception:
        pass


_load_sovits_presets()
