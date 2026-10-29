from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

# ----------------------------------------------------------------------------
# Konfigurasi halaman & gaya visual
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Dashboard E-Commerce Olist", page_icon="🛒", layout="wide")

sns.set_theme(style="whitegrid")
plt.rcParams.update({
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
})
HIGHLIGHT = "#2A7FA8"
MUTED = "#C9CED3"
ALERT = "#D9534F"

DATA_PATH = Path(__file__).parent / "main_data.csv"
COMPLETE_START = pd.Timestamp("2017-01-01")  # periode sebelum ini terlalu sedikit pesanannya
COMPLETE_END = pd.Timestamp("2018-08-31")  # setelah ini data tidak lengkap


# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["order_purchase_timestamp"])
    df["order_date"] = df["order_purchase_timestamp"].dt.normalize()
    return df


def build_rfm(df: pd.DataFrame):
    """RFM per customer_unique_id + segmentasi dengan aturan manual (sama dengan notebook)."""
    if df["customer_unique_id"].nunique() < 8:
        return None  # kuartil tidak bermakna untuk pelanggan yang sangat sedikit
    reference_date = df["order_purchase_timestamp"].max().normalize() + pd.Timedelta(days=1)
    rfm = (
        df.groupby("customer_unique_id")
        .agg(last_purchase=("order_purchase_timestamp", "max"),
             frequency=("order_id", "nunique"),
             monetary=("price", "sum"))
        .reset_index()
    )
    rfm["recency"] = (reference_date - rfm["last_purchase"].dt.normalize()).dt.days
    rfm["r_score"] = pd.qcut(rfm["recency"].rank(method="first", ascending=False), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)

    def segment(row):
        recent = row["r_score"] >= 3
        if row["frequency"] >= 2:
            return "Loyal" if recent else "Repeat - Lama Tidak Aktif"
        if recent:
            return "Baru - Big Spender" if row["m_score"] == 4 else "Baru"
        return "Dormant - Big Spender" if row["m_score"] == 4 else "Dormant"

    rfm["segment"] = rfm.apply(segment, axis=1)
    return rfm


def style_barh(ax, fmt="{:,.0f}"):
    ax.grid(axis="y", visible=False)
    for p in ax.patches:
        ax.text(p.get_width(), p.get_y() + p.get_height() / 2, " " + fmt.format(p.get_width()),
                va="center", fontsize=9)
    ax.set_xlim(0, ax.get_xlim()[1] * 1.15)


def render_rfm(rfm: pd.DataFrame) -> None:
    seg = (
        rfm.groupby("segment")
        .agg(customers=("customer_unique_id", "count"), avg_recency=("recency", "mean"),
             avg_frequency=("frequency", "mean"), avg_monetary=("monetary", "mean"),
             total_monetary=("monetary", "sum"))
    )
    seg["customer_share"] = seg["customers"] / seg["customers"].sum() * 100
    seg["revenue_share"] = seg["total_monetary"] / seg["total_monetary"].sum() * 100
    seg = seg.sort_values("revenue_share", ascending=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Median recency", f"{rfm['recency'].median():.0f} hari")
    m2.metric("Pelanggan membeli >1 kali", f"{(rfm['frequency'] >= 2).mean() * 100:.1f}%")
    m3.metric("Median belanja per pelanggan", f"R$ {rfm['monetary'].median():,.0f}")

    is_big = ["Big Spender" in s for s in seg.index]
    colors = [HIGHLIGHT if b else MUTED for b in is_big]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4), sharey=True)
    axes[0].barh(seg.index, seg["customer_share"], color=colors)
    axes[1].barh(seg.index, seg["revenue_share"], color=colors)
    big_c, big_r = seg.loc[is_big, "customer_share"].sum(), seg.loc[is_big, "revenue_share"].sum()
    axes[0].set_title(f"Big Spender (biru): {big_c:.0f}% pelanggan")
    axes[1].set_title(f"...menyumbang {big_r:.0f}% pendapatan")
    axes[0].set_xlabel("% dari seluruh pelanggan")
    axes[1].set_xlabel("% dari seluruh pendapatan")
    for ax in axes:
        style_barh(ax, "{:.1f}%")
    plt.tight_layout()
    st.pyplot(fig)

    with st.expander("Lihat tabel ringkasan segmen"):
        table = seg.sort_values("revenue_share", ascending=False).rename(columns={
            "customers": "Pelanggan", "avg_recency": "Rata-rata recency (hari)", "avg_frequency": "Rata-rata frequency",
            "avg_monetary": "Rata-rata monetary (R$)", "total_monetary": "Total monetary (R$)",
            "customer_share": "% pelanggan", "revenue_share": "% pendapatan",
        })
        st.dataframe(table.round(1))
    st.caption(
        "Recency & Monetary diberi skor kuartil 1-4; Frequency dikelompokkan manual (1 kali vs 2 kali atau lebih) "
        "karena hampir semua pelanggan hanya membeli sekali."
    )


