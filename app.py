import concurrent.futures
from datetime import datetime
import json
import os
import urllib.request
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# Her 15 saniyede bir (15000 milisaniye) sayfayı otomatik olarak yeniler
st_autorefresh(interval=15000, limit=None, key="canli_fiyat_yenileme")

VERI_DOSYASI = "hisse_arsivi.json"
BILDIRIM_DOSYASI = "bildirim_durumu.json"

st.set_page_config(
    page_title="Canlı Hisse ve Bölge Takip Paneli",
    page_icon="📈",
    layout="wide",
)

components.html(
    """
    <script>
    const disableAutocomplete = () => {
        const inputs = window.parent.document.querySelectorAll('input');
        inputs.forEach(input => {
            input.setAttribute('autocomplete', 'off');
        });
    };
    setInterval(disableAutocomplete, 500);

    document.addEventListener('click', function(e) {
        const target = e.target.closest('.badge-yon-yukselis, .badge-yon-dusus');
        if (target) {
            setTimeout(() => {
                const doc = window.parent.document;
                const expandBtn = doc.querySelector('[data-testid="collapsedControl"]');
                if (expandBtn) {
                    expandBtn.click();
                    return;
                }
                const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (sidebar && sidebar.getAttribute('aria-expanded') === 'false') {
                    const altBtn = doc.querySelector('button[kind="header"], header button');
                    if (altBtn) {
                        altBtn.click();
                        return;
                    }
                }
                const toggleButtons = doc.querySelectorAll('button');
                for (let btn of toggleButtons) {
                    const svg = btn.querySelector('svg');
                    if (svg && (btn.getAttribute('aria-label')?.includes('sidebar') || btn.getAttribute('kind') === 'header' || btn.className.includes('collapsed'))) {
                        btn.click();
                        break;
                    }
                }
            }, 50);
        }
    });
    </script>
    """,
    height=0,
)

st.markdown(
    """
    <style>
    [data-testid="InputInstructions"], 
    [data-testid="stInputInstruction"] {
        display: none !important;
    }
    
    div[data-testid="stTextInput"] input,
    div[data-baseweb="input"] input,
    input[aria-label="Hisse Ara"] {
        text-align: center !important;
    }
    
    div[data-testid="stTextInput"] input::placeholder,
    div[data-baseweb="input"] input::placeholder,
    input[aria-label="Hisse Ara"]::placeholder {
        text-align: center !important;
    }

    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: 'Inter', sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }
    
    @media (max-width: 768px) {
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 6px !important;
        }
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            width: 33.333% !important;
            flex: 1 1 auto !important;
            min-width: 0 !important;
        }
    }

    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #9ca3af !important;
        font-size: 14px !important;
    }
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 28px !important;
        font-weight: 800 !important;
    }
    [data-testid="stSidebar"] .stTextInput > div > div > input {
        background-color: #161b22 !important;
        color: #ffffff !important;
        border: 1.5px solid #ff7700 !important;
        border-radius: 8px !important;
        box-shadow: 0 0 6px rgba(255, 119, 0, 0.35) !important;
        font-weight: 700 !important;
        letter-spacing: 1px !important;
    }
    
    [data-testid="stSidebar"] button,
    .main div.stButton > button {
        background-color: #161b22 !important;
        color: #ffffff !important;
        border: 1.5px solid #ff7700 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        box-shadow: 0 0 6px rgba(255, 119, 0, 0.35) !important;
        transition: background-color 0.05s ease, color 0.05s ease, border-color 0.05s ease;
        white-space: nowrap !important;
    }
    [data-testid="stSidebar"] button:hover,
    .main div.stButton > button:hover {
        background-color: #ff7700 !important;
        color: #0b0f19 !important;
        border-color: #ff7700 !important;
        box-shadow: 0 0 10px rgba(255, 119, 0, 0.8) !important;
    }

    div[data-testid="stTextInput"]:has(input[aria-label="Hisse Ara"]) {
        margin-bottom: -15px !important;
        padding-bottom: 0px !important;
    }

    .clear-btn-wrapper {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
        margin-top: 0px !important;
        margin-bottom: 12px !important;
        position: relative !important;
        z-index: 99 !important;
    }
    .clear-btn-container {
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
    }

    .badge-container {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        align-items: center;
        overflow-x: visible;
    }
    .badge {
        display: inline-block;
        padding: 3px 7px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        white-space: nowrap;
    }
    .badge-mor { background-color: rgba(192, 132, 252, 0.15); color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.3); }
    .badge-kisa { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-orta { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-test { background-color: rgba(156, 163, 175, 0.15); color: #d1d5db; border: 1px solid rgba(156, 163, 175, 0.3); }
    
    .badge-yon-yukselis { background-color: rgba(16, 185, 129, 0.15); color: #34d399 !important; border: 1px solid rgba(16, 185, 129, 0.3); cursor: pointer; text-decoration: none !important; }
    .badge-yon-dusus { background-color: rgba(239, 68, 68, 0.15); color: #f87171 !important; border: 1px solid rgba(239, 68, 68, 0.3); cursor: pointer; text-decoration: none !important; }
    .badge-yon-yukselis:hover, .badge-yon-dusus:hover { opacity: 0.8; }
    
    .delete-btn {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 2px 5px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        cursor: pointer;
        text-decoration: none !important;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        line-height: 1;
        border-bottom: none !important;
        box-shadow: none !important;
    }
    .delete-btn:hover {
        background-color: rgba(239, 68, 68, 0.3);
        color: #ffffff;
        border-bottom: none !important;
    }

    @keyframes pulse-blue {
        0% { transform: scale(0.95) translate3d(0,0,0); opacity: 1; box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.9); }
        70% { transform: scale(1.1) translate3d(0,0,0); opacity: 0.8; box-shadow: 0 0 0 10px rgba(59, 130, 246, 0); }
        100% { transform: scale(0.95) translate3d(0,0,0); opacity: 1; box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
    }
    .mavi-nokta-animasyon {
        display: inline-block;
        width: 11px;
        height: 11px;
        background-color: #3b82f6;
        border-radius: 50%;
        margin-left: 8px;
        vertical-align: middle;
        animation: pulse-blue 1s infinite ease-in-out !important;
        -webkit-animation: pulse-blue 1s infinite ease-in-out !important;
        will-change: transform, opacity;
        transform: translate3d(0,0,0);
        -webkit-transform: translate3d(0,0,0);
    }
    </style>
""",
    unsafe_allow_html=True,
)


