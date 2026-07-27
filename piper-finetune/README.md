finetunes ur_PK-fasih-medium (piper) on banking-domain phrases. phrase list + recordings
come from tts-recorder / banking-chatbot/11-rag-chatbot-voice/backend/tts_finetune_data.

pipeline: preprocess.py (recordings -> ljspeech-style dataset, resampled to 22050hz)
-> piper's own preprocessing (phonemize + cache tensors) -> train.py (resumes from the
base ckpt, doesn't train from scratch) -> export_onnx.py

not committed, all regeneratable / too big for git:
- checkpoints/, lightning_logs/ - training checkpoints, ~800mb each
- cache/ - preprocessed phoneme/audio tensors, rebuilt automatically from dataset/
- piper1_venv/ - the training venv

dataset/ is the actual recorded+converted training audio. output/config.json is the
trained model's config - the real .onnx it produced lives in the running project's
backend/voices/ folder (gitignored there too, same reason).
