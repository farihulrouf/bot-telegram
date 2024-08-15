# Kamus emotikon ke teks
# Kamus emotikon ke teks
emoticon_to_text = {
    "❤": "heart",          # Hati
    "👍": "thumbs up",     # Jempol naik
    "🙏": "prayer",        # Doa
    "😢": "crying",        # Menangis
    "😂": "laughing",      # Tertawa
    "😎": "sunglasses",    # Kacamata hitam
    "🎉": "party",         # Pesta
    "💔": "broken heart",  # Hati patah
    "😡": "angry",         # Marah
    "😍": "heart eyes",    # Mata berbentuk hati
    "🥳": "party face",    # Wajah berpesta
    "💪": "muscle",        # Otot
    "🌟": "star",          # Bintang
    "🔥": "fire",          # Api
    "🥺": "pleading",      # Memohon
    "🙌": "raising hands", # Tangan terangkat
    "🎂": "cake",          # Kue
    "🚀": "rocket",        # Roket
    "🌈": "rainbow"        # Pelangi
}

# Fungsi untuk menerjemahkan emotikon ke teks
def translate_emoticons_to_text(reactions):
    translated_reactions = {}
    for reaction in reactions:
        emoticon = reaction.get('reaction')  # Ambil emotikon dari data
        count = reaction.get(emoticon)       # Ambil jumlah dari data
        # Ganti emotikon dengan teks jika ada di kamus
        text = emoticon_to_text.get(emoticon, emoticon)
        translated_reactions[text] = count  # Tambahkan hasil terjemahan ke dictionary baru
    return translated_reactions
