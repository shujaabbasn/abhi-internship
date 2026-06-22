#transliteration layer for urdu arabic script <-> roman urdu
#uses character mapping tables, not perfect but good enough for benchmarking
#lossy in both directions because urdu has characters that map to same roman letter

#arabic script to roman urdu mapping
ARABIC_TO_ROMAN={
    "ا":"a","آ":"aa","ب":"b","پ":"p","ت":"t","ٹ":"t",
    "ث":"s","ج":"j","چ":"ch","ح":"h","خ":"kh",
    "د":"d","ڈ":"d","ذ":"z","ر":"r","ڑ":"r",
    "ز":"z","ژ":"zh","س":"s","ش":"sh","ص":"s",
    "ض":"z","ط":"t","ظ":"z","ع":"a","غ":"gh",
    "ف":"f","ق":"q","ک":"k","گ":"g","ل":"l",
    "م":"m","ن":"n","و":"o","ہ":"h","ھ":"h",
    "ء":"","ی":"i","ے":"e","ئ":"",
    #common combined forms
    "ں":"n","ؤ":"o","إ":"i","أ":"a",
    #diacritics (zabar, zer, pesh)
    "\u064E":"a","\u064F":"u","\u0650":"i",
    "\u0651":"","\u0652":"","\u0670":"a",
    #punctuation
    "۔":".","؟":"?","،":",","؛":";",
    #numbers
    "۰":"0","۱":"1","۲":"2","۳":"3","۴":"4",
    "۵":"5","۶":"6","۷":"7","۸":"8","۹":"9",
    " ":" "
}

#roman to arabic script mapping (best effort, ambiguous by nature)
ROMAN_TO_ARABIC={
    "aa":"آ","kh":"خ","ch":"چ","sh":"ش","gh":"غ","zh":"ژ",
    "a":"ا","b":"ب","p":"پ","t":"ت","s":"س",
    "j":"ج","h":"ہ","d":"د","r":"ر","z":"ز",
    "f":"ف","q":"ق","k":"ک","g":"گ","l":"ل",
    "m":"م","n":"ن","o":"و","w":"و","u":"و",
    "y":"ی","i":"ی","e":"ے",
    " ":" ",".":"۔","?":"؟",",":"،",
    "0":"۰","1":"۱","2":"۲","3":"۳","4":"۴",
    "5":"۵","6":"۶","7":"۷","8":"۸","9":"۹"
}

#sorted by length descending so multi-char mappings match first (like "kh" before "k")
ROMAN_KEYS_SORTED=sorted(ROMAN_TO_ARABIC.keys(),key=len,reverse=True)

def arabic_to_roman(text):
    result=""
    for char in text:
        if char in ARABIC_TO_ROMAN:
            result=result+ARABIC_TO_ROMAN[char]
        else:
            result=result+char #keep unknown chars as is (english words, digits etc)
    return result

def roman_to_arabic(text):
    result=""
    i=0
    text_lower=text.lower()
    while i<len(text_lower):
        matched=False
        for key in ROMAN_KEYS_SORTED:
            if text_lower[i:i+len(key)]==key:
                result=result+ROMAN_TO_ARABIC[key]
                i=i+len(key)
                matched=True
                break
        if matched==False:
            result=result+text[i] #keep unknown chars as is
            i=i+1
    return result
