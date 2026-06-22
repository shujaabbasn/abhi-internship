import subprocess
import numpy
import os
import time
import wave
import warnings
import logging
os.environ["TORCH_FORCE_WEIGHTS_ONLY_LOAD"]="0"  #must be before any torch import
#suppress parler/transformers config spam
logging.disable(logging.WARNING)
warnings.filterwarnings("ignore")
os.environ["TRANSFORMERS_VERBOSITY"]="error"
os.environ["COQUI_TOS_AGREED"]="1"

#fix torch.load compatibility for coqui models
import torch
original_torch_load=torch.load
def patched_torch_load(*args,**kwargs):
    kwargs["weights_only"]=False
    return original_torch_load(*args,**kwargs)
torch.load=patched_torch_load

os.makedirs("./voice_samples",exist_ok=True)

urdu_text="آپ کا اکاؤنٹ بیلنس پچاس ہزار روپے ہے۔ آپ کی آخری ٹرانزیکشن پانچ ہزار روپے کی تھی جو کامیاب ہو گئی ہے۔"
urdu_romanized="aap ka account balance pachaas hazaar rupay hai. aap ki aakhri transaction paanch hazaar rupay ki thi jo kaamyaab ho gayi hai."
english_text="Your account balance is fifty thousand rupees. Your last transaction of five thousand rupees was successful."

urdu_test_3="آج موسم بہت اچھا ہے، باہر دھوپ نکلی ہوئی ہے۔"
urdu_test_4="کیا آپ مجھے بتا سکتے ہیں کہ قریبی اے ٹی ایم کہاں ہے؟"
urdu_short_1="آپ کا اکاؤنٹ بیلنس پچاس ہزار روپے ہے۔"
urdu_short_2="آپ کی آخری ٹرانزیکشن پانچ ہزار روپے کی تھی۔"

all_results=[]

#english loan words commonly used in urdu banking — keep as english for tts
URDU_ENGLISH_LOANS={
    "اکاؤنٹ":"account","بیلنس":"balance","ٹرانزیکشن":"transaction",
    "بینک":"bank","پاسورڈ":"password","نمبر":"number",
    "کارڈ":"card","پن":"pin","اے ٹی ایم":"ATM",
    "ڈیبٹ":"debit","کریڈٹ":"credit","انٹرنیٹ":"internet",
    "موبائل":"mobile","ایپ":"app","سروس":"service",
    "فون":"phone","ایس ایم ایس":"SMS","ای میل":"email",
}

#multi-char mappings MUST come first (aspirated consonants like تھ = थ not त+ह)
URDU_TO_DEVANAGARI_MULTI={
    "تھ":"थ","دھ":"ध","بھ":"भ","پھ":"फ",
    "گھ":"घ","کھ":"ख","جھ":"झ","ٹھ":"ठ",
    "ڈھ":"ढ","چھ":"छ","رھ":"र्ह",
}

#single char mappings
URDU_TO_DEVANAGARI_SINGLE={
    "آ":"आ","ا":"ा","ب":"ब","پ":"प","ت":"त","ٹ":"ट",
    "ث":"स","ج":"ज","چ":"च","ح":"ह","خ":"ख",
    "د":"द","ڈ":"ड","ذ":"ज़","ر":"र","ڑ":"ड़",
    "ز":"ज़","ژ":"झ","س":"स","ش":"श","ص":"स",
    "ض":"ज़","ط":"त","ظ":"ज़","ع":"अ","غ":"ग़",
    "ف":"फ़","ق":"क़","ک":"क","گ":"ग","ل":"ल",
    "م":"म","न":"न","و":"ो","ہ":"ह","ھ":"ह",
    "ء":"","ی":"ी","ے":"े","ئ":"",
    "ں":"ं","ؤ":"ो","إ":"इ","أ":"अ",
    "\u064E":"","\u064F":"","\u0650":"",  #zabar pesh zer (diacritics, skip)
    "\u0651":"","\u0652":"","\u0670":"",  #tashdeed sukun alef (diacritics, skip)
    "۔":".","؟":"?","،":",","؛":";",
    "۰":"0","۱":"1","۲":"2","۳":"3","۴":"4",
    "۵":"5","۶":"6","۷":"7","۸":"8","۹":"9",
    " ":" "
}

