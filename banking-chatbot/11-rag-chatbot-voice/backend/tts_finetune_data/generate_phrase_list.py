#generates the recording script (phrase list) for fine-tuning the Urdu Piper voice
#(ur_PK-fasih-medium) on banking-domain phrases. English is out of scope - that voice
#already works well.
#pulls real response templates from backend_logic.py and cached_field_prompts.json,
#and reuses the exact production number->word conversion (tts.convert_numbers_to_urdu_words)
#so recorded phrases match exactly what the live app actually sends to TTS.
import sys
import os
import csv
import json

sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
from tts import convert_numbers_to_urdu_words

rows=[]
next_id=[1]

def add_row(emotion_tag,source,text):
    rows.append({
        "id":str(next_id[0]).zfill(4),
        "emotion_tag":emotion_tag,
        "source":source,
        "text":text
    })
    next_id[0]+=1

#wide spread of magnitudes and decimals - the biggest generalization gap in v1
BALANCES=["350","900","1500","4200","8750","15000","25000","33200.50","41700",
    "68500","99999","125000","250000","475000.25","999999","1250000","3400000",
    "7600000","10500000","25000000"]
AMOUNTS=["250","800","1500","2000","3750","5000","9999","12500","25000",
    "50000","87500.50","150000"]
CURRENCIES=["USD","PKR","EUR","GBP"]
CURRENCY_PAIRS=[("USD","PKR"),("EUR","PKR"),("GBP","PKR"),("PKR","USD"),("PKR","EUR")]
CONVERSION_RESULTS=["139500.0","151200.0","176400.0","3.6","3.1"]

#check_balance
add_row("apologetic","check_balance_notfound","اکاؤنٹ نہیں ملا۔")
for balance in BALANCES:
    add_row("neutral","check_balance_success",convert_numbers_to_urdu_words("آپ کا بیلنس "+balance+" روپے ہے۔"))

#send_money
add_row("apologetic","send_money_notfound","آپ کا اکاؤنٹ نہیں ملا۔")
for balance,amount in zip(BALANCES[:8],AMOUNTS[:8]):
    add_row("apologetic","send_money_insufficient",convert_numbers_to_urdu_words(
        "کافی رقم نہیں ہے۔ آپ کا بیلنس "+balance+" روپے ہے، "+amount+" نہیں بھیجے جا سکتے۔"))
for i,(amount,currency) in enumerate(zip(AMOUNTS,CURRENCIES*3)):
    new_balance=BALANCES[i%len(BALANCES)]
    add_row("reassuring","send_money_success",convert_numbers_to_urdu_words(
        amount+" "+currency+" بھیجے جا رہے ہیں۔ ٹرانزیکشن کامیاب رہی۔ نیا بیلنس: "+new_balance+" روپے"))

# currency_conversion
add_row("apologetic","currency_conversion_fail","یہ کرنسی تبدیلی مکمل نہیں ہو سکی۔")
for amount,(from_cur,to_cur),result in zip(AMOUNTS,CURRENCY_PAIRS,CONVERSION_RESULTS):
    add_row("neutral","currency_conversion_success",convert_numbers_to_urdu_words(
        amount+" "+from_cur+" = "+result+" "+to_cur))

# unknown 
add_row("apologetic","unknown","معاف کیجیے، میں سمجھ نہیں سکا۔ براہ کرم دوبارہ واضح طور پر بتائیں۔")

# request_loan 
add_row("friendly","request_loan_decline","اگر آپ کبھی بھی ہمارے قرض کے آپشنز کے بارے میں جاننا چاہیں تو ہمیں بتائیں۔")
add_row("reassuring","request_loan_accept",convert_numbers_to_urdu_words("ہماری ٹیم 2 کاروباری دنوں میں آپ سے رابطہ کرے گی۔"))
add_row("friendly","request_loan_maybe","اگر آپ کا ارادہ بدل جائے تو ہمیں بتائیں۔")

# bank_timings 
add_row("neutral","bank_timings",convert_numbers_to_urdu_words("تمام برانچز صبح 9 بجے کھلتی ہیں اور شام 5 بجے بند ہوتی ہیں۔"))

# not_credited 
add_row("reassuring","not_credited","ہماری ٹیم آپ سے رابطہ کرے گی۔")

