import threading

_kokoro_state={"model":None}
_kokoro_lock=threading.Lock()

def synthesize_kokoro(text,voice_name,speed):
    import soundfile as sf
    import io

    if _kokoro_state["model"] is None:
        with _kokoro_lock:
            if _kokoro_state["model"] is None:
                from kokoro_onnx import Kokoro
                _kokoro_state["model"]=Kokoro("kokoro-v1.0.onnx","voices-v1.0.bin")

    kokoro=_kokoro_state["model"]
    samples,sample_rate=kokoro.create(text,voice=voice_name,speed=speed)
    buf=io.BytesIO()
    sf.write(buf,samples,sample_rate,format="WAV")
    buf.seek(0)
    return buf.read()