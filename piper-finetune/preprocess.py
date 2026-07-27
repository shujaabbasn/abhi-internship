#converts the raw tts-recorder output (118 wav files at 44100hz) into the
#ljspeech-style dataset format piper_train.preprocess expects: a wav/ folder
#at the model's actual training sample rate (22050hz for ur_PK-fasih-medium),
#plus a metadata.csv mapping each file to its transcript.
import subprocess
import os
import csv

RAW_RECORDINGS_DIR="/Users/shuja/abhi-chatbot-cron/tts-recorder/backend/recordings"
PHRASE_LIST_PATH="/Users/shuja/abhi-chatbot-cron/tts-recorder/backend/phrase_list.csv"
OUTPUT_DIR="/Users/shuja/abhi-chatbot-cron/piper-finetune/dataset"
WAV_OUTPUT_DIR=os.path.join(OUTPUT_DIR,"wav")
TARGET_SAMPLE_RATE=22050

os.makedirs(WAV_OUTPUT_DIR,exist_ok=True)

def load_phrases():
    with open(PHRASE_LIST_PATH,"r",encoding="utf-8") as file:
        reader=csv.DictReader(file)
        return list(reader)

def process_one(phrase_id):
    input_path=os.path.join(RAW_RECORDINGS_DIR,phrase_id+".wav")
    if not os.path.exists(input_path):
        return False
    output_path=os.path.join(WAV_OUTPUT_DIR,phrase_id+".wav")
    #silenceremove trims leading/trailing silence, loudnorm normalizes volume
    #to a consistent target, aresample brings it down to the model's training rate
    cmd=[
        "ffmpeg","-y","-i",input_path,
        "-af","silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.1,"
              "areverse,silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.1,areverse,"
              "loudnorm=I=-20:TP=-1.5:LRA=11",
        "-ar",str(TARGET_SAMPLE_RATE),
        "-ac","1",
        output_path
    ]
    result=subprocess.run(cmd,capture_output=True,text=True)
    if result.returncode!=0:
        print("FAILED:",phrase_id,result.stderr[-300:])
        return False
    return True

def main():
    phrases=load_phrases()
    metadata_path=os.path.join(OUTPUT_DIR,"metadata.csv")
    processed=0
    failed=[]
    with open(metadata_path,"w",encoding="utf-8") as metadata_file:
        for phrase in phrases:
            phrase_id=phrase["id"]
            text=phrase["text"]
            success=process_one(phrase_id)
            if not success:
                print("missing recording or failed, skipping:",phrase_id)
                failed.append(phrase_id)
                continue
            metadata_file.write(phrase_id+".wav|"+text+"\n")
            processed+=1

    print()
    print("processed:",processed,"/",len(phrases))
    if failed:
        print("failed/missing:",failed)
    print("dataset written to:",OUTPUT_DIR)

if __name__=="__main__":
    main()