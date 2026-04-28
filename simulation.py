import streamlit as st
import simpy
import random
import pandas as pd
import plotly.express as px

# --- SİMÜLASYON DEĞİŞKENLERİ ---
LEAD_TIMES = []
FINANSAL_SONUCLAR = []
TAMAMLANAN_SIPARIS = 0

# --- SİMÜLASYON MODELİ (SimPy) ---
def pergola_uretim(env, isim, kesim, cnc, montaj, hedef_sure, wip_saat_maliyet, ceza_saat_maliyet):
    global TAMAMLANAN_SIPARIS, FINANSAL_SONUCLAR
    gelis_zamani = env.now

    # 1. Alüminyum Kesim
    with kesim.request() as req:
        yield req
        yield env.timeout(random.triangular(1.0, 1.5, 2.5)) 

    # 2. CNC Profil İşleme
    with cnc.request() as req:
        yield req
        yield env.timeout(random.triangular(2.0, 3.0, 4.5))

    # 3. Montaj
    with montaj.request() as req:
        yield req
        yield env.timeout(random.triangular(4.0, 6.0, 8.0))

    # Zaman Metrikleri
    lead_time = env.now - gelis_zamani
    gecikme_suresi = max(0, lead_time - hedef_sure)
    
    # Finansal Metrikler
    siparis_wip_maliyeti = lead_time * wip_saat_maliyet
    siparis_ceza_maliyeti = gecikme_suresi * ceza_saat_maliyet
    toplam_maliyet = siparis_wip_maliyeti + siparis_ceza_maliyeti

    LEAD_TIMES.append({
        'Sipariş': isim, 
        'Teslim_Suresi_Saat': lead_time,
        'Gecikme_Saat': gecikme_suresi
    })
    
    FINANSAL_SONUCLAR.append({
        'Sipariş': isim,
        'WIP_Maliyeti_TL': siparis_wip_maliyeti,
        'Gecikme_Cezasi_TL': siparis_ceza_maliyeti,
        'Toplam_Gizli_Maliyet_TL': toplam_maliyet
    })
    
    TAMAMLANAN_SIPARIS += 1

def siparis_olusturucu(env, siparis_gelis_sikligi, kesim, cnc, montaj, hedef, wip, ceza):
    i = 0
    while True:
        yield env.timeout(random.expovariate(1.0 / siparis_gelis_sikligi))
        i += 1
        env.process(pergola_uretim(env, f'Sipariş {i}', kesim, cnc, montaj, hedef, wip, ceza))

def simulasyonu_baslat(kesim_kap, cnc_kap, montaj_kap, sip_siklik, sim_suresi, hedef, wip, ceza):
    global LEAD_TIMES, FINANSAL_SONUCLAR, TAMAMLANAN_SIPARIS
    LEAD_TIMES = []
    FINANSAL_SONUCLAR = []
    TAMAMLANAN_SIPARIS = 0

    env = simpy.Environment()
    kesim = simpy.Resource(env, capacity=kesim_kap)
    cnc = simpy.Resource(env, capacity=cnc_kap)
    montaj = simpy.Resource(env, capacity=montaj_kap)

    env.process(siparis_olusturucu(env, sip_siklik, kesim, cnc, montaj, hedef, wip, ceza))
    env.run(until=sim_suresi)
    
    return pd.DataFrame(LEAD_TIMES), pd.DataFrame(FINANSAL_SONUCLAR), TAMAMLANAN_SIPARIS

# --- STREAMLIT ARAYÜZÜ ---
st.set_page_config(page_title="Matek Finansal Simülasyon", layout="wide")

st.title("🏭 Biyoklimatik Pergola - Finansal & Operasyonel Dijital İkiz")
st.markdown("Sistemdeki darboğazların yarattığı **gizli maliyetleri (fırsat maliyeti, ceza ve WIP)** analiz edin.")

