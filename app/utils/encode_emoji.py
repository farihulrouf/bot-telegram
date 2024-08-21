import emoji

def translate_emoticons_to_text(reactions):
    translated = {}
    for reaction in reactions:
        emoticon = reaction["reaction"]
        # Menggunakan library emoji untuk mendapatkan nama emoji
        text = emoji.demojize(emoticon)
        # Hapus karakter ":" jika ada
        text = text.strip(":")
        translated[text] = reaction[emoticon]
    return translated
