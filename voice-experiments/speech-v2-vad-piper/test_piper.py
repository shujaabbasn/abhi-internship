import subprocess
import sounddevice
import soundfile

PIPER_PATH="piper"
PIPER_VOICE_UR="./voices/ur_PK-fasih-medium-model.onnx"

text="آپ کا حال کیسا ہے"
output_wav="test_piper_urdu.wav"

subprocess.run([PIPER_PATH,"--model",PIPER_VOICE_UR,"--output_file",output_wav],input=text,text=True,check=True)

data,samplerate=soundfile.read(output_wav)
sounddevice.play(data,samplerate)
sounddevice.wait()