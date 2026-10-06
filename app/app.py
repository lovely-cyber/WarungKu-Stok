import os
import time
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, flash, abort

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "warungku-dev-key")
DATABASE_URL = os.environ["DATABASE_URL"]

KATEGORI = ["Sembako", "Minuman", "Makanan Ringan", "Bumbu Dapur", "Kebersihan", "Lainnya"]


@contextmanager
def cursor():
    """Buka koneksi, commit otomatis kalau sukses, selalu ditutup."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
    finally:
        conn.close()


def init_db():
    for _ in range(15):  # tunggu database siap
        try:
            with cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS barang (
                        id        SERIAL PRIMARY KEY,
                        nama      VARCHAR(100) NOT NULL,
                        kategori  VARCHAR(50)  NOT NULL DEFAULT 'Lainnya',
                        harga     INTEGER NOT NULL CHECK (harga >= 0),
                        stok      INTEGER NOT NULL CHECK (stok >= 0),
                        stok_min  INTEGER NOT NULL DEFAULT 5 CHECK (stok_min >= 0),
                        dibuat    TIMESTAMP NOT NULL DEFAULT NOW()
                    )""")
            return
        except psycopg2.OperationalError:
            time.sleep(2)
    raise RuntimeError("Database tidak bisa dihubungi")


@app.template_filter("rupiah")
def rupiah(n):
    return "Rp " + f"{int(n):,}".replace(",", ".")


@app.context_processor
def inject_kategori():
    return {"kategori": KATEGORI}


def baca_form():
    f = request.form
    kat = f.get("kategori", "Lainnya")
    return (
        f["nama"].strip(),
        kat if kat in KATEGORI else "Lainnya",
        max(0, int(f["harga"])),
        max(0, int(f["stok"])),
        max(0, int(f.get("stok_min", 5))),
    )


# READ
@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    kat = request.args.get("kategori", "")
    sql = "SELECT * FROM barang WHERE nama ILIKE %s"
    params = [f"%{q}%"]
    if kat:
        sql += " AND kategori = %s"
        params.append(kat)
    sql += " ORDER BY (stok <= stok_min) DESC, nama"
    with cursor() as cur:
        cur.execute(sql, params)
        items = cur.fetchall()
        cur.execute("""
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(stok), 0) AS stok,
                   COALESCE(SUM(harga * stok), 0) AS nilai,
                   COALESCE(SUM((stok <= stok_min)::int), 0) AS menipis
            FROM barang""")
        stats = cur.fetchone()
    return render_template("index.html", items=items, stats=stats, q=q, kat=kat)


# CREATE
@app.route("/tambah", methods=["POST"])
def tambah():
    data = baca_form()
    with cursor() as cur:
        cur.execute(
            "INSERT INTO barang (nama, kategori, harga, stok, stok_min) VALUES (%s,%s,%s,%s,%s)",
            data)
    flash(f"{data[0]} sudah ditambahkan.")
    return redirect(url_for("index"))


# UPDATE (ubah data lengkap)
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if request.method == "POST":
        data = baca_form()
        with cursor() as cur:
            cur.execute(
                "UPDATE barang SET nama=%s, kategori=%s, harga=%s, stok=%s, stok_min=%s WHERE id=%s",
                data + (id,))
        flash(f"Perubahan {data[0]} sudah disimpan.")
        return redirect(url_for("index"))
    with cursor() as cur:
        cur.execute("SELECT * FROM barang WHERE id=%s", (id,))
        item = cur.fetchone()
    if item is None:
        abort(404)
    return render_template("edit.html", item=item)


# UPDATE (tambah/kurangi stok cepat)
@app.route("/stok/<int:id>/<int:delta>", methods=["POST"])
@app.route("/stok/<int:id>/-<int:delta>", methods=["POST"], defaults={"neg": True})
def ubah_stok(id, delta, neg=False):
    with cursor() as cur:
        cur.execute("UPDATE barang SET stok = GREATEST(stok + %s, 0) WHERE id=%s",
                    (-delta if neg else delta, id))
    return redirect(request.referrer or url_for("index"))


# DELETE
@app.route("/hapus/<int:id>", methods=["POST"])
def hapus(id):
    with cursor() as cur:
        cur.execute("DELETE FROM barang WHERE id=%s RETURNING nama", (id,))
        row = cur.fetchone()
    if row:
        flash(f"{row['nama']} sudah dihapus.")
    return redirect(url_for("index"))


@app.errorhandler(404)
def tidak_ada(_):
    return render_template("404.html"), 404


init_db()
