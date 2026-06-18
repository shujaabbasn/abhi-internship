from transformers import VitsModel, AutoTokenizer
import torch
import soundfile

model = VitsModel.from_pretrained("facebook/mms-tts-urd-script_arabic")
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-urd-script_arabic")

text = "آپ کا حال کیسا ہے"
inputs = tokenizer(text, return_tensors="pt")
with torch.no_grad():
    output = model(**inputs).waveform
soundfile.write("test_urdu_facebookmms.wav", output.squeeze().numpy(), model.config.sampling_rate)