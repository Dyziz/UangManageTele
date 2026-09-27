# Bot Telegram Pengatur Keuangan (Anti Ribet) ⚡

Bot Telegram pencatat keuangan super cepat dengan prinsip **langsung to the point tanpa basa-basi**. Tinggal ketik pengeluaran pakai bahasa sehari-hari, data langsung masuk ke database lokal, dan ada grafik visualnya btw ini kebikin gegara gw males pake webnya lol (kalo penasaran web nya bisa kontak langsung ke gw).

---

## ⚡ Fitur Utama

1. **Bahasa Santai & Posisi Angka Bebas**
   - Ketik sesuka hati tanpa format kaku:
     - `nasi 20rb` $\rightarrow$ Makanan & Minuman (Rp 20.000)
     - `duit bensin 40rb` $\rightarrow$ Transportasi (Rp 40.000)
     - `topup gopay 25.5rb` $\rightarrow$ Top Up / E-Wallet (Rp 25.500)
   - Teks yang ada penanda seperti `duit dari Budi 50rb` atau `uang dr freelance 1.5jt` otomatis dicatat sebagai **Pendapatan (Income)**.

2. **Respon Simpel Gak Bacot (Anti Basa-Basi)**
   - Gak ada teks panjang lebar atau salam pembuka kayak AI/Gemini.
   - Bot cuma balas 1 baris konfirmasi ringkas:
     ```text
     ✅ Rp 20.000 | Makanan & Minuman (nasi)
     [❌ Batal]
     ```
   - Salah catat? Tinggal klik tombol **`[❌ Batal]`**, data langsung dihapus detik itu juga dari database.

3. **Indikator Visual Chart Pengeluaran**
   - Cukup ketik `rekap`, bot langsung kirim grafik **Donut Chart** (*dark mode*) dan indikator bar teks untuk ngecek porsi pengeluaranmu bulan ini secara visual.

4. **Riwayat Transaksi Rapi (Ada Halaman Next/Prev)**
   - Ketik `riwayat`, bot menampilkan catatan transaksi lengkap dengan tanggal & jam.
   - Ditampilkan 5 transaksi per halaman, lengkap dengan tombol interaktif **`[⬅️ Prev]`** dan **`[Next ➡️]`** buat gonta-ganti halaman tanpa menuh-menuhin chat.

---

## 🚀 Cara Menjalankan Sendiri (Self-Hosted)

### 1. Setup Environment
```bash
# 1. Masuk ke folder project
cd UangManageTele

# 2. Buat & aktifkan Virtual Environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install Dependensi
pip install -r requirements.txt
```

### 2. Dapatkan Token Bot Telegram
1. Buka Telegram, cari **[@BotFather](https://t.me/BotFather)**.
2. Ketik `/newbot`, ikuti petunjuk sampai dapat **HTTP API Token**.

### 3. Konfigurasi Token
Salin file `.env.example` menjadi `.env`, lalu masukkan token bot kamu:
```env
TELEGRAM_BOT_TOKEN=token_bot_dari_botfather_disini
```

### 4. Jalankan Bot
```bash
python bot.py
```
Buka bot kamu di Telegram, tekan `/start`, dan langsung coba catat transaksi pertamamu!

---

## 🛠️ Mau Tambah / Ubah Kategori Sendiri?

Buka file **`src/parser.py`**, cari bagian `DEFAULT_CATEGORY_RULES`, dan tambahkan kata kuncimu sendiri:

```python
DEFAULT_CATEGORY_RULES = [
    # Contoh kategori Kucing / Pets
    (r'\b(whiskas|pasir|cat\s*food|wetfood|dokter\s*hewan)\b', 'Kebutuhan Kucing', 'EXPENSE'),

    # Contoh kategori Game
    (r'\b(valorant|vp|steam|genshin|mlbb|diamond)\b', 'Game & Hiburan', 'EXPENSE'),
]
```
Bot akan otomatis memetakan kata-kata baru tersebut ke kategori pilihanmu.

---

## 🔒 Privasi
File token `.env` dan database `finance.db` sudah otomatis masuk ke `.gitignore`, jadi aman dan tidak akan pernah ter-upload saat kamu push ke GitHub.