# --- YAN PANEL ---
st.sidebar.header("⚙️ Üretim Parametreleri")
kesim_makinesi = st.sidebar.slider("Kesim Makinesi", 1, 5, 1)
cnc_makinesi = st.sidebar.slider("CNC İşleme Merkezi", 1, 5, 2)
montaj_istasyonu = st.sidebar.slider("Montaj Ekibi", 1, 10, 3)
siparis_sikligi = st.sidebar.slider("Sipariş Geliş Süresi (Saat)", 1.0, 10.0, 4.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.header("💰 Finansal Parametreler")
hedef_sure = st.sidebar.number_input("Hedef Teslim Süresi (Saat)", value=24)
ceza_maliyeti = st.sidebar.number_input("Gecikme Cezası (TL/Saat)", value=500, help="Sözleşme cezası veya müşteri kaybı fırsat maliyeti")
wip_maliyeti = st.sidebar.number_input("WIP Stok Maliyeti (TL/Saat)", value=50, help="Yarı mamulün hatta bekleme maliyeti")
ekip_maliyeti = st.sidebar.number_input("1 Montaj Ekibinin Günlük Maliyeti (TL)", value=3000)

sim_gunu = st.sidebar.slider("Simülasyon Süresi (Gün)", 10, 90, 30)
sim_saati = sim_gunu * 8 

# --- ANA EKRAN ---
if st.sidebar.button("🚀 Finansal Simülasyonu Çalıştır", type="primary"):
    with st.spinner("Sistem ve maliyetler hesaplanıyor..."):
        df_zaman, df_finans, toplam_uretim = simulasyonu_baslat(
            kesim_makinesi, cnc_makinesi, montaj_istasyonu, siparis_sikligi, sim_saati, 
            hedef_sure, wip_maliyeti, ceza_maliyeti
        )

    if not df_zaman.empty:
        # Metrik Hesaplamaları
        ort_lead_time = df_zaman['Teslim_Suresi_Saat'].mean()
        toplam_wip_maliyet = df_finans['WIP_Maliyeti_TL'].sum()
        toplam_ceza_maliyet = df_finans['Gecikme_Cezasi_TL'].sum()
        toplam_gizli_maliyet = df_finans['Toplam_Gizli_Maliyet_TL'].sum()
        toplam_ekip_maliyeti = montaj_istasyonu * ekip_maliyeti * sim_gunu

        tab1, tab2 = st.tabs(["💰 Finansal Metrikler (Yönetim Özeti)", "⚙️ Operasyonel Metrikler (Mühendislik)"])
        
        with tab1:
            st.subheader(f"📅 {sim_gunu} Günlük Finansal Projeksiyon")
            col1, col2, col3 = st.columns(3)
            col1.metric("Toplam WIP Maliyeti", f"{toplam_wip_maliyet:,.0f} TL")
            col2.metric("Toplam Gecikme Cezası", f"{toplam_ceza_maliyet:,.0f} TL", delta_color="inverse")
            col3.metric("🔴 TOPLAM GİZLİ MALİYET", f"{toplam_gizli_maliyet:,.0f} TL")
            
            st.info(f"💡 **Yatırım Analizi:** Şu anki kapasiteyle montaj ekiplerinin toplam sabit maliyeti **{toplam_ekip_maliyeti:,.0f} TL**. Sistemin darboğazından doğan gecikme ve bekleme (gizli) maliyeti ise **{toplam_gizli_maliyet:,.0f} TL**. Montaj ekibini 1 kişi artırıp simülasyonu tekrar çalıştırarak aradaki farkı (ROI) görebilirsiniz.")

            # Maliyet Dağılımı Grafiği
            fig_pie = px.pie(values=[toplam_wip_maliyet, toplam_ceza_maliyet], 
                             names=['WIP (Bekleme) Maliyeti', 'Gecikme Cezası Maliyeti'],
                             title="Darboğaz Kaynaklı Maliyetlerin Dağılımı",
                             color_discrete_sequence=['#f39c12', '#e74c3c'])
            st.plotly_chart(fig_pie, use_container_width=True)

        with tab2:
            col1, col2 = st.columns(2)
            col1.metric("📦 Tamamlanan Sipariş", toplam_uretim)
            col2.metric("⏱️ Ortalama Teslim Süresi", f"{ort_lead_time:.1f} Saat")
            
            fig_hist = px.histogram(df_zaman, x="Teslim_Suresi_Saat", 
                                    title="Siparişlerin Teslim Süresi Dağılımı (Kuyruk Analizi)",
                                    color_discrete_sequence=['#3498db'])
            
            # Hedef süreyi grafikte çizgi olarak göster
            fig_hist.add_vline(x=hedef_sure, line_dash="dash", line_color="red", 
                               annotation_text=f"Hedef ({hedef_sure}s)", annotation_position="top right")
            st.plotly_chart(fig_hist, use_container_width=True)

    else:
        st.warning("Hiç sipariş tamamlanamadı. Kapasiteleri kontrol edin.")