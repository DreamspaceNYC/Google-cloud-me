import os
import time
import hmac
import hashlib
import io
import logging
from typing import Dict

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from google.auth import default as google_auth_default
from google.auth.transport.requests import AuthorizedSession
from google.cloud import texttospeech
from google.oauth2 import id_token
from google.auth.transport import requests as g_requests

AUTH_MODE = os.getenv("AUTH_MODE", "hmac")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
ACCESS_SECRET = os.getenv("ACCESS_SECRET", "changeme").encode()
LOG_PAYLOADS = os.getenv("LOG_PAYLOADS", "false").lower() == "true"
MAX_BODY = int(os.getenv("MAX_BODY", "1000000"))
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "60"))

logger = logging.getLogger("backend")
logging.basicConfig(level=logging.INFO)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# simple in-memory rate limiter
class RateLimiter:
    def __init__(self, max_per_minute: int):
        self.max = max_per_minute
        self.calls: Dict[str, list] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        bucket = self.calls.setdefault(key, [])
        bucket = [t for t in bucket if t > now - 60]
        self.calls[key] = bucket
        if len(bucket) >= self.max:
            return False
        bucket.append(now)
        return True

limiter = RateLimiter(RATE_LIMIT)
used_signatures = set()

@app.middleware("http")
async def check_body(request: Request, call_next):
    body = await request.body()
    if len(body) > MAX_BODY:
        return Response("Payload too large", status_code=413)
    request._body = body  # cache for later
    return await call_next(request)

@app.middleware("http")
async def apply_rate_limit(request: Request, call_next):
    key = f"{request.client.host}:{request.url.path}"
    if not limiter.allow(key):
        return Response("Too Many Requests", status_code=429)
    return await call_next(request)

async def verify_request(request: Request):
    if AUTH_MODE == "secure":
        auth = request.headers.get("authorization")
        if not auth or not auth.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Missing token")
        token = auth.split()[1]
        try:
            decoded = id_token.verify_firebase_token(token, g_requests.Request())
            return decoded
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid token") from exc
    else:
        ts = request.headers.get("x-ts")
        sig = request.headers.get("x-sig")
        if not ts or not sig:
            raise HTTPException(status_code=401, detail="Missing signature")
        if abs(int(time.time()) - int(ts)) > 120:
            raise HTTPException(status_code=401, detail="Stale signature")
        message = f"{request.method}\n{request.url.path}\n{ts}".encode()
        expected = hmac.new(ACCESS_SECRET, message, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig) or sig in used_signatures:
            raise HTTPException(status_code=401, detail="Bad signature")
        used_signatures.add(sig)
        return {}

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/apis")
async def list_apis(_: dict = Depends(verify_request)):
    creds, project_id = google_auth_default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    session = AuthorizedSession(creds)
    url = f"https://serviceusage.googleapis.com/v1/projects/{project_id}/services?filter=state:ENABLED"
    resp = session.get(url)
    services = []
    if resp.ok:
        data = resp.json().get("services", [])
        services = [s["config"]["name"] for s in data]
    return {"services": services}

@app.post("/tts/synthesize")
async def tts_synthesize(req: Request, _: dict = Depends(verify_request)):
    data = await req.json()
    text = data.get("text", "")
    voice_name = data.get("voice", "en-US-Neural2-C")
    encoding = data.get("encoding", "MP3")
    if len(text) > 4400:
        raise HTTPException(status_code=413, detail="Text too long")
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code=voice_name.split("-")[0], name=voice_name)
    audio_config = texttospeech.AudioConfig(audio_encoding=getattr(texttospeech.AudioEncoding, encoding))
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    return StreamingResponse(io.BytesIO(response.audio_content), media_type="audio/mpeg")

@app.post("/client-token")
async def client_token(data: dict):
    path = data.get("path", "/")
    method = data.get("method", "GET")
    ts = str(int(time.time()))
    message = f"{method}\n{path}\n{ts}".encode()
    sig = hmac.new(ACCESS_SECRET, message, hashlib.sha256).hexdigest()
    return {"ts": ts, "sig": sig}