# validation error messages (spoken constantly during field collection) 
ERROR_MESSAGES_UR=[
    "غلط کرنسی کوڈ۔ براہ کرم معیاری تین حروف کا کوڈ استعمال کریں، مثلاً یو ایس ڈی، پی کے آر۔",
    "غلط اکاؤنٹ نمبر۔ یہ 10 سے 20 ہندسوں کے درمیان ہونا چاہیے۔",
    "اکاؤنٹ نہیں ملا۔",
    "رقم منفی نہیں ہو سکتی۔",
    "رقم بہت زیادہ ہے۔ براہ کرم بینک سے براہ راست رابطہ کریں۔",
    "رقم ایک عدد ہونی چاہیے۔",
    "شہر کا نام تصدیق نہیں ہو سکا۔ براہ کرم درست شہر کا نام درج کریں۔",
    "براہ کرم 'ہاں' یا 'نہیں' میں جواب دیں۔",
    "آپ اپنے ہی اکاؤنٹ میں رقم نہیں بھیج سکتے۔"
]
for msg in ERROR_MESSAGES_UR:
    add_row("apologetic","validation_error",convert_numbers_to_urdu_words(msg))

# field prompts (asked on nearly every turn, so pronunciation quality matters a lot here) 
field_prompts_path=os.path.join(os.path.dirname(__file__),"..","cached_field_prompts.json")
if os.path.exists(field_prompts_path):
    with open(field_prompts_path,"r") as f:
        field_prompts=json.load(f)
    for field_name,data in field_prompts.items():
        add_row("friendly","field_prompt",data["urdu"])

# free-form knowledge-base style sentences (real gap in v1 - RAG answers about loans/
#accounts are LLM-generated free prose, not templates, so the fine-tune needs exposure
#to natural sentence structure and product names beyond the rigid templates above) 
KNOWLEDGE_BASE_STYLE=[
    "ABHI کئی طرح کے قرضے پیش کرتا ہے، جیسے ٹریکٹر لون، موٹرسائیکل لون اور کاروباری قرضہ۔",
    "کاشتکار قرضہ خاص طور پر کسانوں کی مالی ضروریات پوری کرنے کے لیے بنایا گیا ہے۔",
    "نسواں قرضہ خواتین کاروباری افراد کے لیے ایک قلیل مدتی سہولت ہے۔",
    "آسان اکاؤنٹ میں کوئی کم از کم بیلنس یا لین دین کی شرط نہیں ہے۔",
    "روزانہ منافع اکاؤنٹ آپ کو روزانہ کی بنیاد پر بچت کرنے کا موقع دیتا ہے۔",
    "سہولت کرنٹ اکاؤنٹ کاروباری افراد کے لیے سب سے بہتر انتخاب ہے۔",
    "اعتماد بچت اکاؤنٹ آپ کے مستقبل کو محفوظ بنانے کے لیے بہترین ہے۔",
    "سنہری قرضہ آپ کے سونے کے زیورات کو کاروباری سرمائے میں تبدیل کرتا ہے۔",
    "معذرت، اس سوال کا جواب دستیاب معلومات میں موجود نہیں ہے۔",
    "براہ کرم مزید تفصیلات کے لیے قریبی برانچ سے رابطہ کریں۔",
    "ہمارے تمام قرضہ جات کی شرح سود مسابقتی اور آسان اقساط پر مبنی ہے۔",
    "اے بی ایچ آئی بینک ایپ کے ذریعے آپ گھر بیٹھے تمام سہولات حاصل کر سکتے ہیں۔"
]
for sentence in KNOWLEDGE_BASE_STYLE:
    add_row("neutral","knowledge_base_style",sentence)

# pure number-word coverage (numbers are the highest-value thing to get right) 
NUMBER_COVERAGE=["12","15","28","42","67","99","100","135","350","480","999",
    "1000","2500","4500","7800","9999","10000","15500","25000","48000","99999",
    "100000","175000","250000","500000","999999","1000000","2500000","5000000",
    "10000000","25000000","50000000"]
for number in NUMBER_COVERAGE:
    add_row("neutral","number_coverage",convert_numbers_to_urdu_words(number+" روپے"))

output_path=os.path.join(os.path.dirname(__file__),"phrase_list.csv")
with open(output_path,"w",newline="",encoding="utf-8") as f:
    writer=csv.DictWriter(f,fieldnames=["id","emotion_tag","source","text"])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

print("wrote",len(rows),"phrases to",output_path)