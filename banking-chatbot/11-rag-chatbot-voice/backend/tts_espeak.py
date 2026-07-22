import subprocess
import tempfile
import os

ESPEAK_PATH="espeak-ng"

def synthesize_espeak_urdu(text,speed):
    fd,output_wav=tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        words_per_minute=str(int(175*speed))
        cmd=[ESPEAK_PATH,"-v","ur","-s",words_per_minute,"-w",output_wav,text]
        subprocess.run(cmd,check=True)
        with open(output_wav,"rb") as file:
            return file.read()
    finally:
        os.remove(output_wav)
