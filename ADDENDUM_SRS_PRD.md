# Dokumen Addendum: Revisi SRS & PRD
## Sistem Manajemen Keuangan Personal Berbasis Telegram Bot

Dokumen ini merupakan addendum resmi untuk melengkapi dan menyempurnakan dokumen **SRS & PRD** sebelumnya, berdasarkan pengujian skenario interaksi manusia nyata (*natural conversation*) dan prinsip *zero-friction CUI (Conversational User Interface)*.

---

### 1. Revisi Algoritma Parsing Transaksi (FR-02 & Parsing Engine)

#### 1.1 Masalah pada Algoritma Lama
* Algoritma sebelumnya mengasumsikan urutan sekuensial kaku: `[Nominal] [Deskripsi]` (contoh: `20k nasi telur`).
* Pengguna nyata sering mengetik dengan nominal di belakang (`nasi 20rb`), nominal di tengah, menggunakan kata pengantar (*stop words* seperti `duit bensin 40rb`), atau menulis angka desimal dengan singkatan ribuan (`25.5rb`).
* Penentuan Income/Expense hanya bersandar pada kata benda kategori (misal `gaji`), belum memiliki *intent cue detector* untuk frasa dinamis seperti `duit dari...` atau `uang dr...`.

#### 1.2 Algoritma Baru: 4-Stage Parsing Pipeline
1. **Stage 1 (Income Intent Detection):**
   * Pindai pola kata kunci pemasukan dinamis menggunakan regex:
     `\b(?:duit\s+dari|uang\s+dr|duit\s+dr|uang\s+dari|dikasih|dapet|dapat|gaji|terima\s+dari|transferan\s+dari)\b`
   * Jika cocok $\rightarrow$ Tetapkan `type = 'INCOME'`, Kategori Default = `'Pendapatan'`.
   * Jika tidak cocok $\rightarrow$ Tetapkan `type = 'EXPENSE'`, Kategori Default = `'Lain-lain'`.
2. **Stage 2 (Universal Magnitude & Position-Agnostic Amount Extraction):**
   * Gunakan regex fleksibel untuk menangkap nominal di posisi mana pun:
     `(?:rp\.?\s*)?(\d+(?:[.,]\d+)?)\s*(k|rb|ribu|jt|juta|m|miliar)?\b`
   * Konversi desimal + magnitudo:
     * `25.5rb` $\rightarrow$ $25.5 \times 1.000 = 25.500$
     * `1.5jt` $\rightarrow$ $1.5 \times 1.000.000 = 1.500.000$
     * `20.000` $\rightarrow$ $20.000$
3. **Stage 3 (Lexical Sanitization & Multi-Token Keyword Matching):**
   * Potong string nominal dari teks untuk menyisakan deskripsi.
   * Bersihkan *filler words* / *stop words* (`duit`, `uang`, `beli`, `buat`, `ke`, `dari`, `dr`).
   * Cocokkan frasa leksikal multi-token (prioritaskan frasa panjang seperti `topup gopay`, `nasi goreng`, `service motor` sebelum kata tunggal).
4. **Stage 4 (Auto-Assignment & Fallback):**
   * Petakan ke `category_id`. Jika tidak ditemukan padanan, tetapkan kategori `'Lain-lain'`.

---

### 2. Standar Antarmuka CUI: "To The Point" (NFR-UX)

#### 2.1 Kebijakan Respons Bot
* **DILARANG** menggunakan salam pembuka panjang (*"Halo kak!"*, *"Catatan keuangan berhasil disimpan..."*).
* Bot wajib membalas secara **padat, akurat, dalam 1-2 baris** maksimal, disertai tombol interaktif **Undo / Batal**.

#### 2.2 Format Output Standar
* **Pencatatan Pengeluaran (Expense):**
  ```text
  ✅ Rp 20.000 | Makanan & Minuman (nasi)
  [❌ Batal]
  ```
* **Pencatatan Pemasukan (Income):**
  ```text
  💰 +Rp 50.000 | Pendapatan (Budi)
  [❌ Batal]
  ```
* **Reaksi Pembatalan (Jika tombol Batal ditekan):**
  Pesan di-update di tempat (*inline edit*):
  ```text
  🗑️ Dibatalkan: Rp 20.000 (nasi)
  ```

---

### 3. Penambahan Fitur Visual: Chart & Rekapitulasi (FR-05 Enhancement)

#### 3.1 Spesifikasi Chart Generator
* **Engine:** `matplotlib` (Headless Agg backend, dieksekusi asinkron).
* **Format:** Gambar PNG dengan tema modern gelap (*dark mode*) yang cocok dengan UI Telegram Desktop / Mobile (`#1E1E2E` background).
* **Tipe Visual:**
  1. **Donut Chart:** Menampilkan persentase porsi pengeluaran per kategori beserta nominal total di lubang tengah donut.
  2. **Text Bar Fallback:** Representasi baris teks berformat indikator batang (`[████░░░░] 45%`) untuk koneksi lemah.

#### 3.2 Perintah Terkait
* `/rekap` atau ketik `rekap` $\rightarrow$ Mengirim chart visual pengeluaran bulan berjalan + rincian teks.
* `/riwayat` atau ketik `riwayat` $\rightarrow$ Menampilkan 5 transaksi terakhir secara ringkas.

---

### 4. Matriks Validasi Skenario Uji Baru

| ID Uji | Input Teks Pengguna | Hasil Ekstraksi Nominal | Tipe | Kategori Terpilih | Deskripsi Bersih | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-07** | `nasi 20rb` | Rp 20.000 | EXPENSE | Makanan & Minuman | nasi | PASS |
| **TC-08** | `duit bensin 40rb` | Rp 40.000 | EXPENSE | Transportasi | bensin | PASS |
| **TC-09** | `topup gopay 25.5rb` | Rp 25.500 | EXPENSE | Top Up / E-Wallet | topup gopay | PASS |
| **TC-10** | `duit dari Budi 50rb` | Rp 50.000 | INCOME | Pendapatan | Budi | PASS |
| **TC-11** | `uang dr kantor 3.5jt` | Rp 3.500.000 | INCOME | Pendapatan | kantor | PASS |
| **TC-12** | `parkir motor 2k` | Rp 2.000 | EXPENSE | Transportasi | parkir motor | PASS |
| **TC-13** | `tekan tombol [Batal]` | - | - | Status data: Deleted | Dihapus dari DB | PASS |