def arsiv_yukle():
    if os.path.exists(VERI_DOSYASI):
        try:
            with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def arsiv_kaydet(arsiv):
    try:
        with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(arsiv, f, ensure_ascii=False, indent=4)
    except Exception:
        pass


def bildirim_durumu_yukle():
    if os.path.exists(BILDIRIM_DOSYASI):
        try:
            with open(BILDIRIM_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"son_okunan_kiran": 0}


def bildirim_durumu_kaydet(durum):
    try:
        with open(BILDIRIM_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(durum, f, ensure_ascii=False, indent=4)
    except Exception:
        pass


def arama_temizle(key):
    if key in st.session_state:
        st.session_state[key] = ""


@st.cache_data(ttl=15, show_spinner=False)
def fiyat_cek(hisse_kodu):
    if not hisse_kodu:
        return 0.0, 0.0
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{hisse_kodu}.IS?interval=1m"
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=1.5) as response:
            data = json.loads(response.read().decode())
            results = data.get("chart", {}).get("result")
            if not results:
                return 0.0, 0.0
            meta = results[0]["meta"]
            fiyat = meta.get("regularMarketPrice", 0.0)
            onceki = meta.get(
                "chartPreviousClose", meta.get("previousClose", fiyat)
            )
            yuzde = ((fiyat - onceki) / onceki) * 100 if onceki else 0.0
            return float(fiyat), float(yuzde)
    except Exception:
        return 0.0, 0.0


def parse_dizi_deger(val):
    if isinstance(val, list):
        items = [str(x).strip() for x in val if str(x).strip() != "" and str(x).strip() != "-"]
        return items if items else []
    elif isinstance(val, str):
        if "," in val or "|" in val:
            delim = "|" if "|" in val else ","
            items = [x.strip() for x in val.split(delim) if x.strip() != "" and x.strip() != "-"]
            return items if items else []
        else:
            v = val.strip()
            return [v] if v and v not in ["None", "-", ""] else []
    return []


