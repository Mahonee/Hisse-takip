import concurrent.futures
from datetime import datetime
import html
import json
import os
import urllib.parse
import urllib.request
import streamlit as st
import streamlit.components.v1 as components

VERI_DOSYASI = "hisse_arsivi.json"
BILDIRIM_DOSYASI = "bildirim_durumu.json"

st.set_page_config(
    page_title="Canlı Hisse and Bölge Takip Paneli",
    page_icon="📈",
    layout="wide",
)

components.html(
    """
    <script>
    const meta = document.createElement('meta');
    meta.name = 'viewport';
    meta.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
    window.parent.document.head.appendChild(meta);
    
    window.parent.document.addEventListener('touchstart', function(event) {
        if (event.touches.length > 1) {
            event.preventDefault();
        }
    }, { passive: false });

    let lastTouchEnd = 0;
    window.parent.document.addEventListener('touchend', function(event) {
        const now = (new Date()).getTime();
        if (now - lastTouchEnd <= 300) {
            event.preventDefault();
        }
        lastTouchEnd = now;
    }, { passive: false });
    </script>
    """,
    height=0,
)

components.html(
    """
    <script>
    const disableAutocomplete = () => {
        const inputs = window.parent.document.querySelectorAll('input');
        inputs.forEach(input => {
            input.setAttribute('autocomplete', 'off');
            input.setAttribute('autocorrect', 'off');
            input.setAttribute('autocapitalize', 'off');
            input.setAttribute('spellcheck', 'false');
            input.setAttribute('data-form-type', 'other');
            input.addEventListener('focus', function() {
                this.setAttribute('autocomplete', 'off');
            });
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
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --zemin: #0c0d10;
        --yuzey: #15171b;
        --yuzey-alt: #1a1c21;
        --cizgi: #26282e;
        --cizgi-belirgin: #34363d;
        --metin: #e9e6df;
        --metin-soluk: #8a8d94;
        --altin: #ff7a1a;
        --altin-parlak: #ff9a4d;
        --neon-golge: 0 0 6px rgba(255, 122, 26, 0.45);
        --neon-golge-hover: 0 0 14px rgba(255, 122, 26, 0.85);
        --yesil: #2ecc71;
        --kirmizi: #e74c3c;
        --mor: #9b59b6;
        --sari: #f1c40f;
        --mavi: #3498db;
        --gri: #95a5a6;
    }

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }
    header {
        visibility: visible !important;
        background: transparent !important;
    }

    .baslik-kapsayici {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 10px;
        flex-wrap: wrap;
        padding-bottom: 14px;
        border-bottom: 1px solid var(--cizgi);
        margin-bottom: 4px;
    }
    .baslik-kapsayici h1 {
        font-family: 'Fraunces', serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.2px;
    }

    [data-testid="InputInstructions"], 
    [data-testid="stInputInstruction"] {
        display: none !important;
    }
    
    div[data-testid="stSidebar"] div[data-testid="stTextInput"] input,
    div[data-testid="stSidebar"] div[data-baseweb="input"] input {
        text-align: center !important;
    }
    
    div[data-testid="stSidebar"] div[data-testid="stTextInput"] input::placeholder,
    div[data-testid="stSidebar"] div[data-baseweb="input"] input::placeholder {
        text-align: center !important;
        color: var(--metin-soluk) !important;
    }
    
    div[data-testid="stTextInput"] input,
    div[data-baseweb="input"] input,
    input[aria-label="Hisse Ara"] {
        text-align: left !important;
    }
    
    div[data-testid="stTextInput"] input::placeholder,
    div[data-baseweb="input"] input::placeholder,
    input[aria-label="Hisse Ara"]::placeholder {
        text-align: left !important;
        color: var(--metin-soluk) !important;
    }

    @media (max-width: 768px) {
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
        
        [data-testid="stSidebar"] {
            width: 240px !important;
            height: 100dvh !important;
            max-height: 85dvh !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            overflow-y: auto !important;
            -webkit-overflow-scrolling: touch !important;
        }
        section[data-testid="stSidebar"][aria-expanded="true"] {
            min-width: 240px !important;
            max-width: 240px !important;
            height: 100dvh !important;
            max-height: 85dvh !important;
        }
        [data-testid="stSidebar"] > div {
            height: 100% !important;
            overflow-y: auto !important;
            padding-bottom: 80px !important;
        }
    }

    [data-testid="stSidebar"] > div:first-child {
        height: 100vh;
        overflow-y: auto !important;
        padding-bottom: 120px !important;
    }

    html {
        scroll-behavior: smooth;
        touch-action: pan-x pan-y;
    }
    body {
        touch-action: pan-x pan-y;
    }
    * {
        transition: border-color 0.15s ease,
                    box-shadow 0.15s ease,
                    background-color 0.15s ease,
                    color 0.15s ease;
    }
    html, body, .stApp {
        background-color: var(--zemin) !important;
        color: var(--metin) !important;
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3, .baslik-kapsayici h1 {
        font-family: 'Fraunces', serif !important;
    }
    [data-testid="stSidebar"] {
        background-color: var(--yuzey) !important;
        border-right: 1px solid var(--cizgi);
    }
    [data-testid="stSidebar"] h3 {
        font-weight: 600 !important;
        font-size: 16px !important;
        color: var(--metin) !important;
        letter-spacing: 0.2px;
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
    [data-testid="stSidebar"] .stMarkdown {
        color: var(--metin-soluk) !important;
        font-weight: 600 !important;
        font-size: 12.5px !important;
        letter-spacing: 0.3px;
    }

    .istatistik-seridi {
        display: flex;
        align-items: stretch;
        border: 1.5px solid var(--altin);
        border-radius: 8px;
        background-color: var(--yuzey);
        overflow: hidden;
        margin-bottom: 18px;
        box-shadow: var(--neon-golge);
    }
    .istatistik-blok {
        flex: 1;
        padding: 14px 20px;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .istatistik-blok + .istatistik-blok {
        border-left: 1px solid var(--cizgi);
    }
    .istatistik-etiket {
        font-size: 12px;
        color: var(--metin-soluk);
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .istatistik-deger {
        font-family: 'Fraunces', serif;
        font-size: 26px;
        font-weight: 600;
        color: var(--metin);
        letter-spacing: 0.2px;
    }

    [data-testid="stSidebar"] .stTextInput > div > div > input {
        background-color: var(--yuzey-alt) !important;
        color: var(--metin) !important;
        border: 1.5px solid var(--altin) !important;
        border-radius: 6px !important;
        box-shadow: var(--neon-golge) !important;
        font-weight: 600 !important;
        letter-spacing: 0.4px !important;
        text-align: center !important;
    }
    [data-testid="stSidebar"] .stTextInput > div > div > input:focus {
        border-color: var(--altin-parlak) !important;
        box-shadow: var(--neon-golge-hover) !important;
    }
    
    [data-testid="stSidebar"] button,
    .main div.stButton > button {
        background-color: var(--yuzey-alt) !important;
        color: var(--metin) !important;
        border: 1.5px solid var(--altin) !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        box-shadow: var(--neon-golge) !important;
        white-space: nowrap !important;
    }
    [data-testid="stSidebar"] button:hover,
    .main div.stButton > button:hover {
        background-color: rgba(255, 122, 26, 0.12) !important;
        color: var(--altin-parlak) !important;
        border-color: var(--altin-parlak) !important;
        box-shadow: var(--neon-golge-hover) !important;
    }
    [data-testid="stSidebar"] button[kind="primary"] {
        background-color: rgba(255, 122, 26, 0.18) !important;
        color: var(--altin-parlak) !important;
        border-color: var(--altin-parlak) !important;
        box-shadow: var(--neon-golge-hover) !important;
    }

    div[data-testid="stTextInput"]:has(input[aria-label="Hisse Ara"]) input {
        border: 1.5px solid var(--altin) !important;
        border-radius: 6px !important;
        box-shadow: var(--neon-golge) !important;
        background-color: var(--yuzey-alt) !important;
        color: var(--metin) !important;
    }
    div[data-testid="stTextInput"]:has(input[aria-label="Hisse Ara"]) input:focus {
        border-color: var(--altin-parlak) !important;
        box-shadow: var(--neon-golge-hover) !important;
    }

    div.stButton > button[kind="secondary"] {
        background-color: var(--yuzey-alt) !important;
        color: var(--metin-soluk) !important;
        border: 1.5px solid var(--altin) !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        box-shadow: var(--neon-golge) !important;
        width: 100% !important;
        padding: 0px 4px !important;
        font-size: 12px !important;
        height: 38px !important;
        min-height: 38px !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        background-color: rgba(255, 122, 26, 0.12) !important;
        color: var(--altin-parlak) !important;
        border-color: var(--altin-parlak) !important;
        box-shadow: var(--neon-golge-hover) !important;
    }

    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 22px;
        border-bottom: 1px solid var(--cizgi);
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        background-color: transparent !important;
        color: var(--metin-soluk) !important;
        font-weight: 600 !important;
        font-size: 13.5px !important;
        padding: 0 2px 10px 2px !important;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        color: var(--altin-parlak) !important;
        border-bottom: 2px solid var(--altin) !important;
        box-shadow: 0 2px 6px -1px rgba(255, 122, 26, 0.6) !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background-color: transparent !important;
    }

    .hisse-karti {
        background-color: var(--yuzey);
        border: 1.5px solid var(--altin);
        border-radius: 8px;
        padding: 13px 14px;
        box-shadow: var(--neon-golge);
    }
    .hisse-karti:hover {
        border-color: var(--altin-parlak);
        box-shadow: var(--neon-golge-hover);
    }

    *:focus-visible {
        outline: 2px solid var(--altin-parlak) !important;
        outline-offset: 2px !important;
    }
    .hisse-karti-ust {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 9px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--cizgi);
        flex-wrap: wrap;
        gap: 6px;
    }
    .hisse-kimlik {
        display: flex;
        align-items: baseline;
        gap: 8px;
        flex-wrap: nowrap;
        min-width: 0;
        overflow: hidden;
    }
    .hisse-kod {
        font-family: 'Fraunces', serif;
        font-size: 16px;
        font-weight: 600;
        color: var(--metin);
        white-space: nowrap;
        letter-spacing: 0.2px;
    }
    .hisse-fiyat {
        font-size: 12.5px;
        font-weight: 500;
        color: var(--metin-soluk);
        white-space: nowrap;
    }
    .hisse-yuzde {
        font-size: 11.5px;
        font-weight: 600;
        white-space: nowrap;
    }
    .hisse-aksiyonlar {
        display: flex;
        align-items: center;
        gap: 6px;
        flex-shrink: 0;
    }
    .hisse-tarih {
        font-size: 11px;
        color: var(--metin-soluk);
        white-space: nowrap;
    }
    .hisse-grid-icerik {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 8px;
        font-size: 12px;
    }
    @media (max-width: 600px) {
        .hisse-grid-icerik {
            grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
            gap: 4px !important;
        }
        .hisse-grid-icerik span.badge {
            font-size: 9.5px !important;
            padding: 2px 4px !important;
        }
        .grup-etiket {
            font-size: 9.5px !important;
        }
    }
    .grup-etiket {
        color: var(--metin-soluk);
        font-weight: 600;
        display: block;
        margin-bottom: 3px;
        font-size: 10.5px;
        letter-spacing: 0.3px;
        white-space: nowrap;
    }

    .badge-container {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        align-items: center;
        overflow-x: visible;
    }
    .badge {
        display: inline-block;
        padding: 2.5px 6px;
        border-radius: 4px;
        font-size: 10.5px;
        font-weight: 600;
        white-space: nowrap;
    }
    .badge-mor { background-color: rgba(155, 89, 182, 0.22); color: var(--mor); border: 1.5px solid var(--mor); box-shadow: 0 0 5px rgba(155, 89, 182, 0.45); }
    .badge-kisa { background-color: rgba(241, 196, 15, 0.22); color: var(--sari); border: 1.5px solid var(--sari); box-shadow: 0 0 5px rgba(241, 196, 15, 0.45); }
    .badge-orta { background-color: rgba(52, 152, 219, 0.22); color: var(--mavi); border: 1.5px solid var(--mavi); box-shadow: 0 0 5px rgba(52, 152, 219, 0.45); }
    .badge-test { background-color: rgba(149, 165, 166, 0.22); color: var(--gri); border: 1.5px solid var(--gri); box-shadow: 0 0 5px rgba(149, 165, 166, 0.45); }
    
    .badge-yon-yukselis { background-color: rgba(46, 204, 113, 0.22); color: var(--yesil) !important; border: 1.5px solid var(--yesil); box-shadow: 0 0 6px rgba(46, 204, 113, 0.6); cursor: pointer; text-decoration: none !important; }
    .badge-yon-dusus { background-color: rgba(231, 76, 60, 0.22); color: var(--kirmizi) !important; border: 1.5px solid var(--kirmizi); box-shadow: 0 0 6px rgba(231, 76, 60, 0.6); cursor: pointer; text-decoration: none !important; }
    .badge-yon-yukselis:hover, .badge-yon-dusus:hover { opacity: 0.9; }
    
    .delete-btn {
        background-color: transparent;
        color: var(--metin-soluk);
        border: 1.5px solid var(--altin);
        padding: 3px 7px;
        border-radius: 4px;
        font-size: 11px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        line-height: 1;
        box-shadow: var(--neon-golge);
        text-decoration: none !important;
    }
    .delete-btn:hover {
        background-color: rgba(231, 76, 60, 0.2);
        color: var(--kirmizi);
        border-color: var(--kirmizi);
        box-shadow: 0 0 12px rgba(231, 76, 60, 0.8);
    }

    @keyframes pulse-altin {
        0% { transform: scale(0.95); opacity: 1; box-shadow: 0 0 0 0 rgba(255, 122, 26, 0.7); }
        70% { transform: scale(1.1); opacity: 0.8; box-shadow: 0 0 0 8px rgba(255, 122, 26, 0); }
        100% { transform: scale(0.95); opacity: 1; box-shadow: 0 0 0 0 rgba(255, 122, 26, 0); }
    }
    .mavi-nokta-animasyon {
        display: inline-block;
        width: 8px;
        height: 8px;
        background-color: var(--altin-parlak);
        border-radius: 50%;
        margin-left: 6px;
        vertical-align: middle;
        animation: pulse-altin 1.4s infinite ease-in-out !important;
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
    return {"temizlendi": False, "son_temizlenen_kiranlar": []}


def bildirim_durumu_kaydet(durum):
    try:
        with open(BILDIRIM_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(durum, f, ensure_ascii=False, indent=4)
    except Exception:
        pass


@st.cache_data(ttl=60, show_spinner=False)
def fiyat_cek(hisse_kodu):
    if not hisse_kodu:
        return None, None
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
                return None, None
            meta = results[0]["meta"]
            fiyat = meta.get("regularMarketPrice")
            if fiyat is None:
                return None, None
            onceki = meta.get(
                "chartPreviousClose", meta.get("previousClose", fiyat)
            )
            yuzde = ((fiyat - onceki) / onceki) * 100 if onceki else 0.0
            return float(fiyat), float(yuzde)
    except Exception:
        return None, None


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

anlik_fiyatlar_cache = {}
if arsiv:
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fiyat_cek, h): h for h in arsiv.keys()}
        for future in concurrent.futures.as_completed(futures):
            h = futures[future]
            try:
                f, y = future.result()
                anlik_fiyatlar_cache[h] = (f, y)
            except Exception:
                anlik_fiyatlar_cache[h] = (None, None)

tum_hisseler_metin = ""
if arsiv:
    tmp_list = []
    for h_kodu, h_val in arsiv.items():
        h_yon = h_val.get("yon", "-").replace("-Aktif", "")
        h_tarih = h_val.get("tarih", "-")
        h_mor = ", ".join([str(x) for x in h_val.get("mor", []) if str(x).strip() and str(x).strip() != "-"])
        h_turuncu = ", ".join([str(x) for x in h_val.get("turuncu", []) if str(x).strip() and str(x).strip() != "-"])
        h_mavi = ", ".join([str(x) for x in h_val.get("mavi", []) if str(x).strip() and str(x).strip() != "-"])
        h_gri = ", ".join([str(x) for x in h_val.get("gri", []) if str(x).strip() and str(x).strip() != "-"])
        
        fiyat_val, yuzde_val = anlik_fiyatlar_cache.get(h_kodu, (None, None))
        if fiyat_val is not None:
            fiyat_str = f"{fiyat_val:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")
            yuzde_isaret = "+" if yuzde_val > 0 else ""
            yuzde_str = f"({yuzde_isaret}%{yuzde_val:.2f})".replace(".", ",")
            h_guncel_fiyat_bilgi = f"Fiyat: {fiyat_str} {yuzde_str}"
        else:
            h_guncel_fiyat_bilgi = "Fiyat: Veri Yok"

        satir = f"Hisse: {h_kodu} | {h_guncel_fiyat_bilgi} | Yön: {h_yon} | Tarih: {h_tarih}\nAlarm: [{h_mor}] | Kısa: [{h_turuncu}] | Orta: [{h_mavi}] | Test: [{h_gri}]\n"
        tmp_list.append(satir)
    tum_hisseler_metin = "\n".join(tmp_list)

st.markdown(
    """
    <div class="baslik-kapsayici">
        <div>
            <h1 style="margin: 0; padding: 0; font-size: 1.7rem;">Canlı Hisse ve Bölge Takip Paneli</h1>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

safe_js_metin = json.dumps(tum_hisseler_metin, ensure_ascii=False)

kopyala_js_kodu = f"""
<script>
function metniKopyala() {{
    const metin = {safe_js_metin};
    navigator.clipboard.writeText(metin).then(() => {{
        let btn = document.getElementById('copyBtn');
        btn.innerText = 'Kopyalandı';
        setTimeout(() => {{ btn.innerText = 'Hisse Verilerini Kopyala'; }}, 1800);
    }}).catch(err => {{
        alert('Panoya kopyalanamadı.');
    }});
}}
</script>
<button onclick="metniKopyala()" id="copyBtn" style="
    background-color: #1a1c21;
    color: #e9e6df;
    border: 1.5px solid #ff7a1a;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-family: 'Inter', sans-serif;
    font-size: 12.5px;
    cursor: pointer;
    width: 100%;
    box-shadow: 0 0 6px rgba(255, 122, 26, 0.45);
    margin-top: 4px;
    margin-bottom: 5px;
">Hisse Verilerini Kopyala</button>
"""
components.html(kopyala_js_kodu, height=50)

st.markdown("---")

def form_icerigini_olustur():
    st.subheader("Hisse Ekle / Güncelle")

    input_key = "hisse_giris_input"
    if input_key not in st.session_state:
        st.session_state[input_key] = ""

    if "secilen_hisse_hedef" in st.session_state and st.session_state["secilen_hisse_hedef"]:
        hedef_hisse = st.session_state["secilen_hisse_hedef"]
        st.session_state[input_key] = hedef_hisse
        st.session_state["secilen_hisse_hedef"] = ""

    hisse_input = (
        st.text_input(
            "Hisse Kodu", key=input_key, placeholder="", autocomplete="off"
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
        anlik_fiyat_degeri = onizleme_fiyat or 0.0
        if onizleme_fiyat is not None and onizleme_fiyat > 0:
            renk_bg = (
                "#2ecc71"
                if onizleme_yuzde > 0
                else "#e74c3c"
                if onizleme_yuzde < 0
                else "#95a5a6"
            )
            isaret = "+" if onizleme_yuzde > 0 else ""
            st.markdown(
                f"""
                    <div style="background-color: #1a1c21; padding: 10px; border-radius: 6px; border: 1.5px solid #ff7a1a; box-shadow: 0 0 6px rgba(255, 122, 26, 0.45); text-align: center; margin-bottom: 10px;">
                        <span style="font-family: 'Fraunces', serif; font-size: 19px; font-weight: 600; color: #e9e6df;">{onizleme_fiyat:.2f} TL</span><br>
                        <span style="font-size: 12px; font-weight: 600; color: {renk_bg};">{isaret}%{onizleme_yuzde:.2f}</span>
                    </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning("⚠️ Fiyat yükleniyor veya kod hatalı.")

    st.markdown(
        "<p style='color:#8a8d94; font-weight:600; font-size:12.5px; margin-bottom:2px;'>Öngörülen Yön</p>",
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
        "<p style='color: #9b59b6; font-weight: 600; font-size:12.5px; margin-top:8px;'>Mor Alarm Seviyesi</p>",
        unsafe_allow_html=True,
    )
    m1, m2, m3 = st.columns(3)
    mor_1 = m1.text_input("M1", value=mor_defaults[0], placeholder="1", key=f"m1_{hisse_input}", label_visibility="collapsed", autocomplete="off")
    mor_2 = m2.text_input("M2", value=mor_defaults[1], placeholder="2", key=f"m2_{hisse_input}", label_visibility="collapsed", autocomplete="off")
    mor_3 = m3.text_input("M3", value=mor_defaults[2], placeholder="3", key=f"m3_{hisse_input}", label_visibility="collapsed", autocomplete="off")

    turuncu_defaults = get_val_list("turuncu")
    st.markdown(
        "<p style='color: #f1c40f; font-weight: 600; font-size:12.5px; margin-top:8px;'>Sarı / Kısa Vade</p>",
        unsafe_allow_html=True,
    )
    s1, s2, s3 = st.columns(3)
    sari_1 = s1.text_input("S1", value=turuncu_defaults[0], placeholder="1", key=f"s1_{hisse_input}", label_visibility="collapsed", autocomplete="off")
    sari_2 = s2.text_input("S2", value=turuncu_defaults[1], placeholder="2", key=f"s2_{hisse_input}", label_visibility="collapsed", autocomplete="off")
    sari_3 = s3.text_input("S3", value=turuncu_defaults[2], placeholder="3", key=f"s3_{hisse_input}", label_visibility="collapsed", autocomplete="off")

    mavi_defaults = get_val_list("mavi")
    st.markdown(
        "<p style='color: #3498db; font-weight: 600; font-size:12.5px; margin-top:8px;'>Mavi / Orta Bölge</p>",
        unsafe_allow_html=True,
    )
    mv1, mv2, mv3 = st.columns(3)
    mavi_1 = mv1.text_input("MV1", value=mavi_defaults[0], placeholder="1", key=f"mv1_{hisse_input}", label_visibility="collapsed", autocomplete="off")
    mavi_2 = mv2.text_input("MV2", value=mavi_defaults[1], placeholder="2", key=f"mv12_{hisse_input}", label_visibility="collapsed", autocomplete="off")
    mavi_3 = mv3.text_input("MV3", value=mavi_defaults[2], placeholder="3", key=f"mv3_{hisse_input}", label_visibility="collapsed", autocomplete="off")

    gri_defaults = get_val_list("gri")
    st.markdown(
        "<p style='color: #95a5a6; font-weight: 600; font-size:12.5px; margin-top:8px;'>Gri Test Bölgesi</p>",
        unsafe_allow_html=True,
    )
    g1, g2, g3 = st.columns(3)
    gri_1 = g1.text_input("G1", value=gri_defaults[0], placeholder="1", key=f"g1_{hisse_input}", label_visibility="collapsed", autocomplete="off")
    gri_2 = g2.text_input("G2", value=gri_defaults[1] if len(gri_defaults) > 1 else "", placeholder="2", key=f"g2_{hisse_input}", label_visibility="collapsed", autocomplete="off")
    gri_3 = g3.text_input("G3", value=gri_defaults[2] if len(gri_defaults) > 2 else "", placeholder="3", key=f"g3_{hisse_input}", label_visibility="collapsed", autocomplete="off")

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
            st.rerun(scope="app")

with st.sidebar:
    @st.fragment
    def sidebar_render():
        form_icerigini_olustur()
    sidebar_render()

@st.fragment(run_every=3)
def canli_veri_ve_tablo_alani():
    guncel_arsiv = arsiv_yukle()
    
    if not guncel_arsiv:
        st.info("Sol menüyü kullanarak ilk hissenizi ekleyin.")
        return

    guncel_fiyatlar_cache = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fiyat_cek, h): h for h in guncel_arsiv.keys()}
        for future in concurrent.futures.as_completed(futures):
            h = futures[future]
            try:
                f, y = future.result()
                guncel_fiyatlar_cache[h] = (f, y)
            except Exception:
                guncel_fiyatlar_cache[h] = (None, None)

    data_rows = []
    alarmli_sayisi = 0
    kiran_sayisi = 0
    kiran_hisseler = []

    for hisse, val in guncel_arsiv.items():
        fiyat, yuzde = guncel_fiyatlar_cache.get(hisse, (None, None))
        veri_yok = fiyat is None
        fiyat = fiyat or 0.0
        yuzde = yuzde or 0.0

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

        if is_alarmli and not veri_yok and fiyat > 0:
            if any(fiyat >= af for af in alarm_floats):
                is_kiran = True
                kiran_sayisi += 1
                kiran_hisseler.append(hisse)
            else:
                alarmli_sayisi += 1
        elif is_alarmli:
            alarmli_sayisi += 1

        fiyat_metni = (
            "Veri Yok"
            if veri_yok
            else f"{fiyat:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

        data_rows.append({
            "Hisse": hisse,
            "Fiyat": fiyat_metni,
            "Yuzde": f"%{yuzde:.2f}".replace(".", ","),
            "YuzdeVal": yuzde,
            "VeriYok": veri_yok,
            "Alarm": alarm,
            "Yon": str(yon).replace("-Aktif", ""),
            "Turuncu": turuncu_v,
            "Mavi": mavi_v,
            "Gri": gri_v,
            "Tarih": str(tarih_v),
            "is_alarmli": is_alarmli,
            "is_kiran": is_kiran,
        })

    bildirim_data = bildirim_durumu_yukle()
    temizlendi_mi = bildirim_data.get("temizlendi", False)
    eski_kiranlar = set(bildirim_data.get("son_temizlenen_kiranlar", []))
    su_anki_kiranlar_set = set(kiran_hisseler)

    gosterilecek_mavi_isik = False
    if kiran_hisseler:
        if not temizlendi_mi:
            gosterilecek_mavi_isik = True
        elif su_anki_kiranlar_set != eski_kiranlar:
            gosterilecek_mavi_isik = True
            bildirim_durumu_kaydet({"temizlendi": False, "son_temizlenen_kiranlar": list(su_anki_kiranlar_set)})

    mavi_nokta_html = '<span class="mavi-nokta-animasyon"></span>' if gosterilecek_mavi_isik else ''

    st.markdown(
        f"""
        <div class="istatistik-seridi">
            <div class="istatistik-blok">
                <div class="istatistik-etiket">Toplam Hisse</div>
                <div class="istatistik-deger">{len(data_rows)}</div>
            </div>
            <div class="istatistik-blok">
                <div class="istatistik-etiket">Alarmlı Hisseler</div>
                <div class="istatistik-deger">{alarmli_sayisi}</div>
            </div>
            <div class="istatistik-blok">
                <div class="istatistik-etiket"><span>Alarmı Kıranlar</span>{mavi_nokta_html}</div>
                <div class="istatistik-deger">{kiran_sayisi}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "Tüm Hisseler",
        "Hisseler",
        "Alarmlı Hisseler",
        "Alarmı Kıranlar"
    ])

    sekmeler = [
        ("📈 Tüm Hisseler", tab1, 0),
        ("📋 Hisseler", tab2, 1),
        ("🚨 Alarmlı Hisseler", tab3, 2),
        ("⚡ Alarmı Kıranlar", tab4, 3)
    ]

    for sekme_adi, sekme_nesnesi, sekme_index in sekmeler:
        with sekme_nesnesi:
            arama_key = f"arama_{sekme_adi}"
            temizle_click_key = f"temizle_tiklandi_{sekme_index}"

            if st.session_state.get(temizle_click_key, False):
                st.session_state[arama_key] = ""
                st.session_state[temizle_click_key] = False

            arama_col, temizle_col = st.columns([5, 2])
            with arama_col:
                arama_kriteri = (
                    st.text_input(
                        "Hisse Ara", key=arama_key, placeholder="Hisse ara...",
                        label_visibility="collapsed", autocomplete="off"
                    )
                    .strip()
                    .upper()
                )
            with temizle_col:
                if st.button("Temizle", key=f"temizle_btn_{sekme_index}", use_container_width=True, type="secondary"):
                    st.session_state[temizle_click_key] = True
                    if sekme_adi == "⚡ Alarmı Kıranlar":
                        bildirim_durumu_kaydet({
                            "temizlendi": True, 
                            "son_temizlenen_kiranlar": kiran_hisseler
                        })
                    st.rerun()

            is_alarm_tab = sekme_adi in [
                "📈 Tüm Hisseler",
                "🚨 Alarmlı Hisseler",
                "⚡ Alarmı Kıranlar",
            ]

            def kutu_html_uret(liste, css_class):
                temiz_liste = [str(x).strip() for x in liste if str(x).strip() not in ["", "-", "None"]]
                if not temiz_liste:
                    return f'<div class="badge-container"><span class="badge {css_class}">-</span></div>'
                parcalar = ['<div class="badge-container">']
                for item in temiz_liste:
                    parcalar.append(f'<span class="badge {css_class}">{html.escape(item)}</span>')
                parcalar.append('</div>')
                return "".join(parcalar)

            gosterilen_sayi = 0
            kartlar_html = []
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
                        "#2ecc71"
                        if d["YuzdeVal"] > 0
                        else "#e74c3c"
                        if d["YuzdeVal"] < 0
                        else "#95a5a6"
                    )
                    isaret = "+" if d["YuzdeVal"] > 0 else ""

                    alarm_html = kutu_html_uret(d["Alarm"], "badge-mor") if is_alarm_tab else ""
                    kisa_html = kutu_html_uret(d["Turuncu"], "badge-kisa")
                    orta_html = kutu_html_uret(d["Mavi"], "badge-orta")
                    test_html = kutu_html_uret(d["Gri"], "badge-test")

                    yon_class = "badge-yon-yukselis" if "Yükseliş" in d["Yon"] else "badge-yon-dusus"
                    clean_yon = d['Yon'].replace("-Aktif", "")

                    hisse_guvenli = html.escape(d["Hisse"])
                    fiyat_guvenli = html.escape(d["Fiyat"])
                    yuzde_guvenli = html.escape(d["Yuzde"])
                    yon_guvenli = html.escape(clean_yon)
                    tarih_guvenli = html.escape(d["Tarih"])
                    hisse_url = urllib.parse.quote(d["Hisse"])

                    alarm_bolumu_html = f'<div><span class="grup-etiket">ALARM</span>{alarm_html}</div>' if is_alarm_tab else ''

                    fiyat_satiri = (
                        f'<span class="hisse-fiyat" style="font-style: italic;">Veri Yok</span>'
                        if d.get("VeriYok")
                        else (
                            f'<span class="hisse-fiyat">{fiyat_guvenli} TL</span>'
                            f'<span class="hisse-yuzde" style="color: {renk_cl};">({isaret}{yuzde_guvenli})</span>'
                        )
                    )

                    kartlar_html.append(
                        f'<div class="hisse-karti">'
                        f'<div class="hisse-karti-ust">'
                        f'<div class="hisse-kimlik">'
                        f'<span class="hisse-kod">{hisse_guvenli}</span>'
                        f'{fiyat_satiri}'
                        f'</div>'
                        f'<div class="hisse-aksiyonlar">'
                        f'<a href="?secilen_hisse={hisse_url}&tab={sekme_index}" target="_self" class="badge {yon_class}">{yon_guvenli}</a>'
                        f'<span class="hisse-tarih">{tarih_guvenli}</span>'
                        f'<a href="?silinecek_hisse={hisse_url}" target="_self" class="delete-btn" title="Sil">🗑️</a>'
                        f'</div></div>'
                        f'<div class="hisse-grid-icerik">'
                        f'{alarm_bolumu_html}'
                        f'<div><span class="grup-etiket">KISA VADE</span>{kisa_html}</div>'
                        f'<div><span class="grup-etiket">ORTA / SON</span>{orta_html}</div>'
                        f'<div><span class="grup-etiket">TEST EDİLEBİR</span>{test_html}</div>'
                        f'</div></div>'
                    )

            if kartlar_html:
                for html_parca in kartlar_html:
                    st.markdown(html_parca, unsafe_allow_html=True)
                    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            if gosterilen_sayi == 0:
                st.info("Aradığınız kriterlere uygun hisse bulunamadı.")

canli_veri_ve_tablo_alani()
