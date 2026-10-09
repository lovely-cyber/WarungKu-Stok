# WarungKu Stok

Aplikasi web pencatatan stok barang warung. Dibuat dengan Flask dan PostgreSQL, dijalankan dengan Docker Compose.

## Fitur
- Login dengan dua peran: admin (semua fitur) dan karyawan (lihat daftar dan ubah stok saja)
- CRUD barang: tambah, lihat, ubah, hapus
- Tombol + / - untuk mengubah stok dengan cepat
- Batas stok hampir habis per barang, dengan penanda otomatis
- Pencarian nama dan filter kategori
- Ringkasan: jenis barang, total stok, nilai stok, jumlah barang hampir habis

## Menjalankan
    cp .env.example .env     # lewati jika file .env sudah ada
    docker compose up --build

| Layanan | Alamat |
|---|---|
| Aplikasi | http://localhost:5000 |
| Adminer (database) | http://localhost:8080 (System: PostgreSQL, Server: db, isi lainnya dari .env) |

## Akun
Username, email, dan password diatur di file `.env` (lihat `.env.example`). Pilih peran saat login.

## Menghentikan
    docker compose down        # data tetap ada (volume dbdata)
    docker compose down -v     # hapus data juga

## Arsitektur container
| Container | Image | Fungsi |
|---|---|---|
| warungku_web | dibuild dari Dockerfile (python:3.12-slim + gunicorn, user non-root) | Aplikasi Flask |
| warungku_db | postgres:16-alpine | Database, volume dbdata, healthcheck |
| warungku_adminer | adminer | Melihat isi database |

Ketiganya berada di jaringan `warungku-net`. Web baru berjalan setelah database sehat.
