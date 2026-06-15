SAMPLE_RATE=16000 #16k industry standard, will try others

WHISPER_MODEL_SIZE="medium"
WHISPER_DEVICE="cpu"
WHISPER_COMPUTE_TYPE="int8"

OLLAMA_MODEL="qwen2.5:7b"
OLLAMA_URL="http://localhost:11434/api/chat" #ollama binds to 127.0.0.1:11434
OLLAMA_TEMPERATURE=0.3 #lower or higher?
OLLAMA_NUM_PREDICT=100 #what should be limit?

PIPER_PATH="piper"
VOICE_MAP={
    "en":"./voices/en_US-bryce-medium.onnx",
    "ur":"./voices/ur_PK-fasih-medium-model.onnx"
}

ALLOWED_LANGUAGES=["en","ur"]

#VAD (voice activity detection) settings
VAD_AGGRESSIVENESS=2 #0-3, higher = more aggressive filtering of non-speech (fewer false triggers)
FRAME_DURATION_MS=30 #webrtcvad requires 10/20/30 ms frames
SILENCE_DURATION_MS=1000 #how long silence must persist after speech to consider the turn done

#PROMPTS: #will try multiple
SAMPLE_PROMPT = (
    "You are a helpful voice assistant. Users may speak to you in English, Urdu, "
    "or a mix of both in the same sentence. "
    "Listen to their intent, but you MUST reply in strictly ONE language. "
    "If their dominant language is Urdu, reply entirely in native Urdu script. "
    "If their dominant language is English, reply entirely in English. "
    "Never mix languages in your response. Do NOT use any markdown formatting, "
    "asterisks, bolding or special symbols in your text."
)
