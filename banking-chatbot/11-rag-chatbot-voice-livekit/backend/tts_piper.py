import subprocess
import tempfile
import os

PIPER_PATH="piper"
VOICES_DIR=os.path.join(os.path.dirname(__file__),"voices")

#per-voice overrides for VITS synthesis randomness (noise_scale affects vocal
#texture/expressiveness, noise_w_scale affects timing/rhythm variation).
#piper's built-in defaults (0.667 / 0.8) are left as-is for voices not listed here.
VOICE_SYNTHESIS_SCALES={
    "ur_PK-abhibank-finetune.onnx":{"noise_scale":0.75,"noise_w_scale":0.85},
}

def synthesize_piper(text,voice_file,speed):
    model_path=os.path.join(VOICES_DIR,voice_file)
    fd,output_wav=tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        cmd=[PIPER_PATH,"--model",model_path,"--output_file",output_wav]
        if speed!=1.0:
            cmd.extend(["--length-scale",str(1.0/speed)])
        scales=VOICE_SYNTHESIS_SCALES.get(voice_file)
        if scales:
            cmd.extend(["--noise-scale",str(scales["noise_scale"])])
            cmd.extend(["--noise-w-scale",str(scales["noise_w_scale"])])
        subprocess.run(cmd,input=text,text=True,check=True)
        with open(output_wav,"rb") as file:
            return file.read()
    finally:
        os.remove(output_wav)