# ----------------------------------------------------------------------------
# Sidebar: filter
# ----------------------------------------------------------------------------
data = load_data()
data_min = data["order_date"].min().date()
data_max = data["order_date"].max().date()

st.sidebar.header("Filter")
date_range = st.sidebar.date_input(
    "Rentang tanggal pembelian",
    value=(max(COMPLETE_START.date(), data_min), min(COMPLETE_END.date(), data_max)),
    min_value=data_min,
    max_value=data_max,
    help="Default memakai periode data yang lengkap (Jan 2017 - Agu 2018).",
)
all_states = sorted(data["customer_state"].dropna().unique())
selected_states = st.sidebar.multiselect("State pelanggan", options=all_states, default=all_states)
st.sidebar.caption(
    "Analisis hanya memakai pesanan berstatus *delivered*. "
    "Pendapatan = jumlah harga produk (tanpa ongkos kirim)."
)

if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Pilih tanggal akhir pada filter untuk menampilkan dashboard.")
    st.stop()

start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
filtered = data[
    (data["order_date"] >= start_date)
    & (data["order_date"] <= end_date)
    & (data["customer_state"].isin(selected_states))
]
if filtered.empty:
    st.warning("Tidak ada data untuk filter yang dipilih. Ubah rentang tanggal atau state.")
    st.stop()

# ----------------------------------------------------------------------------
# Header & KPI
# ----------------------------------------------------------------------------
st.title("🛒 Dashboard E-Commerce Olist")
st.caption(f"Periode: {start_date:%d %b %Y} - {end_date:%d %b %Y} | {len(selected_states)} state dipilih")

order_level = filtered.drop_duplicates("order_id")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Jumlah pesanan", f"{order_level['order_id'].nunique():,}")
c2.metric("Total pendapatan", f"R$ {filtered['price'].sum():,.0f}")
c3.metric("Pelanggan unik", f"{filtered['customer_unique_id'].nunique():,}")
c4.metric("Rata-rata skor ulasan", f"{order_level['review_score'].mean():.2f} / 5")