#sorted by length so longer matches hit first
URDU_MULTI_KEYS=sorted(URDU_TO_DEVANAGARI_MULTI.keys(),key=len,reverse=True)
URDU_LOAN_KEYS=sorted(URDU_ENGLISH_LOANS.keys(),key=len,reverse=True)

def urdu_to_devanagari(text):
    #first pass: replace english loan words with english
    result=text
    for urdu_word in URDU_LOAN_KEYS:
        if urdu_word in result:
            result=result.replace(urdu_word,URDU_ENGLISH_LOANS[urdu_word])
    #second pass: convert remaining urdu to devanagari
    final=""
    pos=0
    while pos<len(result):
        found=False
        #check multi-char mappings first (aspirated consonants)
        for key in URDU_MULTI_KEYS:
            if result[pos:pos+len(key)]==key:
                final=final+URDU_TO_DEVANAGARI_MULTI[key]
                pos=pos+len(key)
                found=True
                break
        if found==False:
            char=result[pos]
            if char in URDU_TO_DEVANAGARI_SINGLE:
                final=final+URDU_TO_DEVANAGARI_SINGLE[char]
            else:
                final=final+char  #keep english letters, digits etc
            pos=pos+1
    return final

def already_exists(output_filename):
    filepath="./voice_samples/"+output_filename
    if os.path.exists(filepath):
        size=os.path.getsize(filepath)
        if size>1000:
            print(output_filename,"- already exists, skipping")
            return True
    return False

