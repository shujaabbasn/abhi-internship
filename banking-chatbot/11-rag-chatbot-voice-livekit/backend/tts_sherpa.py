import os
import io
import glob
import threading

VOICES_DIR=os.path.join(os.path.dirname(__file__),"voices")
_sherpa_state={}
_sherpa_lock=threading.Lock()

def synthesize_sherpa(text,voice_name,speed):
    import sherpa_onnx
    import wave
    import numpy as np

    if voice_name not in _sherpa_state:
        with _sherpa_lock:
            if voice_name not in _sherpa_state:
                voice_dir=os.path.join(VOICES_DIR,voice_name)
                onnx_matches=glob.glob(os.path.join(voice_dir,"*.onnx"))
                if not onnx_matches:
                    raise FileNotFoundError("No .onnx model found in "+voice_dir)
                model_path=onnx_matches[0]
                tokens_path=os.path.join(voice_dir,"tokens.txt")
                data_dir=os.path.join(voice_dir,"espeak-ng-data")
                config=sherpa_onnx.OfflineTtsConfig(
                    model=sherpa_onnx.OfflineTtsModelConfig(
                        vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                            model=model_path,
                            tokens=tokens_path,
                            data_dir=data_dir
                        )
                    )
                )
                _sherpa_state[voice_name]=sherpa_onnx.OfflineTts(config)

    tts=_sherpa_state[voice_name]
    audio=tts.generate(text,speed=speed)
    buf=io.BytesIO()
    with wave.open(buf,"wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(audio.sample_rate)
        samples=np.array(audio.samples)
        samples=(samples*32767).astype(np.int16)
        wf.writeframes(samples.tobytes())
    return buf.getvalue()