# ----------------------------------------------------------------------------
# 1. Tren penjualan
# ----------------------------------------------------------------------------
st.header("1. Tren Pesanan dan Pendapatan")
monthly = (
    filtered.assign(month=filtered["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp())
    .groupby("month")
    .agg(order_count=("order_id", "nunique"), revenue=("price", "sum"))
    .reset_index()
)
if len(monthly) >= 2:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    peak = monthly.loc[monthly["order_count"].idxmax()]
    for ax, col, label in zip(axes, ["order_count", "revenue"], ["Jumlah pesanan", "Pendapatan (R$ ribu)"]):
        ax.plot(monthly["month"], monthly[col], color=HIGHLIGHT, linewidth=2.2, marker="o", markersize=4)
        pk = monthly.loc[monthly[col].idxmax()]
        ax.scatter(pk["month"], pk[col], color=ALERT, zorder=5, s=55)
        ax.set_ylabel(label)
        ax.set_ylim(bottom=0)
        ax.grid(axis="x", visible=False)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
        ax.tick_params(axis="x", rotation=45)
    axes[1].yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v / 1000:,.0f}"))
    axes[0].set_title(f"Pesanan per bulan (puncak: {peak['month']:%b %Y})")
    axes[1].set_title("Pendapatan per bulan")
    plt.tight_layout()
    st.pyplot(fig)
else:
    st.info("Pilih rentang minimal dua bulan untuk melihat tren.")

# ----------------------------------------------------------------------------
# 2. Kategori produk
# ----------------------------------------------------------------------------
st.header("2. Kategori Produk")
category_rev = (
    filtered[filtered["product_category_name_english"] != "unknown"]
    .groupby("product_category_name_english")["price"].sum()
    .sort_values(ascending=False)
)
if len(category_rev) >= 1:
    n_show = min(5, len(category_rev))
    top = category_rev.head(n_show)
    bottom = category_rev.tail(n_show).sort_values(ascending=False)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    axes[0].barh(top.index[::-1], top.values[::-1] / 1000, color=[MUTED] * (n_show - 1) + [HIGHLIGHT])
    axes[0].set_title(f"{n_show} kategori dengan pendapatan tertinggi")
    axes[0].set_xlabel("Pendapatan (R$ ribu)")
    axes[1].barh(bottom.index[::-1], bottom.values[::-1], color=[ALERT] + [MUTED] * (n_show - 1))
    axes[1].set_title(f"{n_show} kategori dengan pendapatan terendah")
    axes[1].set_xlabel("Pendapatan (R$, bukan ribu)")
    for ax in axes:
        style_barh(ax)
    plt.tight_layout()
    st.pyplot(fig)
    st.caption("Kategori terendah bervolume sangat kecil, jadi dibaca sebagai kategori ceruk, bukan performa buruk.")

# ----------------------------------------------------------------------------
# 3. Wilayah (geospasial)
# ----------------------------------------------------------------------------
st.header("3. Sebaran Wilayah")
state_summary = (
    filtered.groupby("customer_state")
    .agg(customers=("customer_unique_id", "nunique"), revenue=("price", "sum"))
    .sort_values("revenue", ascending=False)
)
left, right = st.columns(2)

with left:
    top_states = state_summary.head(10)
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    ax.bar(top_states.index, top_states["revenue"] / 1000,
           color=[HIGHLIGHT] + [MUTED] * (len(top_states) - 1))
    ax.set_title("10 state dengan pendapatan tertinggi")
    ax.set_ylabel("Pendapatan (R$ ribu)")
    ax.set_xlabel("State")
    ax.grid(axis="x", visible=False)
    plt.tight_layout()
    st.pyplot(fig)

with right:
    geo = filtered.dropna(subset=["customer_lat", "customer_lng"])
    if geo.empty:
        st.info("Tidak ada data koordinat untuk filter ini.")
    else:
        zip_level = geo.drop_duplicates("customer_zip_code_prefix")
        state_geo = (
            geo.groupby("customer_state")
            .apply(lambda g: pd.Series({
                "lat": np.average(g["customer_lat"], weights=g["price"]),
                "lng": np.average(g["customer_lng"], weights=g["price"]),
                "revenue": g["price"].sum(),
            }))
        )
        # Luas lingkaran = pendapatan / 1500 (skala tetap, sehingga ukuran antar-filter bisa dibandingkan)
        fig, ax = plt.subplots(figsize=(6.5, 4.6))
        ax.scatter(zip_level["customer_lng"], zip_level["customer_lat"], s=2, color=MUTED, alpha=0.5, linewidths=0)
        ax.scatter(state_geo["lng"], state_geo["lat"], s=state_geo["revenue"] / 1500,
                   color=HIGHLIGHT, alpha=0.55, edgecolors="white", linewidths=1)
        for st_code, row in state_geo.sort_values("revenue", ascending=False).head(8).iterrows():
            ax.annotate(st_code, (row["lng"], row["lat"]), ha="center", va="center", fontsize=8, fontweight="bold")
        ax.set_title("Peta pendapatan per state")
        ax.set_aspect("equal")
        ax.set_xlabel("Bujur")
        ax.set_ylabel("Lintang")
        ax.grid(False)
        plt.tight_layout()
        st.pyplot(fig)
        st.caption("Titik abu-abu = kode pos pelanggan. Luas lingkaran biru sebanding dengan pendapatan state.")

# ----------------------------------------------------------------------------
# 4. RFM
# ----------------------------------------------------------------------------
st.header("4. Segmentasi Pelanggan (RFM)")
rfm = build_rfm(filtered)
if rfm is None:
    st.info("Jumlah pelanggan pada filter ini terlalu sedikit untuk segmentasi RFM. Perluas rentang tanggal atau state.")
else:
    render_rfm(rfm)

# ----------------------------------------------------------------------------
# 5. Keterlambatan vs ulasan (binning)
# ----------------------------------------------------------------------------
st.header("5. Keterlambatan Pengiriman dan Skor Ulasan")
reviewed = filtered.drop_duplicates("order_id").dropna(subset=["review_score"]).copy()
labels = ["Lebih cepat >7 hari", "Tepat waktu / lebih cepat 0-7 hari", "Telat 1-3 hari", "Telat 4-7 hari", "Telat >7 hari"]
reviewed["delay_group"] = pd.cut(reviewed["delay_days"], bins=[-np.inf, -8, 0, 3, 7, np.inf], labels=labels)
delay_summary = (
    reviewed.groupby("delay_group", observed=False)
    .agg(orders=("order_id", "count"), avg_review=("review_score", "mean"),
         pct_bad=("review_score", lambda s: (s <= 2).mean() * 100 if len(s) else np.nan))
)
fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
bar_colors = [MUTED, MUTED, "#F2C4C2", "#E8A09E", ALERT]
xt = [l.replace(" / ", "\n").replace(" hari", "\nhari") for l in labels]
for ax, col, title, ylabel, ylim in [
    (axes[0], "avg_review", "Semakin telat, skor ulasan semakin rendah", "Rata-rata skor ulasan (1-5)", (0, 5)),
    (axes[1], "pct_bad", "Proporsi ulasan buruk (skor 1-2) naik saat telat", "% ulasan skor 1 atau 2", (0, 100)),
]:
    vals = delay_summary[col]
    keep = vals.notna().to_numpy()  # kelompok tanpa data tidak digambar (bukan nol)
    ax.bar(np.arange(len(labels))[keep], vals[keep], color=[c for c, k in zip(bar_colors, keep) if k])
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(xt, fontsize=8)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_ylim(*ylim)
    ax.set_xlabel("Kelompok keterlambatan terhadap estimasi")
    ax.grid(axis="x", visible=False)
    for i, v in enumerate(delay_summary[col]):
        if pd.notna(v):
            ax.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=9)
plt.tight_layout()
st.pyplot(fig)
st.caption("Ini menunjukkan hubungan (asosiasi), bukan bukti sebab-akibat.")

st.divider()
st.caption("Sumber data: Brazilian E-Commerce Public Dataset by Olist (Kaggle).")
