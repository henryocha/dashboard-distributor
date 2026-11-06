import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import glob
import os

# Set halaman web agar melebar rapi
st.set_page_config(page_title="Dashboard Pemenuhan Distributor", layout="wide")

st.title("📊 Dashboard Analisis Pemenuhan Distributor")
st.markdown("Aplikasi web interaktif untuk memantau performa distributor dan item barang secara real-time.")

# Fungsi untuk membaca data gabungan yang sudah diproses sebelumnya
@st.cache_data
def muat_data():
    list_laporan = glob.glob("Laporan_Persentase_Pemenuhan_*.xlsx")
    if not list_laporan:
        list_laporan = glob.glob("C:/Users/IF-CMU 2/Desktop/Laporan_Persentase_Pemenuhan_*.xlsx")
        
    if list_laporan:
        file_terbaru = max(list_laporan, key=os.path.getctime)
        try:
            df_dist = pd.read_excel(file_terbaru, sheet_name="Total Per Distributor")
            df_item = pd.read_excel(file_terbaru, sheet_name="Persen Per Item")
            return df_dist, df_item, os.path.basename(file_terbaru)
        except Exception as e:
            st.error(f"Gagal membaca sheet Excel: {e}")
            return None, None, None
    return None, None, None

df_dist, df_item, nama_file = muat_data()

if df_dist is None or df_item is None:
    st.error("❌ File laporan gabungan Excel tidak ditemukan di Desktop! Pastikan kamu sudah menjalankan script penggabung sebelumnya.")