def akilli_formatla(ham_deger, guncel_fiyat=0):
    if not ham_deger:
        return ""
    ham_deger = str(ham_deger).strip()
    if ham_deger == "-" or not ham_deger:
        return ham_deger
    sadece_rakam = "".join([c for c in ham_deger if c.isdigit()])
    if not sadece_rakam:
        return ham_deger
    
    if len(sadece_rakam) >= 3:
        sade_rakim = sadece_rakam[:-2]
        ondalik = sadece_rakam[-2:]
    else:
        sade_rakim = sadece_rakam
        ondalik = "00"
        
    try:
        tam_kisim_int = int(sade_rakim)
        tam_kisim_formatli = f"{tam_kisim_int:,}".replace(",", ".")
    except Exception:
        tam_kisim_formatli = sade_rakim
    return f"{tam_kisim_formatli},{ondalik}"


query_params = st.query_params

silme_hedefi = query_params.get("silinecek_hisse")
if silme_hedefi:
    GuncelArsiv = arsiv_yukle()
    if silme_hedefi in GuncelArsiv:
        del GuncelArsiv[silme_hedefi]
        arsiv_kaydet(GuncelArsiv)
    st.query_params.clear()
    st.rerun()

if "secilen_hisse" in query_params:
    st.session_state["secilen_hisse_hedef"] = query_params["secilen_hisse"]
    st.query_params.clear()

arsiv = arsiv_yukle()

st.title("📈 Canlı Hisse ve Bölge Takip Paneli")
st.markdown("---")

