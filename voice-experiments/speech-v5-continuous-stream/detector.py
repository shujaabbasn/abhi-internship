package language

import (
      "strings"
      "unicode"
)

// Detect classifies the input text into one of the supported languages.
// It returns the detected Language plus a Mixed flag (true when the text
// contains a meaningful blend of Urdu-like and English tokens).
func Detect(text string) (Language, bool) {
      if strings.TrimSpace(text) == "" {
            return Unknown, false
      }

      var (
            arabicChars int // Urdu/Nastaliq code points
            latinTotal  int
            latinUpper  int // English words start with uppercase
            tokens      int
            urduLatin   int // tokens matching Roman-Urdu lexicon
      )

      words := strings.Fields(text)
      for _, w := range words {
            tokens++
            hasArabic, hasLatin := false, false
            for _, r := range w {
                  switch {
                  case isArabicBlock(r):
                        arabicChars++
                        hasArabic = true
                  case unicode.Is(unicode.Latin, r):
                        latinTotal++
                        if unicode.IsUpper(r) {
                              latinUpper++
                        }
                        hasLatin = true
                  }
            }
            _ = hasLatin
            // A token is "Urdu in Latin script" if it's all-lowercase Latin and
            // matches the small Roman-Urdu function-word lexicon below.
            if hasLatin && !hasArabic && isRomanUrduWord(strings.ToLower(strings.Trim(w, ".,!?؟۔\"'"))) {
                  urduLatin++
            }
      }

      // 1) Native Urdu (Arabic/Nastaliq script) dominates.
      if arabicChars >= 3 {
            // Even one English word alongside native Urdu => Mixed.
            if latinTotal >= 3 {
                  return Urdu, true
            }
            return Urdu, false
      }

      // 2) No Arabic script at all — decide between English / Roman-Urdu / Mixed.
      if tokens == 0 {
            return Unknown, false
      }

      urduRatio := float64(urduLatin) / float64(tokens)
      // English-ness heuristic: most tokens start uppercase OR no Roman-Urdu hits.
      englishLike := urduLatin == 0 || (latinUpper >= tokens/2 && urduRatio < 0.2)

      switch {
      case urduRatio >= 0.6:
            // Predominantly Roman-Urdu tokens. If any English present → Mixed.
            mixed := urduLatin < tokens
            return RomanUrdu, mixed
      case urduRatio > 0.2 && englishLike:
            // A blend of Roman-Urdu and English function words → code-mixed.
            return Mixed, true
      case englishLike:
            return English, false
      default:
            // Low signal — conservatively report Mixed.
            return Mixed, true
      }
}

// isArabicBlock reports whether r is in the Arabic script Unicode blocks
// used by Urdu (Nastaliq uses the same code points as Arabic).
func isArabicBlock(r rune) bool {
      // Arabic (0x0600–0x06FF) and Arabic Supplement (0x0750–0x077F).
      if r >= 0x0600 && r <= 0x06FF {
        return true
      }
      if r >= 0x0750 && r <= 0x077F {
            return true
      }
      return false
}

// romanUrduLexicon is a small but high-coverage set of Roman-Urdu function
// words and very common content words. These appear in nearly every Roman-Urdu
// utterance, so even a 20-word lexicon yields strong detection signal.
var romanUrduLexicon = map[string]struct{}{
      // pronouns
      "mein": {}, "main": {}, "mera": {}, "meri": {}, "mujhe": {}, "mujhay": {},
      "hum": {}, "hamara": {}, "hamari": {}, "tum": {}, "tera": {}, "teri": {},
      "aap": {}, "apka": {}, "apki": {}, "woh": {}, "wo": {}, "yeh": {}, "ye": {},
      "kya": {}, "kis": {}, "kaun": {},
      // verbs / auxiliaries (excluding ambiguous English-shared spellings)
      "hoon": {}, "hun": {}, "hai": {}, "hain": {}, "tha": {}, "thi": {},
      "kar": {}, "karna": {}, "karta": {}, "karti": {}, "chahiye": {},
      "chahta": {}, "chahti": {}, "dekh": {}, "suno": {}, "batao": {}, "batayein": {},
      // common particles (excluding "the", "to", "ho", "ya", "par" which collide with English)
      "liye": {},
      "bhi":  {}, "nahi": {}, "nahin": {},
      "haan": {}, "abhi": {}, "bahut": {}, "thoda": {}, "kuch": {}, "sab": {},
}

func isRomanUrduWord(w string) bool {
      _, ok := romanUrduLexicon[w]
      return ok
}


#postgresql
#vectordb 
#chromadb, quadrant