else:
    st.info(f"📂 Menggunakan sumber data dari: **{nama_file}**")
    
    # Ambil daftar kolom bulan saja
    kolom_bulan_dist = [c for c in df_dist.columns if c not in ['Nama Distributor', 'Rata-rata Semua Bulan']]
    kolom_bulan_item = [c for c in df_item.columns if c not in ['Nama Distributor', 'Nama Obat/Alkes', 'Rata-rata Pemenuhan', 'Jenis Pengadaan']]
    
    # --- FUNGSI MENGUBAH ANGKA DESIMAL MENJADI FORMAT PERSEN TEKS ---
    def format_ke_persen(val):
        if val == "Tidak Ada Pemesanan" or pd.isna(val):
            return "Tidak Ada Pemesanan"
        try:
            num = float(val)
            if num <= 1.0:
                return f"{num * 100:.0f}%"
            return f"{num:.0f}%"
        except:
            return str(val)

    # ------------------ SIDEBAR FILTER ------------------
    st.sidebar.header("⚙️ Pengaturan Filter")
    
    mode_analisis = st.sidebar.radio("Pilih Mode Analisis:", ["Berdasarkan Distributor", "Berdasarkan Nama Obat/Alkes"])
    
    pilihan_dist = ""
    pilihan_item = ""
    
    if mode_analisis == "Berdasarkan Distributor":
        daftar_dist_unik = sorted(list(df_dist['Nama Distributor'].dropna().unique()))
        pilihan_dist = st.sidebar.selectbox("Pilih Nama Distributor:", daftar_dist_unik)
        
        data_filtered_dist = df_dist[df_dist['Nama Distributor'] == pilihan_dist]
        data_filtered_item = df_item[df_item['Nama Distributor'] == pilihan_dist]
            
    else: # Berdasarkan Nama Obat/Alkes
        daftar_obat_unik = sorted(list(df_item['Nama Obat/Alkes'].dropna().unique()))
        pilihan_item = st.sidebar.selectbox("Pilih Nama Obat/Alkes:", daftar_obat_unik)
        
        data_filtered_item = df_item[df_item['Nama Obat/Alkes'] == pilihan_item]
        distributor_terkait = data_filtered_item['Nama Distributor'].unique()
        data_filtered_dist = df_dist[df_dist['Nama Distributor'].isin(distributor_terkait)]

    # ------------------ BARIS UTAMA: KARTU METRIK (KPI) ------------------
    col1, col2, col3 = st.columns(3)
    with col1:
        df_hitung = df_dist['Rata-rata Semua Bulan'].copy()
        df_hitung = pd.to_numeric(df_hitung.replace('Tidak Ada Pemesanan', np.nan), errors='coerce')
        rerata_total = df_hitung.mean()
        st.metric(label="Rata-rata Pemenuhan Nasional", value=f"{rerata_total*100:.1f}%" if not pd.isna(rerata_total) else "0.0%")
    with col2:
        total_dist_aktif = len(data_filtered_dist['Nama Distributor'].unique())
        st.metric(label="Jumlah Distributor Terfilter", value=total_dist_aktif)
    with col3:
        st.metric(label="Fokus Analisis", value=pilihan_dist if mode_analisis == "Berdasarkan Distributor" else pilihan_item)

    st.markdown("---")

    # ------------------ BARIS KEDUA: GRAFIK TREN INTERAKTIF ------------------
    st.subheader("📈 Tren Persentase Pemenuhan Bulanan")
    
    if mode_analisis == "Berdasarkan Distributor":
        df_melt = data_filtered_dist.melt(id_vars=['Nama Distributor'], value_vars=kolom_bulan_dist, var_name='Bulan', value_name='Persentase')
        df_melt['Persentase'] = pd.to_numeric(df_melt['Persentase'].replace('Tidak Ada Pemesanan', 0), errors='coerce')
        
        fig = px.line(df_melt, x='Bulan', y='Persentase', color='Nama Distributor', 
                      markers=True, labels={'Persentase': 'Persen Pemenuhan'},
                      title=f"Perkembangan Pemenuhan Total - {pilihan_dist}")
    else:
        df_melt = data_filtered_item.melt(id_vars=['Nama Distributor', 'Nama Obat/Alkes'], value_vars=kolom_bulan_item, var_name='Bulan', value_name='Persentase')
        df_melt['Persentase'] = pd.to_numeric(df_melt['Persentase'].replace('Tidak Ada Pemesanan', 0), errors='coerce')
        
        fig = px.line(df_melt, x='Bulan', y='Persentase', color='Nama Distributor', 
                      markers=True, labels={'Persentase': 'Persen Pemenuhan'},
                      title=f"Perbandingan Performa Distributor untuk Item: {pilihan_item}")
        
    fig.update_layout(yaxis_tickformat='.0%')
    st.plotly_chart(fig, use_container_width=True)

    # ------------------ BARIS KETIGA: TABEL DATA DETAIL ------------------
    st.subheader("📋 Tabel Rincian Data Persentase")
    
    # Fungsi styling warna otomatis berdasarkan teks persen
    def beri_warna_sel(val):
        if val == "Tidak Ada Pemesanan" or pd.isna(val):
            return ""
        try:
            num = float(str(val).replace('%', '').strip())
            if num >= 80:
                return 'background-color: #C6EFCE; color: #006100;'
            elif num < 80:
                return 'background-color: #FFC7CE; color: #9C0006;'
        except:
            return ""
        return ""

    # KONDISI TAMPILAN TABEL BERDASARKAN MODE ANALISIS
    if mode_analisis == "Berdasarkan Distributor":
        tab1, tab2 = st.tabs(["Total per Distributor", "Detail Rincian per Item Obat/Alkes"])
        with tab1:
            st.markdown("**Persentase Pemenuhan Total (Gabungan Semua Item):**")
            df_tampil_dist = data_filtered_dist.copy()
            for col in kolom_bulan_dist + ['Rata-rata Semua Bulan']:
                df_tampil_dist[col] = df_tampil_dist[col].apply(format_ke_persen)
            st.dataframe(df_tampil_dist.style.map(beri_warna_sel, subset=kolom_bulan_dist + ['Rata-rata Semua Bulan']), use_container_width=True)
            
        with tab2:
            st.markdown(f"**Rincian Item Obat/Alkes dari {pilihan_dist}:**")
            df_tampil_item = data_filtered_item.copy()
            for col in kolom_bulan_item + ['Rata-rata Pemenuhan']:
                df_tampil_item[col] = df_tampil_item[col].apply(format_ke_persen)
            st.dataframe(df_tampil_item.style.map(beri_warna_sel, subset=kolom_bulan_item + ['Rata-rata Pemenuhan']), use_container_width=True)
            
    else: # KELUARAN JIKA MODE FILTER OBAT/ALKES (TAB DIHILANGKAN, LANGSUNG TO THE POINT)
        st.markdown(f"**Rincian Perbandingan Distributor untuk Item: {pilihan_item}**")
        df_tampil_item = data_filtered_item.copy()
        for col in kolom_bulan_item + ['Rata-rata Pemenuhan']:
            df_tampil_item[col] = df_tampil_item[col].apply(format_ke_persen)
        st.dataframe(df_tampil_item.style.map(beri_warna_sel, subset=kolom_bulan_item + ['Rata-rata Pemenuhan']), use_container_width=True)
