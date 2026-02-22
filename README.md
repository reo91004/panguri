# 판구리

판구리는 Discord 음성 채널에서 텍스트 채팅을 자동으로 읽어주는 TTS(Text-to-Speech) 봇입니다. edge-tts 스트리밍 기반으로 빠른 응답 속도를 제공하며, 한국어 읽기에 최적화되어 있습니다.

## 기능

- 텍스트 채널 메시지 자동 읽기
- 한국어 TTS 엔진 지원 (edge-tts, 구글 번역기, GPT-SoVITS)
- GPT-SoVITS 캐릭터 음성 TTS (애니, 게임 캐릭터 등)
- edge-tts 스트리밍 (낮은 지연시간) + gTTS 폴백
- LRU 오디오 캐시 (반복 메시지 즉시 재생)
- 사용자별 음성/속도/피치/효과 설정
- 한국어 줄임말/초성 자동 변환 (ㅋㅋ → 크크, ㄲㅂ → 쌍기역 비읍)
- edge-tts 오디오 미수신 시 자동 폴백 (깨진 스트림 재생 방지)
- 음성 채널에 혼자 남으면 즉시 퇴장

---

## Windows 초기 설정

### 1. Python 설치

[python.org](https://www.python.org/downloads/)에서 Python 3.10 이상을 다운로드하여 설치합니다.
설치 시 **"Add Python to PATH"** 옵션을 반드시 체크하세요.

### 2. FFmpeg 설치

아래 방법 중 하나를 선택합니다.

**winget (권장):**

```bash
winget install Gyan.FFmpeg
```

**Chocolatey:**

```bash
choco install ffmpeg
```

**수동 설치:**
[ffmpeg.org](https://ffmpeg.org/download.html)에서 다운로드 후, `bin` 폴더를 시스템 PATH에 추가합니다.

### 3. 프로젝트 설정

```bash
git clone <저장소 URL>
cd tts
pip install -r requirements.txt
```

### 4. 환경 변수 설정

`.env.example`을 복사하여 `.env` 파일을 생성하고 봇 토큰을 입력합니다.

```bash
copy .env.example .env
```

`.env` 파일 내용:

```
DISCORD_BOT_TOKEN=여기에_봇_토큰_입력

# GPT-SoVITS (선택사항 - 캐릭터 음성을 사용하지 않으면 생략 가능)
SOVITS_API_URL=http://localhost:9880
SOVITS_REQUEST_TIMEOUT=30
```

### 5. 판구리 실행

```bash
python bot.py
```

---

## macOS 초기 설정

### 1. Python 설치

```bash
brew install python@3.12
```

### 2. FFmpeg 설치

```bash
brew install ffmpeg
```

### 3. 프로젝트 설정

```bash
git clone <저장소 URL>
cd tts
pip install -r requirements.txt
```

### 4. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 봇 토큰을 입력합니다:

```
DISCORD_BOT_TOKEN=여기에_봇_토큰_입력

# GPT-SoVITS (선택사항 - 캐릭터 음성을 사용하지 않으면 생략 가능)
SOVITS_API_URL=http://localhost:9880
SOVITS_REQUEST_TIMEOUT=30
```

### 5. 판구리 실행

```bash
python bot.py
```

---

## 사용 방법

| 명령어      | 설명                                                               |
| ----------- | ------------------------------------------------------------------ |
| `/입장`     | 판구리를 음성 채널에 참가시키고 현재 텍스트 채널을 자동읽기로 설정 |
| `/퇴장`     | 판구리를 음성 채널에서 퇴장                                        |
| `/채팅지정` | 지정채널 설정/해제 — 메시지 시 자동으로 음성 채널에 참가하여 읽기  |
| `/목소리`   | 음성, 속도, 피치, 효과 설정 (드롭다운 UI)                          |
| `/스킵`     | 현재 재생 중인 TTS 건너뛰기                                        |

### 기본 사용 흐름

1. 음성 채널에 접속
2. 텍스트 채널에서 `/입장` 입력
3. 해당 텍스트 채널에 메시지를 보내면 자동으로 음성 읽기
4. `/목소리`로 원하는 음성/속도/피치/효과 설정 가능
5. `/퇴장`으로 판구리 퇴장

### 지정채널 사용 흐름

1. 텍스트 채널에서 `/채팅지정` 입력 → 지정채널로 설정
2. 음성 채널에 접속한 상태에서 해당 채널에 메시지를 보내면 판구리가 **자동으로 음성 채널에 참가**하여 읽기
3. `/퇴장` 후에도 지정채널 설정은 유지됨
4. `/채팅지정` 재입력 → 지정채널 해제

---

## 지원 음성 목록

### Edge TTS

| 이름 | 음성 ID                        | 언어   |
| ---- | ------------------------------ | ------ |
| 선희 | ko-KR-SunHiNeural              | 한국어 |
| 인준 | ko-KR-InJoonNeural             | 한국어 |
| 현수 | ko-KR-HyunsuMultilingualNeural | 한국어 |

### 구글 번역기 (gTTS)

| 이름        | 음성 ID | 언어   |
| ----------- | ------- | ------ |
| 구글 번역기 | gtts:ko | 한국어 |

### GPT-SoVITS (캐릭터 음성)

`data/characters.json`에 등록된 캐릭터가 자동으로 `/목소리` 드롭다운에 추가됩니다. 설정 방법은 아래의 [GPT-SoVITS 캐릭터 음성 설정](#gpt-sovits-캐릭터-음성-설정) 섹션을 참고하세요.

### 음성 효과 목록 (FFmpeg 필터)

| 이름   | 설명             |
| ------ | ---------------- |
| 기본   | 효과 없음        |
| 하이톤 | 높은 톤          |
| 저음   | 낮은 톤          |
| 라디오 | 라디오/방송 느낌 |
| 메가폰 | 확성기 느낌      |
| 에코   | 메아리 효과      |

---

## GPT-SoVITS 캐릭터 음성 설정

GPT-SoVITS를 사용하면 애니메이션, 게임 등의 캐릭터 목소리로 TTS를 재생할 수 있습니다. **선택사항**이며, 설정하지 않아도 기본 TTS(edge-tts, gTTS)는 정상 작동합니다.

### 사전 준비

- NVIDIA GPU가 장착된 Windows PC (RTX 4060 이상 권장)
- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) 설치 및 모델 학습 완료
- 캐릭터별 레퍼런스 음성 파일 (`.wav`) 준비

### 1. GPT-SoVITS API 서버 실행

GPT-SoVITS를 API 모드로 실행합니다. 기본 포트는 `9880`입니다.

```bash
# GPT-SoVITS 디렉토리에서
python api.py
```

### 2. 캐릭터 등록

`data/characters.json` 파일에 캐릭터를 추가합니다:

```json
{
	"ryan": {
		"display_name": "라이언",
		"refer_wav_path": "D:/GPT-SoVITS/references/ryan.wav",
		"prompt_text": "안녕, 나는 라이언이야.",
		"prompt_language": "ko",
		"text_language": "ko"
	},
	"apeach": {
		"display_name": "어피치",
		"refer_wav_path": "D:/GPT-SoVITS/references/apeach.wav",
		"prompt_text": "복숭아가 아니라 어피치라고!",
		"prompt_language": "ko",
		"text_language": "ko"
	}
}
```

| 필드              | 설명                                               |
| ----------------- | -------------------------------------------------- |
| `display_name`    | `/목소리` 드롭다운에 표시되는 이름                 |
| `refer_wav_path`  | GPT-SoVITS 서버 기준 레퍼런스 음성 파일의 절대경로 |
| `prompt_text`     | 레퍼런스 음성의 대사 텍스트 (정확할수록 품질 향상) |
| `prompt_language` | 레퍼런스 음성의 언어 (`ko`, `ja`, `en` 등)         |
| `text_language`   | 합성할 텍스트의 언어 (`ko`, `ja`, `en` 등)         |

### 3. 환경 변수 설정

`.env` 파일에 GPT-SoVITS 서버 주소를 설정합니다. 같은 PC에서 실행 중이라면 기본값 그대로 사용할 수 있습니다.

```
SOVITS_API_URL=http://localhost:9880
SOVITS_REQUEST_TIMEOUT=30
```

### 4. 봇 재시작

캐릭터를 추가하거나 수정한 후에는 봇을 재시작해야 합니다. 시작 로그에서 연결 상태를 확인할 수 있습니다:

```
GPT-SoVITS 서버 연결됨 (2개 캐릭터)        ← 정상
GPT-SoVITS 서버에 연결할 수 없습니다       ← 서버 미실행 (기본 TTS는 정상 작동)
```

### 5. 사용

1. Discord에서 `/목소리` 명령어 입력
2. 음성 드롭다운에서 캐릭터 선택 (캐릭터 음성은 "캐릭터 음성"으로 표시됨)
3. **저장** 클릭
4. 이후 메시지를 보내면 해당 캐릭터 목소리로 읽어줍니다

GPT-SoVITS 서버가 중단되면 자동으로 edge-tts 기본 음성으로 폴백됩니다.

---

## Discord 봇 생성 가이드

1. [Discord Developer Portal](https://discord.com/developers/applications)에 접속
2. **New Application** 클릭 → 이름 입력 → 생성
3. 왼쪽 메뉴에서 **Bot** 선택
4. **Reset Token** 클릭 → 토큰 복사 → `.env` 파일에 붙여넣기
5. **Privileged Gateway Intents** 섹션에서 아래 항목 활성화:
   - **Message Content Intent**
6. 왼쪽 메뉴에서 **OAuth2** → **URL Generator** 선택
7. Scopes: `bot`, `applications.commands` 체크
8. Bot Permissions: `Connect`, `Speak`, `Read Messages/View Channels`, `Send Messages` 체크
9. 생성된 URL을 복사하여 브라우저에서 열고 서버에 판구리 초대