def save_wav_file(filepath,audio_data,sample_rate):
    with wave.open(filepath,"wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

def generate_piper(text,model_path,output_filename,length_scale=1.0,noise_scale=0.667,noise_width=0.8):
    if already_exists(output_filename):
        return
    start_time=time.time()
    process=subprocess.run(["piper","--model",model_path,"--output-raw",
        "--length-scale",str(length_scale),"--noise-scale",str(noise_scale),"--noise-w",str(noise_width)],
        input=text.encode("utf-8"),capture_output=True)
    if process.returncode!=0 or len(process.stdout)==0:
        print(output_filename,"- FAILED")
        return
    audio=numpy.frombuffer(process.stdout,dtype=numpy.int16)
    save_wav_file("./voice_samples/"+output_filename,audio,22050)
    duration=round(len(audio)/22050,1)
    generation_time=round(time.time()-start_time,1)
    print(output_filename)
    all_results.append({
        "file":output_filename,
        "duration":duration,
        "generation_time":generation_time,
        "engine":"Piper TTS",
        "type":"OFFLINE"
    })

def generate_parler(text,language,output_filename,voice_description):
    if already_exists(output_filename):
        return
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer
    if not hasattr(generate_parler,"model"):
        print("loading parler model...")
        generate_parler.model=ParlerTTSForConditionalGeneration.from_pretrained("ai4bharat/indic-parler-tts").to("cpu")
        generate_parler.tokenizer=AutoTokenizer.from_pretrained("ai4bharat/indic-parler-tts")
    description_tokens=generate_parler.tokenizer(voice_description,return_tensors="pt")
    text_tokens=generate_parler.tokenizer(text,return_tensors="pt")
    start_time=time.time()
    generation=generate_parler.model.generate(
        input_ids=description_tokens.input_ids,
        attention_mask=description_tokens.attention_mask,
        prompt_input_ids=text_tokens.input_ids,
        prompt_attention_mask=text_tokens.attention_mask)
    audio=generation.cpu().numpy().squeeze()
    sample_rate=generate_parler.model.config.sampling_rate
    save_wav_file("./voice_samples/"+output_filename,(audio*32767).astype(numpy.int16),sample_rate)
    duration=round(len(audio)/sample_rate,1)
    generation_time=round(time.time()-start_time,1)
    print(output_filename)
    all_results.append({
        "file":output_filename,
        "duration":duration,
        "generation_time":generation_time,
        "engine":"Indic Parler TTS (ai4bharat)",
        "type":"OFFLINE"
    })

def generate_edge(text,voice_name,output_filename):
    if already_exists(output_filename):
        return
    import asyncio
    import edge_tts
    async def run_edge():
        communicator=edge_tts.Communicate(text,voice_name)
        await communicator.save("./voice_samples/"+output_filename)
    start_time=time.time()
    asyncio.run(run_edge())
    generation_time=round(time.time()-start_time,1)
    print(output_filename)
    all_results.append({
        "file":output_filename,
        "duration":"see file",
        "generation_time":generation_time,
        "engine":"Microsoft Edge TTS ("+voice_name+")",
        "type":"ONLINE"
    })

def generate_mms(text,model_id,output_filename):
    if already_exists(output_filename):
        return
    import torch
    from transformers import VitsModel,AutoTokenizer
    if not hasattr(generate_mms,"models"):
        generate_mms.models={}
    if model_id not in generate_mms.models:
        print("loading",model_id,"...")
        generate_mms.models[model_id]={
            "model":VitsModel.from_pretrained(model_id),
            "tokenizer":AutoTokenizer.from_pretrained(model_id)
        }
    model=generate_mms.models[model_id]["model"]
    tokenizer=generate_mms.models[model_id]["tokenizer"]
    inputs=tokenizer(text,return_tensors="pt")
    start_time=time.time()
    with torch.no_grad():
        output=model(**inputs).waveform
    audio=output.squeeze().numpy()
    sample_rate=model.config.sampling_rate
    audio_int16=(audio*32767).astype(numpy.int16)
    save_wav_file("./voice_samples/"+output_filename,audio_int16,sample_rate)
    duration=round(len(audio)/sample_rate,1)
    generation_time=round(time.time()-start_time,1)
    print(output_filename)
    all_results.append({
        "file":output_filename,
        "duration":duration,
        "generation_time":generation_time,
        "engine":"Facebook MMS-TTS ("+model_id+")",
        "type":"OFFLINE"
    })

def generate_coqui_finetuned(text,output_filename,ref_wav="./voice_samples/06_edge_urdu_male.wav"):
    if already_exists(output_filename):
        return
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    from huggingface_hub import snapshot_download
    import torch
    if not hasattr(generate_coqui_finetuned,"model"):
        print("loading coqui xtts-v2 urdu fine-tuned...")
        model_path=snapshot_download(repo_id="suhaibrashid17/XTTS-v2-Urdu-FT")
        config=XttsConfig()
        config.load_json(model_path+"/config.json")
        generate_coqui_finetuned.model=Xtts.init_from_config(config)
        generate_coqui_finetuned.model.load_checkpoint(config,checkpoint_dir=model_path)
        generate_coqui_finetuned.model.eval()
        generate_coqui_finetuned.config=config
    start_time=time.time()
    #extract voice embedding from reference audio
    gpt_cond_latent,speaker_embedding=generate_coqui_finetuned.model.get_conditioning_latents(
        audio_path=ref_wav,
        gpt_cond_len=generate_coqui_finetuned.config.gpt_cond_len,
        max_ref_length=generate_coqui_finetuned.config.max_ref_len,
        sound_norm_refs=generate_coqui_finetuned.config.sound_norm_refs
    )
    #convert urdu to devanagari for proper hindi phoneme mapping
    hindi_text=urdu_to_devanagari(text)
    print("devanagari:",hindi_text)
    #generate speech — hindi phonemes match urdu pronunciation
    out=generate_coqui_finetuned.model.inference(
        hindi_text,
        "hi",  #hindi has proper phoneme support in xtts-v2
        gpt_cond_latent,
        speaker_embedding,
        temperature=0.1,       #low temperature prevents randomness
        length_penalty=1.0,
        repetition_penalty=10.0,  #high penalty prevents mumbling loops
        top_k=10,
        top_p=0.3              #tight sampling keeps output coherent
    )
    audio=out["wav"]
    audio_int16=(numpy.array(audio)*32767).astype(numpy.int16)
    save_wav_file("./voice_samples/"+output_filename,audio_int16,24000)
    duration=round(len(audio)/24000,1)
    generation_time=round(time.time()-start_time,1)
    print(output_filename)
    all_results.append({
        "file":output_filename,
        "duration":duration,
        "generation_time":generation_time,
        "engine":"Coqui XTTS-v2 Urdu Fine-tuned (suhaibrashid17)",
        "type":"OFFLINE"
    })

print("generating samples...\n")

#piper voices
generate_piper(urdu_text,"./voices/ur_PK-fasih-medium-model.onnx","01_piper_urdu_default.wav")
generate_piper(urdu_text,"./voices/ur_PK-fasih-medium-model.onnx","02_piper_urdu_slow.wav",length_scale=1.2,noise_scale=0.9,noise_width=0.9)
generate_piper(english_text,"./voices/en_US-bryce-medium.onnx","03_piper_english.wav")

#parler tts
try:
    generate_parler(urdu_text,"ur","04_parler_urdu_male.wav",
        "A male speaker with a clear Urdu voice, moderate pace, calm tone.")
    generate_parler(urdu_text,"ur","05_parler_urdu_female.wav",
        "A female speaker with a clear Urdu voice, moderate pace, warm tone.")
except Exception as error:
    print("parler failed:",str(error)[:80])

#edge tts online comparison
try:
    generate_edge(urdu_text,"ur-PK-AsadNeural","06_edge_urdu_male.wav")
    generate_edge(urdu_text,"ur-PK-UzmaNeural","07_edge_urdu_female.wav")
except Exception as error:
    print("edge-tts failed:",str(error)[:80])

#facebook mms-tts (meta, supports urdu natively)
try:
    generate_mms(urdu_text,"facebook/mms-tts-urd-script_arabic","08_mms_urdu_arabic.wav")
    generate_mms(urdu_romanized,"facebook/mms-tts-urd-script_latin","09_mms_urdu_latin.wav")
except Exception as error:
    print("mms-tts failed:",str(error)[:80])

#coqui xtts-v2 fine-tuned for urdu
#uses hindi phonemes via devanagari transliteration for correct pronunciation
#english loan words kept in english for natural code-switching
#uses edge male voice as reference by default, pass ref_wav to change
try:
    #edge voice reference — different sentences prove its not just replaying
    generate_coqui_finetuned(urdu_text,"12_coqui_xtts_urdu_finetuned.wav")
    generate_coqui_finetuned(urdu_test_3,"12c_coqui_finetuned_weather.wav")
    generate_coqui_finetuned(urdu_test_4,"12d_coqui_finetuned_atm.wav")
    #your own voice reference
    if os.path.exists("./voice_samples/my_voice.wav"):
        generate_coqui_finetuned(urdu_text,"13_coqui_my_voice.wav","./voice_samples/my_voice.wav")
        generate_coqui_finetuned(urdu_short_1,"14_coqui_my_voice_short1.wav","./voice_samples/my_voice.wav")
        generate_coqui_finetuned(urdu_short_2,"15_coqui_my_voice_short2.wav","./voice_samples/my_voice.wav")
    else:
        print("my_voice.wav not found — skipping personal voice samples")
except Exception as error:
    print("coqui fine-tuned failed:",str(error)[:80])

#write summary file (append to existing)
summary_path="./voice_samples/summary.txt"
file_is_new=not os.path.exists(summary_path)
with open(summary_path,"a") as summary_file:
    if file_is_new:
        summary_file.write("TTS Voice Samples\n\n")
        summary_file.write("Test sentence (Urdu): "+urdu_text+"\n")
        summary_file.write("Test sentence (English): "+english_text+"\n\n")
        summary_file.write("notes:\n")
        summary_file.write("- piper: fastest, fully offline, neural tts\n")
        summary_file.write("- indic parler: natural quality offline, but very slow on cpu\n")
        summary_file.write("- edge tts: best quality overall but needs internet\n")
        summary_file.write("- facebook mms-tts: meta's model, fully offline, supports urdu natively\n")
        summary_file.write("- coqui xtts-v2: high quality multilingual, fully offline, voice cloning\n\n")
        summary_file.write("for real-time offline banking assistant with voice cloning,\n")
        summary_file.write("coqui xtts-v2 fine-tuned + gpu is the target.\n")
        summary_file.write("piper is the fallback for cpu-only environments.\n\n")
    if len(all_results)>0:
        summary_file.write("run: "+time.strftime("%Y-%m-%d %H:%M:%S")+"\n")
        for entry in all_results:
            summary_file.write(entry["file"]+"\n")
            summary_file.write("  engine: "+entry["engine"]+"\n")
            summary_file.write("  type: "+entry["type"]+"\n")
            summary_file.write("  audio duration: "+str(entry["duration"])+" seconds\n")
            summary_file.write("  generation time: "+str(entry["generation_time"])+" seconds\n\n")

print("\ndone -",len(all_results),"new samples + summary.txt in ./voice_samples/")