def form_icerigini_olustur():
    st.subheader("🎯 Hisse Ekle / Güncelle")

    input_key = "hisse_giris_input"
    if input_key not in st.session_state:
        st.session_state[input_key] = ""

    if "secilen_hisse_hedef" in st.session_state and st.session_state["secilen_hisse_hedef"]:
        hedef_hisse = st.session_state["secilen_hisse_hedef"]
        st.session_state[input_key] = hedef_hisse
        st.session_state["secilen_hisse_hedef"] = ""

    hisse_input = (
        st.text_input(
            "Hisse Kodu", key=input_key, placeholder=""
        )
        .strip()
        .upper()
    )
    existing = arsiv.get(hisse_input, {})

    def get_val_list(key):
        v = existing.get(key, ["", "", ""])
        if isinstance(v, list):
            res = [str(x) for x in v]
            while len(res) < 3:
                res.append("")
            return res[:3]
        elif isinstance(v, str):
            parts = [x.strip() for x in v.split("|") if x.strip() != ""]
            if len(parts) == 1 and "," in v:
                parts = [x.strip() for x in v.split(",") if x.strip() != ""]
            while len(parts) < 3:
                parts.append("")
            return parts[:3]
        return ["", "", ""]

    def get_single_val(key, default=""):
        v = existing.get(key, default)
        if isinstance(v, list):
            return v[0] if v else default
        return str(v) if v is not None else default

    yon_state_key = "secilen_yon"
    son_hisse_key = "son_yuklenen_hisse"

    if son_hisse_key not in st.session_state:
        st.session_state[son_hisse_key] = ""

    if hisse_input != st.session_state[son_hisse_key]:
        st.session_state[yon_state_key] = get_single_val("yon", "▲ Yükseliş")
        st.session_state[son_hisse_key] = hisse_input

    if yon_state_key not in st.session_state:
        st.session_state[yon_state_key] = "▲ Yükseliş"

    anlik_fiyat_degeri = 0.0
    if hisse_input:
        onizleme_fiyat, onizleme_yuzde = fiyat_cek(hisse_input)
        anlik_fiyat_degeri = onizleme_fiyat
        if onizleme_fiyat > 0:
            renk_bg = (
                "#10b981"
                if onizleme_yuzde > 0
                else "#ef4444"
                if onizleme_yuzde < 0
                else "#6b7280"
            )
            isaret = "+" if onizleme_yuzde > 0 else ""
            st.markdown(
                f"""
                    <div style="background-color: #1f2937; padding: 8px; border-radius: 8px; border: 1.5px solid #ff7700; text-align: center; margin-bottom: 8px; box-shadow: 0 0 6px rgba(255, 119, 0, 0.35);">
                        <span style="font-size: 20px; font-weight: 800; color: #f8fafc;">{onizleme_fiyat:.2f} TL</span><br>
                        <span style="font-size: 12px; font-weight: 700; color: {renk_bg};">{isaret}%{onizleme_yuzde:.2f}</span>
                    </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning("⚠️ Fiyat yükleniyor veya kod hatalı.")

    st.markdown(
        "<p style='color:#ffffff; font-weight:bold; margin-bottom:2px;'>Öngörülen Yön</p>",
        unsafe_allow_html=True,
    )
    col_b1, col_b2 = st.columns(2)

    is_yukselis_aktif = st.session_state.get(yon_state_key, "▲ Yükseliş") == "▲ Yükseliş"

    with col_b1:
        if st.button("▲ Yükseliş", key=f"btn_yuk_{hisse_input}", use_container_width=True, type="primary" if is_yukselis_aktif else "secondary"):
            st.session_state[yon_state_key] = "▲ Yükseliş"
            st.rerun()

    with col_b2:
        if st.button("▼ Düşüş", key=f"btn_dus_{hisse_input}", use_container_width=True, type="primary" if not is_yukselis_aktif else "secondary"):
            st.session_state[yon_state_key] = "▼ Düşüş"
            st.rerun()

    mor_defaults = get_val_list("mor")
    st.markdown(
        "<p style='color: #c084fc; font-weight: bold; margin-top:6px;'>💜 Mor Alarm Seviyesi</p>",
        unsafe_allow_html=True,
    )
    m1, m2, m3 = st.columns(3)
    mor_1 = m1.text_input("M1", value=mor_defaults[0], placeholder="1", key=f"m1_{hisse_input}", label_visibility="collapsed")
    mor_2 = m2.text_input("M2", value=mor_defaults[1], placeholder="2", key=f"m2_{hisse_input}", label_visibility="collapsed")
    mor_3 = m3.text_input("M3", value=mor_defaults[2], placeholder="3", key=f"m3_{hisse_input}", label_visibility="collapsed")

    turuncu_defaults = get_val_list("turuncu")
    st.markdown(
        "<p style='color: #fbbf24; font-weight: bold; margin-top:6px;'>💛 Sarı / Kısa Vade</p>",
        unsafe_allow_html=True,
    )
    s1, s2, s3 = st.columns(3)
    sari_1 = s1.text_input("S1", value=turuncu_defaults[0], placeholder="1", key=f"s1_{hisse_input}", label_visibility="collapsed")
    sari_2 = s2.text_input("S2", value=turuncu_defaults[1], placeholder="2", key=f"s2_{hisse_input}", label_visibility="collapsed")
    sari_3 = s3.text_input("S3", value=turuncu_defaults[2], placeholder="3", key=f"s3_{hisse_input}", label_visibility="collapsed")

    mavi_defaults = get_val_list("mavi")
    st.markdown(
        "<p style='color: #60a5fa; font-weight: bold; margin-top:6px;'>💙 Mavi / Orta Bölge</p>",
        unsafe_allow_html=True,
    )
    mv1, mv2, mv3 = st.columns(3)
    mavi_1 = mv1.text_input("MV1", value=mavi_defaults[0], placeholder="1", key=f"mv1_{hisse_input}", label_visibility="collapsed")
    mavi_2 = mv2.text_input("MV2", value=mavi_defaults[1], placeholder="2", key=f"mv12_{hisse_input}", label_visibility="collapsed")
    mavi_3 = mv3.text_input("MV3", value=mavi_defaults[2], placeholder="3", key=f"mv3_{hisse_input}", label_visibility="collapsed")

    gri_defaults = get_val_list("gri")
    st.markdown(
        "<p style='color: #d1d5db; font-weight: bold; margin-top:6px;'>🤍 Gri Test Bölgesi</p>",
        unsafe_allow_html=True,
    )
    g1, g2, g3 = st.columns(3)
    gri_1 = g1.text_input("G1", value=gri_defaults[0], placeholder="1", key=f"g1_{hisse_input}", label_visibility="collapsed")
    gri_2 = g2.text_input("G2", value=gri_defaults[1] if len(gri_defaults) > 1 else "", placeholder="2", key=f"g2_{hisse_input}", label_visibility="collapsed")
    gri_3 = g3.text_input("G3", value=gri_defaults[2] if len(gri_defaults) > 2 else "", placeholder="3", key=f"g3_{hisse_input}", label_visibility="collapsed")

    st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
    if st.button("KAYDET / GÜNCELLE", key=f"btn_kaydet_{hisse_input}", use_container_width=True):
        if hisse_input:
            current_arsiv = arsiv_yukle()
            bugun = datetime.now().strftime("%d.%m.%Y")
            current_arsiv[hisse_input] = {
                "mor": [
                    akilli_formatla(mor_1, anlik_fiyat_degeri),
                    akilli_formatla(mor_2, anlik_fiyat_degeri),
                    akilli_formatla(mor_3, anlik_fiyat_degeri),
                ],
                "turuncu": [
                    akilli_formatla(sari_1, anlik_fiyat_degeri),
                    akilli_formatla(sari_2, anlik_fiyat_degeri),
                    akilli_formatla(sari_3, anlik_fiyat_degeri),
                ],
                "mavi": [
                    akilli_formatla(mavi_1, anlik_fiyat_degeri),
                    akilli_formatla(mavi_2, anlik_fiyat_degeri),
                    akilli_formatla(mavi_3, anlik_fiyat_degeri),
                ],
                "gri": [
                    akilli_formatla(gri_1, anlik_fiyat_degeri),
                    akilli_formatla(gri_2, anlik_fiyat_degeri),
                    akilli_formatla(gri_3, anlik_fiyat_degeri),
                ],
                "yon": st.session_state.get(yon_state_key, "▲ Yükseliş"),
                "tarih": bugun,
            }
            arsiv_kaydet(current_arsiv)
            st.success(f"'{hisse_input}' kaydedildi ve güncellendi!")
            
            components.html(
                """
                <script>
                const doc = window.parent.document;
                const closeBtn = doc.querySelector('[data-testid="collapsedControl"]');
                const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (sidebar && sidebar.getAttribute('aria-expanded') === 'true') {
                    const toggleBtns = doc.querySelectorAll('button');
                    for (let btn of toggleBtns) {
                        const ariaLabel = btn.getAttribute('aria-label') || '';
                        if (ariaLabel.includes('sidebar') || ariaLabel.includes('Collapse')) {
                            btn.click();
                            break;
                        }
                    }
                }
                </script>
                """,
                height=0,
            )
            st.rerun()

with st.sidebar:
    @st.fragment
    def sidebar_render():
        form_icerigini_olustur()
    sidebar_render()

if not arsiv:
    st.info("Sol menüyü kullanarak ilk hissenizi ekleyin.")
else:
    data_rows = []
    alarmli_sayisi = 0
    kiran_sayisi = 0

    hisseler = list(arsiv.keys())
    fiyat_sonuclari = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fiyat_cek, h): h for h in hisseler}
        for future in concurrent.futures.as_completed(futures):
            h = futures[future]
            try:
                fiyat_sonuclari[h] = future.result()
            except Exception:
                fiyat_sonuclari[h] = (0.0, 0.0)

    for hisse, val in arsiv.items():
        fiyat, yuzde = fiyat_sonuclari.get(hisse, (0.0, 0.0))

        if isinstance(val, dict):
            alarm = parse_dizi_deger(val.get("mor", []))
            yon = val.get("yon", "▲ Yükseliş").replace("-Aktif", "")
            turuncu_v = parse_dizi_deger(val.get("turuncu", []))
            mavi_v = parse_dizi_deger(val.get("mavi", []))
            gri_v = parse_dizi_deger(val.get("gri", []))
            tarih_v = val.get("tarih", datetime.now().strftime("%d.%m.%Y"))
        else:
            alarm, yon, turuncu_v, mavi_v, gri_v = [], "▲ Yükseliş", [], [], []
            tarih_v = datetime.now().strftime("%d.%m.%Y")

        alarm_floats = []
        for a in alarm:
            try:
                clean_str = str(a).replace(".", "").replace(",", ".")
                f_val = float(clean_str)
                if f_val > 0:
                    alarm_floats.append(f_val)
            except Exception:
                pass

        is_alarmli = len(alarm_floats) > 0
        is_kiran = False

        if is_alarmli and fiyat > 0:
            if any(fiyat >= af for af in alarm_floats):
                is_kiran = True
                kiran_sayisi += 1
            else:
                alarmli_sayisi += 1

        data_rows.append({
            "Hisse": hisse,
            "Fiyat": (
                f"{fiyat:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            ),
            "Yuzde": f"%{yuzde:.2f}".replace(".", ","),
            "YuzdeVal": yuzde,
            "Alarm": alarm,
            "Yon": str(yon).replace("-Aktif", ""),
            "Turuncu": turuncu_v,
            "Mavi": mavi_v,
            "Gri": gri_v,
            "Tarih": str(tarih_v),
            "is_alarmli": is_alarmli,
            "is_kiran": is_kiran,
        })

    c1, c2 = st.columns(2)
    c1.metric("🚨 Alarmlı Hisseler", alarmli_sayisi)
    
    bildirim_durumu = bildirim_durumu_yukle()
    son_okunan = bildirim_durumu.get("son_okunan_kiran", 0)

    gosterilecek_mavi_isik = kiran_sayisi > son_okunan
    mavi_nokta_html = '<span class="mavi-nokta-animasyon"></span>' if gosterilecek_mavi_isik else ''

    c2.markdown(
        f"""
        <div style="font-size: 14px; color: #9ca3af; margin-bottom: 4px; font-weight: 600; display: flex; align-items: center;">
            <span>⚡ Alarmı Kıranlar</span> {mavi_nokta_html}
        </div>
        <div style="font-size: 28px; font-weight: 800; color: #ffffff;">
            {kiran_sayisi}
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Tüm Hisseler",
        "📋 Hisseler",
        "🚨 Alarmlı Hisseler",
        "⚡ Alarmı Kıranlar"
    ])

    sekmeler = [
        ("📈 Tüm Hisseler", tab1, 0),
        ("📋 Hisseler", tab2, 1),
        ("🚨 Alarmlı Hisseler", tab3, 2),
        ("⚡ Alarmı Kıranlar", tab4, 3)
    ]

    for sekme_adi, sekme_nesnesi, sekme_index in sekmeler:
        with sekme_nesnesi:
            if sekme_adi == "⚡ Alarmı Kıranlar":
                if son_okunan != kiran_sayisi:
                    bildirim_durumu["son_okunan_kiran"] = kiran_sayisi
                    bildirim_durumu_kaydet(bildirim_durumu)

            arama_key = f"arama_{sekme_adi}"
            
            arama_kriteri = (
                st.text_input("Hisse Ara", key=arama_key, placeholder="Hisse Ara...")
                .strip()
                .upper()
            )

            st.markdown('<div class="clear-btn-wrapper"><div class="clear-btn-container">', unsafe_allow_html=True)
            st.button(
                "🧹 ARAMAYI TEMİZLE",
                key=f"btn_clear_{sekme_adi}",
                use_container_width=True,
                on_click=arama_temizle,
                args=(arama_key,),
                type="secondary",
            )
            st.markdown('</div></div>', unsafe_allow_html=True)

            is_alarm_tab = sekme_adi in [
                "📈 Tüm Hisseler",
                "🚨 Alarmlı Hisseler",
                "⚡ Alarmı Kıranlar",
            ]

            def kutu_html_uret(liste, css_class):
                temiz_liste = [str(x).strip() for x in liste if str(x).strip() not in ["", "-", "None"]]
                if not temiz_liste:
                    return f'<div class="badge-container"><span class="badge {css_class}">-</span></div>'
                html = '<div class="badge-container">'
                for item in temiz_liste:
                    html += f'<span class="badge {css_class}">{item}</span>'
                html += '</div>'
                return html

            gosterilen_sayi = 0
            for d in data_rows:
                kosul_saglandi = False
                if sekme_adi == "📈 Tüm Hisseler":
                    kosul_saglandi = True
                elif sekme_adi == "📋 Hisseler" and not d["is_alarmli"]:
                    kosul_saglandi = True
                elif (
                    sekme_adi == "🚨 Alarmlı Hisseler"
                    and d["is_alarmli"]
                    and not d["is_kiran"]
                ):
                    kosul_saglandi = True
                elif (
                    sekme_adi == "⚡ Alarmı Kıranlar"
                    and d["is_alarmli"]
                    and d["is_kiran"]
                ):
                    kosul_saglandi = True

                if arama_kriteri and arama_kriteri not in d["Hisse"]:
                    kosul_saglandi = False

                if kosul_saglandi:
                    gosterilen_sayi += 1
                    
                    renk_cl = (
                        "#34d399"
                        if d["YuzdeVal"] > 0
                        else "#f87171"
                        if d["YuzdeVal"] < 0
                        else "#9ca3af"
                    )
                    isaret = "+" if d["YuzdeVal"] > 0 else ""

                    alarm_html = kutu_html_uret(d["Alarm"], "badge-mor") if is_alarm_tab else ""
                    kisa_html = kutu_html_uret(d["Turuncu"], "badge-kisa")
                    orta_html = kutu_html_uret(d["Mavi"], "badge-orta")
                    test_html = kutu_html_uret(d["Gri"], "badge-test")

                    yon_class = "badge-yon-yukselis" if "Yükseliş" in d["Yon"] else "badge-yon-dusus"
                    clean_yon = d['Yon'].replace("-Aktif", "")
                    
                    card_id = f"card_{d['Hisse']}_{sekme_index}"
                    card_border_style = "border: 1.5px solid #1f2937;"

                    alarm_bolumu_html = f'<div><span style="color: #9ca3af; font-weight:600; display:block; margin-bottom:2px;">ALARM</span>{alarm_html}</div>' if is_alarm_tab else ''

                    link_url = f"?secilen_hisse={d['Hisse']}&tab={sekme_index}"
                    sil_url = f"?silinecek_hisse={d['Hisse']}&tab={sekme_index}"
                    
                    onclick_sil = (
                        f"const card = document.getElementById('{card_id}');"
                        f"if(card) {{ card.style.transform = 'scaleY(0)'; card.style.opacity = '0'; card.style.margin = '0'; card.style.padding = '0'; "
                        f"setTimeout(() => {{ window.location.href = '{sil_url}'; }}, 100); }}"
                        f"event.preventDefault();"
                    )

                    kart_html = (
                        f'<div id="{card_id}" style="background-color: #111827; {card_border_style} padding: 12px; border-radius: 10px; margin-bottom: 15px; transition: all 0.15s ease-out; transform-origin: top center;">'
                        f'<div class="hisse-card-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid #1f2937; padding-bottom: 6px; flex-wrap: wrap; gap: 6px;">'
                        f'<div style="display: flex; align-items: center; gap: 6px; flex-wrap: nowrap; min-width: 0; overflow: hidden;">'
                        f'<span style="font-size: 15px; font-weight: 800; color: #ffffff; white-space: nowrap;">{d["Hisse"]}</span>'
                        f'<span style="font-size: 12px; font-weight: 600; color: #d1d5db; white-space: nowrap;">{d["Fiyat"]} TL</span>'
                        f'<span style="font-size: 11px; font-weight: 700; color: {renk_cl}; white-space: nowrap;">({isaret}{d["Yuzde"]})</span>'
                        f'</div>'
                        f'<div class="hisse-card-actions" style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">'
                        f'<a href="{link_url}" target="_self" class="badge {yon_class}" onclick="sessionStorage.setItem(\'hedefHisse\', \'{d["Hisse"]}\');">{clean_yon}</a>'
                        f'<span style="font-size: 11px; color: #9ca3af; white-space: nowrap;">📅 {d["Tarih"]}</span>'
                        f'<a href="{sil_url}" onclick="{onclick_sil}" class="delete-btn" title="Sil">🗑️</a>'
                        f'</div></div>'
                        f'<div class="hisse-grid-container" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 8px; font-size: 12px;">'
                        f'{alarm_bolumu_html}'
                        f'<div><span style="color: #9ca3af; font-weight:600; display:block; margin-bottom:2px;">KISA VADE</span>{kisa_html}</div>'
                        f'<div><span style="color: #9ca3af; font-weight:600; display:block; margin-bottom:2px;">ORTA / SON</span>{orta_html}</div>'
                        f'<div><span style="color: #9ca3af; font-weight:600; display:block; margin-bottom:2px;">TEST EDİLEBİR</span>{test_html}</div>'
                        f'</div></div>'
                    )

                    st.markdown(kart_html, unsafe_allow_html=True)

            if gosterilen_sayi == 0:
                st.info("Aradığınız kriterlere uygun hisse bulunamadı.")
