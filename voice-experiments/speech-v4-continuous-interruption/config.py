SAMPLE_RATE=16000 #16k industry standard, will try others
#whisper
WHISPER_MODEL_SIZE="medium" #reduced from medium
WHISPER_DEVICE="cpu" #trying mps, failed: ValueError: unsupported device mps
WHISPER_COMPUTE_TYPE="int8" #float32 took too

#DEVICE="mps"
#window
CONTEXT_WINDOW_SIZE=50

#llm
OLLAMA_MODEL="qwen2.5:3b" #pulled 0.5, 3 and 7
OLLAMA_URL="http://localhost:11434/api/chat" #ollama binds to 127.0.0.1:11434
OLLAMA_TEMPERATURE=0.5 #trying 1
OLLAMA_NUM_PREDICT=50 #reduced from 100

SAMPLE_PROMPT=(
    "You are a helpful voice assistant. Reply only in English or Urdu, never any other language. "
    "If the user speaks English or mixes languages, reply in English only. "
    "If the user speaks only Urdu, reply in Urdu script only. "
    "Keep replies short. "
    "Do NOT use markdown, asterisks, or special symbols."
    "DO NOT REPLY IN ANY OTHER LANGUAGE THAT IS NOT ENGLISH OR URDU"
    "Keep previous context in mind when you respond"
)

# SAMPLE_PROMPT=(
#     "You are a helpful voice assistant. Always reply in the same language "
#     "the user spoke in (English or Urdu). Keep replies short and conversational. "
#     "Do NOT use any markdown formatting, asterisks, bolding or special symbols in your text."
# )


# SAMPLE_PROMPT_2=(
#     "You are a helpful, friendly voice assistant. You must respond entirely in the "
#     "same language as the user's input (if they speak Urdu, reply in Urdu script. "
#     "if they speak English, reply in English). Your response will be read aloud, so "
#     "keep it fluid, natural, and under 3-4 sentences. Avoid symbols or complex punctuation."
#     "Do NOT use any markdown formatting, asterisks, bolding or special symbols in your text."
# )

ALLOWED_LANGUAGES=["en","ur"]

#piper
PIPER_PATH="piper"
PIPER_VOICE_EN="./voices/en_US-bryce-medium.onnx"
PIPER_VOICE_UR="./voices/ur_PK-fasih-medium-model.onnx"
#voice detection
#changed to silero
#uses a nn, better for noise, highest precision abd recall
#https://github.com/snakers4/silero-vad/wiki/Quality-Metrics
# VAD_THRESHOLD=0.5 #speech probability bw 0 and 1 where number greater than threshold determines that speech has been detected
# SILERO_CHUNK_SIZE=512 #silero uses 512 samples ato nce
# SILENCE_DURATION_MS=2500
# SILENCE_CHUNKS_NEEDED=int((SILENCE_DURATION_MS/1000)*SAMPLE_RATE/SILERO_CHUNK_SIZE)


VAD_AGGRESSIVENESS=3
FRAME_DURATION_MS=20
SILENCE_DURATION_MS=1500
SILENCE_FRAMES_NEEDED=SILENCE_DURATION_MS//FRAME_DURATION_MS #2500/20=125frames