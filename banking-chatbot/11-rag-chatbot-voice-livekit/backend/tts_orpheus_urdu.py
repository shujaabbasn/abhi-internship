import os
import tempfile
import threading

MODELS_DIR=os.path.join(os.path.dirname(__file__),"models")
ORPHEUS_URDU_DIR=os.path.join(MODELS_DIR,"orpheus-urdu")

_orpheus_urdu_state={"model":None,"tokenizer":None}
_snac_state={"model":None}
_orpheus_lock=threading.Lock()

def unload_orpheus_urdu():
    #orpheus (6.2GB) and xtts (5.3GB) can't both fit in memory on a 16GB machine,
    #so whichever engine is switched away from gets evicted before the other loads
    import gc
    with _orpheus_lock:
        _orpheus_urdu_state["model"]=None
        _orpheus_urdu_state["tokenizer"]=None
        _snac_state["model"]=None
    gc.collect()

def _snac_convert_to_audio(codes):
    import torch
    if _snac_state["model"] is None:
        with _orpheus_lock:
            if _snac_state["model"] is None:
                from snac import SNAC
                _snac_state["model"]=SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval()
    snac_model=_snac_state["model"]

    num_frames=len(codes)//7
    codes=codes[:num_frames*7]
    codes_0=[]
    codes_1=[]
    codes_2=[]
    for j in range(num_frames):
        i=7*j
        codes_0.append(codes[i])
        codes_1.append(codes[i+1])
        codes_1.append(codes[i+4])
        codes_2.append(codes[i+2])
        codes_2.append(codes[i+3])
        codes_2.append(codes[i+5])
        codes_2.append(codes[i+6])

    code_tensors=[
        torch.tensor(codes_0,dtype=torch.int32).unsqueeze(0),
        torch.tensor(codes_1,dtype=torch.int32).unsqueeze(0),
        torch.tensor(codes_2,dtype=torch.int32).unsqueeze(0)
    ]
    with torch.inference_mode():
        audio_hat=snac_model.decode(code_tensors)
    return audio_hat

def synthesize_orpheus_urdu(text,speed):
    import torch
    import torchaudio
    from transformers import AutoTokenizer,AutoModelForCausalLM

    if _orpheus_urdu_state["model"] is None:
        with _orpheus_lock:
            if _orpheus_urdu_state["model"] is None:
                tokenizer=AutoTokenizer.from_pretrained(ORPHEUS_URDU_DIR)
                model=AutoModelForCausalLM.from_pretrained(ORPHEUS_URDU_DIR,torch_dtype=torch.bfloat16,attn_implementation="sdpa")
                model.eval()
                _orpheus_urdu_state["model"]=model
                _orpheus_urdu_state["tokenizer"]=tokenizer

    model=_orpheus_urdu_state["model"]
    tokenizer=_orpheus_urdu_state["tokenizer"]
    device=model.device

    prompt_tokens=tokenizer(text,return_tensors="pt")
    start_token=torch.tensor([[128259]],dtype=torch.int64)
    end_tokens=torch.tensor([[128009,128260,128261,128257]],dtype=torch.int64)
    input_ids=torch.cat([start_token,prompt_tokens.input_ids,end_tokens],dim=1).to(device)
    attention_mask=torch.ones_like(input_ids)

    with torch.inference_mode():
        generated=model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=400,
            do_sample=True,
            temperature=0.6,
            top_p=0.8,
            repetition_penalty=1.3,
            eos_token_id=128258
        )

    new_ids=generated[0][input_ids.shape[1]:].tolist()
    codes=[]
    index=0
    for token_id in new_ids:
        token_string=tokenizer.decode([token_id])
        if "<custom_token_" not in token_string:
            continue
        try:
            number_str=token_string[token_string.rfind("<custom_token_")+14:].rstrip(">")
            code_value=int(number_str)-10-((index%7)*4096)
        except ValueError:
            continue
        if code_value>0:
            codes.append(code_value)
            index+=1

    if len(codes)<7:
        raise RuntimeError("Orpheus produced no usable audio tokens for this input.")

    audio_hat=_snac_convert_to_audio(codes)
    wav=audio_hat.squeeze(0).detach().cpu()
    fd,output_wav=tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        torchaudio.save(output_wav,wav,24000)
        with open(output_wav,"rb") as file:
            return file.read()
    finally:
        os.remove(output_wav)