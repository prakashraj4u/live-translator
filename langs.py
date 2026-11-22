# code: naam, whisper (sunne ke liye), nllb (translate ke liye), mms (bolne ke liye), "your turn"
LANGS = {
    "hi": dict(name="Hindi",     whisper="hi", nllb="hin_Deva", mms="hin", turn="आपकी बारी"),
    "en": dict(name="English",   whisper="en", nllb="eng_Latn", mms="eng", turn="Your turn"),
    "bn": dict(name="Bengali",   whisper="bn", nllb="ben_Beng", mms="ben", turn="আপনার পালা"),
    "ta": dict(name="Tamil",     whisper="ta", nllb="tam_Taml", mms="tam", turn="உங்கள் முறை"),
    "te": dict(name="Telugu",    whisper="te", nllb="tel_Telu", mms="tel", turn="మీ వంతు"),
    "mr": dict(name="Marathi",   whisper="mr", nllb="mar_Deva", mms="mar", turn="तुमची पाळी"),
    "gu": dict(name="Gujarati",  whisper="gu", nllb="guj_Gujr", mms="guj", turn="તમારો વારો"),
    "kn": dict(name="Kannada",   whisper="kn", nllb="kan_Knda", mms="kan", turn="ನಿಮ್ಮ ಸರದಿ"),
    "ml": dict(name="Malayalam", whisper="ml", nllb="mal_Mlym", mms="mal", turn="നിങ്ങളുടെ ഊഴം"),
    "pa": dict(name="Punjabi",   whisper="pa", nllb="pan_Guru", mms="pan", turn="ਤੁਹਾਡੀ ਵਾਰੀ"),
    "ur": dict(name="Urdu",      whisper="ur", nllb="urd_Arab", mms="urd-script_arabic", turn="آپ کی باری"),
    "ne": dict(name="Nepali",    whisper="ne", nllb="npi_Deva", mms="npi", turn="तपाईंको पालो"),
    "as": dict(name="Assamese",  whisper="as", nllb="asm_Beng", mms="asm", turn="আপোনাৰ পাল"),
    "or": dict(name="Odia",      whisper=None, nllb="ory_Orya", mms="ory", turn="ଆପଣଙ୍କ ପାଳି"),  # Odia sunna Whisper me nahi hai
}
