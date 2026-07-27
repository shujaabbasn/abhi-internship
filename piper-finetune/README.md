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
trained model's config - the actual exported voice this pipeline produced is checked
in at banking-chatbot/11-rag-chatbot-voice/backend/voices/ur_PK-abhibank-finetune.onnx
(force-added past the *.onnx gitignore rule, since this one's actually authored here
rather than a downloaded base model).
