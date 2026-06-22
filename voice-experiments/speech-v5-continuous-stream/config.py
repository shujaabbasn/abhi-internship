SAMPLE_RATE=16000 #16k industry standard
#whisper
WHISPER_MODEL_SIZE="medium"
WHISPER_DEVICE="cpu" #mps not supported by faster-whisper
WHISPER_COMPUTE_TYPE="int8" #float32 too slow

#context window
CONTEXT_WINDOW_SIZE=50

#llm
OLLAMA_MODEL="qwen2.5:3b"
OLLAMA_URL="http://localhost:11434/api/chat"
OLLAMA_TEMPERATURE=0.5
OLLAMA_NUM_PREDICT=50

SAMPLE_PROMPT=(
    "You are a helpful voice assistant. Reply only in English or Urdu, never any other language. "
    "If the user speaks English or mixes languages, reply in English only. "
    "If the user speaks only Urdu, reply in Urdu script only. "
    "Keep replies short. "
    "Do NOT use markdown, asterisks, or special symbols."
    "DO NOT REPLY IN ANY OTHER LANGUAGE THAT IS NOT ENGLISH OR URDU"
    "Keep previous context in mind when you respond"
)

ALLOWED_LANGUAGES=["en","ur"]

#piper
PIPER_PATH="piper"
PIPER_VOICE_EN="./voices/en_US-bryce-medium.onnx"
PIPER_VOICE_UR="./voices/ur_PK-fasih-medium-model.onnx"

#vad using webrtcvad
VAD_AGGRESSIVENESS=3
FRAME_DURATION_MS=20
SILENCE_DURATION_MS=1500
SILENCE_FRAMES_NEEDED=SILENCE_DURATION_MS//FRAME_DURATION_MS

#threading
QUEUE_TIMEOUT=0.5 #seconds main loop waits on queue before checking again
MAX_LISTEN_SECONDS=30 #timeout per utterance
CONSECUTIVE_SPEECH_FRAMES_NEEDED=8 #8x20ms=160ms sustained speech to trigger

#transliteration toggle: flip to True to test roman urdu pipeline
USE_TRANSLITERATION=False

#prompt when transliteration is on (llm receives roman urdu)
SAMPLE_PROMPT_ROMAN=(
    "You are a helpful voice assistant. Reply only in English or Roman Urdu, never any other language. "
    "If the user speaks English or mixes languages, reply in English only. "
    "If the user speaks Urdu (written in roman script like 'aap kaise hain'), reply in Roman Urdu only. "
    "Keep replies short. "
    "Do NOT use markdown, asterisks, or special symbols."
    "DO NOT REPLY IN ANY OTHER LANGUAGE THAT IS NOT ENGLISH OR ROMAN URDU"
    "Keep previous context in mind when you respond"
)