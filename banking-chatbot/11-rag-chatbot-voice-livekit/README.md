prototyping a real-time voice pipeline on livekit's agents framework instead of the browser record-button flow. two ways to talk to it: `agent.py console` (fully local simulation, mic in/speaker out, no livekit server needed) or a real livekit room via the frontend's "Live Call" button.

- stt: faster-whisper wrapped as a custom stt.STT, restricted to en/ur only
- llm: the existing /chat backend called directly from llm_node - no real llm plugin
  is used (see PlaceholderLLM, which exists only because AgentSession refuses to
  start without one, even though it's never actually called)
- tts: piper, picks the voice per turn based on session language

## prerequisites

- mongodb, redis running locally (`brew services start mongodb-community redis`)
- ollama running (`ollama serve`, or the Ollama app), with these models pulled:
  `ollama pull qwen2.5:3b && ollama pull llama3 && ollama pull alif-urdu`
- for the real-time voice room specifically: `livekit-server` binary installed
  (self-hosted, free - see livekit's docs) - not needed for console mode

## setup

1. `cd backend && python3 -m venv venv && venv/bin/pip install -r requirements.txt`
2. create `backend/.env` with:
   ```
   CACHE_MODE=file
   MONGO_URL=mongodb://localhost:27017
   MONGO_DB_NAME=abhi_bank_voice
   OLLAMA_URL=http://localhost:11434/api/chat
   CURRENCY_API=https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/
   CITIES_API=https://countries.dev/cities?q=
   WEATHER_API=https://wttr.in/
   REDIS_HOST=localhost
   REDIS_PORT=6379
   FRONTEND_URL=http://localhost:5174
   WHISPER_MODEL_SIZE=small
   WHISPER_DEVICE=cpu
   WHISPER_COMPUTE_TYPE=int8
   HF_TOKEN=...              # only needed if using a gated hugging face model
   CHAT_BACKEND_URL=http://localhost:8002
   LIVEKIT_URL=ws://localhost:7880
   LIVEKIT_API_KEY=devkey
   LIVEKIT_API_SECRET=secret
   ```
   the livekit values above are `livekit-server --dev`'s own built-in placeholder
   credentials (it prints them on startup) - fine for local use, not for a real
   deployment.
3. seed the database: `venv/bin/python3 seed_accounts.py && venv/bin/python3 seed_intents.py && venv/bin/python3 seed_field_prompts.py && venv/bin/python3 seed_tts_settings.py`
4. `cd ../front && npm install`
5. drop the fine-tuned urdu voice into `backend/voices/ur_PK-abhibank-finetune.onnx`
   (checked into this repo directly, not gitignored - see the main project's
   backend/voices/ folder) and the base piper voices (en_US-bryce-medium.onnx,
   ur_PK-fasih-medium-model.onnx) downloaded from piper's own voice repository

## running it

five terminals:
```
brew services start mongodb-community redis   # if not already running
ollama serve                                    # if not already running
livekit-server --dev                            # only needed for Live Call, not console mode
cd backend && venv/bin/uvicorn main:app --port 8002
cd backend && venv/bin/python3 agent.py console  # or `agent.py dev` for real Live Call
cd front && npm run dev
```
then open http://localhost:5174 - "Mic" records and transcribes to text chat,
"Live Call" is the real-time voice room (needs livekit-server + `agent.py dev`,
not console mode).

## known limitations

- `agent.py console`/`agent.py dev` both pay a one-time model-load cost on first
  use (whisper + silero vad) and a similar ollama cold-start cost after ~5min
  idle (kept warm afterward via keep_alive, see backend_logic.py)
- short/unclear speech can still fail to transcribe correctly - the pipeline is
  built to fail safely (ask you to repeat) rather than silently guess wrong, but
  it's not perfect, especially on the "small" whisper model size chosen for
  latency over accuracy
- this whole setup is local/dev only - see the main README for what's actually
  involved in deploying it for real
