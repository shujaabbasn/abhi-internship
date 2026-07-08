import subprocess
import tempfile
import os

PIPER_PATH="piper"
VOICE_MODEL=os.path.join(os.path.dirname(__file__),"voices","en_US-bryce-medium.onnx")

def text_to_speech(text):
    fd,output_wav=tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        subprocess.run(
            [PIPER_PATH,"--model",VOICE_MODEL,"--output_file",output_wav],
            input=text,text=True,check=True
        )
        with open(output_wav,"rb") as file:
            return file.read()
    finally:
        os.remove(output_wav)
