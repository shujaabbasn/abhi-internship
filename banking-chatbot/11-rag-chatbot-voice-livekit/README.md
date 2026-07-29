prototyping a real-time voice pipeline on livekit's agents framework instead of the browser record-button flow.

no livekit server needed to test, it's a full local simulation (mic in, speaker out).

- stt: faster-whisper wrapped as a custom stt.STT, restricted to en/ur only
- llm: the existing /chat backend called directly from llm_node - no real llm plugin
  is used (see PlaceholderLLM, which exists only because AgentSession refuses to
  start without one, even though it's never actually called)
- tts: piper, picks the voice per turn based on session language

not committed: venv/, voices/, models/, kokoro-v1.0.onnx, voices-v1.0.bin - same
large model files as the main project, gitignored for the same reason.
