import os
import json
import base64
import uuid
import aiohttp
from dotenv import load_dotenv

# Load env (safe)
load_dotenv(override=True)

TTS_URL = os.getenv("DOUBAO_TTS_URL", "https://openspeech.bytedance.com/api/v3/tts/unidirectional")
APP_ID = os.getenv("DOUBAO_APP_ID")
ACCESS_TOKEN = os.getenv("DOUBAO_SPEECH_TOKEN")
CLUSTER = os.getenv("DOUBAO_TTS_CLUSTER", "volcano_tts")
RESOURCE_ID = os.getenv("DOUBAO_TTS_RESOURCE_ID", "volc.service_type.10029")
APP_TOKEN = os.getenv("DOUBAO_TTS_APP_TOKEN", "token")
VOICE_TYPE = os.getenv("DOUBAO_TTS_VOICE_TYPE", "zh_male_yunzhou_jupiter_bigtts")
ENCODING = os.getenv("DOUBAO_TTS_ENCODING", "pcm")
SAMPLE_RATE = int(os.getenv("DOUBAO_TTS_SAMPLE_RATE", "24000"))
SPEED = float(os.getenv("DOUBAO_TTS_SPEED", "1.0"))
VOLUME = float(os.getenv("DOUBAO_TTS_VOLUME", "1.0"))
UID = os.getenv("DOUBAO_TTS_UID", "388808087185088")
TEXT_TYPE = os.getenv("DOUBAO_TTS_TEXT_TYPE", "plain")
FRONTEND_TYPE = os.getenv("DOUBAO_TTS_FRONTEND_TYPE", "unitTson")
WITH_FRONTEND = int(os.getenv("DOUBAO_TTS_WITH_FRONTEND", "1"))


def _build_request(text: str) -> dict:
    if not APP_ID or not ACCESS_TOKEN or not CLUSTER:
        raise ValueError("Missing DOUBAO_APP_ID / DOUBAO_SPEECH_TOKEN / DOUBAO_TTS_CLUSTER")

    return {
        "app": {
            "appid": APP_ID,
            "token": APP_TOKEN,
            "cluster": CLUSTER,
        },
        "user": {
            "uid": UID,
        },
        "audio": {
            "voice_type": VOICE_TYPE,
            "encoding": ENCODING,
            "rate": SAMPLE_RATE,
            "speed_ratio": SPEED,
            "volume_ratio": VOLUME,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "text_type": TEXT_TYPE,
            "operation": "query",
            "with_frontend": WITH_FRONTEND,
            "frontend_type": FRONTEND_TYPE,
        },
    }


async def synthesize(text: str) -> bytes:
    """
    Call Doubao HTTP TTS and return raw audio bytes (decoded from base64).
    """
    headers = {
        "Authorization": f"Bearer;{ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    if RESOURCE_ID:
        headers["Resource-Id"] = RESOURCE_ID
    payload = _build_request(text)

    async with aiohttp.ClientSession() as session:
        async with session.post(TTS_URL, data=json.dumps(payload), headers=headers, timeout=10) as resp:
            resp.raise_for_status()
            data = await resp.json()

    if not isinstance(data, dict):
        raise RuntimeError("Unexpected TTS response")
    if "data" not in data:
        raise RuntimeError(f"TTS error: {data}")

    audio_b64 = data["data"]
    return base64.b64decode(audio_b64)
