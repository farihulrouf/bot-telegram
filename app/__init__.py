import os
from app.models.telegram_model import sessions, create_client

# Membuat direktori sessions jika belum ada
if not os.path.exists('sessions'):
    os.makedirs('sessions')

# Memuat sesi yang ada dari direktori sessions
session_files = [f for f in os.listdir('sessions') if f.endswith('.session')]
for session_file in session_files:
    phone = session_file.replace('.session', '')
    client = create_client(phone)
    sessions[phone] = client
