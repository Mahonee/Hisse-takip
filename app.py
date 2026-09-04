import concurrent.futures
from datetime import datetime
from github import Github
import html
import json
import os
import urllib.parse
import urllib.request
import streamlit as st
import streamlit.components.v1 as components

# Sayfa yapılandırması
st.set_page_config(
    page_title="Canlı Hisse ve Bölge Takip Paneli", page_icon="📈", layout="wide"
)

# Sabitler ve Dosya Yolları
VERI_DOSYASI = "hisseler.json"
BILDIRIM_DOSYASI = "bildirim_durumu.json"
SIFRE_KORUMASI = "1111"


# Arşiv (Hisse) Verilerini Yükleme
def arsiv_yukle():
  if os.path.exists(VERI_DOSYASI):
    try:
      with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      pass
  return {}


def arsiv_kaydet(arsiv):
    # 1. Önce yerel dosyaya kaydet
    try:
        with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(arsiv, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Yerel kayıt hatası: {e}")
        return

    # 2. GitHub API ile senkronizasyon
    try:
        token = st.secrets.get("GITHUB_TOKEN")
        repo_name = st.secrets.get("GITHUB_REPO")
        
        if not token or not repo_name:
            st.error("Secrets içinde GITHUB_TOKEN veya GITHUB_REPO bulunamadı!")
            return

        g = Github(token)
        repo = g.get_repo(repo_name)
        file_path = VERI_DOSYASI
        updated_content = json.dumps(arsiv, ensure_ascii=False, indent=4)
        branch_name = "main"

        try:
            contents = repo.get_contents(file_path, ref=branch_name)
            repo.update_file(
                path=contents.path,
                message="Otomatik hisse güncellemesi (Streamlit)",
                content=updated_content,
                sha=contents.sha,
                branch=branch_name
            )
        except Exception:
            repo.create_file(
                path=file_path,
                message="İlk hisseler.json oluşturma (Streamlit)",
                content=updated_content,
                branch=branch_name
            )
            
        st.success("GitHub'a başarıyla senkronize edildi!")
    except Exception as e:
        st.error(f"GitHub senkronizasyon hatası: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

def bildirim_durumu_yukle():
  if os.path.exists(BILDIRIM_DOSYASI):
    try:
      with open(BILDIRIM_DOSYASI, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      pass
  return {
      "temizlendi": False,
      "son_kiran_sayisi": 0,
      "son_temizlenen_kiranlar": [],
  }


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
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
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
      onceki = meta.get("chartPreviousClose", meta.get("previousClose", fiyat))
      yuzde = ((fiyat - onceki) / onceki) * 100 if onceki else 0.0
      return float(fiyat), float(yuzde)
  except Exception:
    return None, None


# Hisse listesini belleğe yükle
hisse_listesi = arsiv_yukle()
st.write(f"Yüklenen hisse sayısı: {len(hisse_listesi.keys())}")

# Mobil görünüm ve zoom engelleme ayarı
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
        const target = e.target.closest('.badge-yon-yukselis, .badge-yon-dusus, .badge-yon-beklemede');
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
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Inter:wght@400;500;600;700&display=swap');

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
        --pembe: #fd79a8;
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
        font-family: 'Cinzel', serif !important;
        font-weight: 700 !important;
        letter-spacing: 0.8px;
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
    [data-testid="stSidebar"] {
        width: 255px !important;
        height: 100dvh !important;
        max-height: 100dvh !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        overflow-y: auto !important;
        -webkit-overflow-scrolling: touch !important;
        overscroll-behavior: contain !important;
    }

    section[data-testid="stSidebar"][aria-expanded="true"] {
        width: 255px !important;
        min-width: 255px !important;
        max-width: 255px !important;
        height: 100dvh !important;
        max-height: 100dvh !important;
        overflow: hidden !important;
    }

    [data-testid="stSidebar"] > div {
        height: 100% !important;
        min-height: 100dvh !important;
        max-height: 100dvh !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        padding-bottom: 120px !important;
        -webkit-overflow-scrolling: touch !important;
        overscroll-behavior: contain !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        height: 100% !important;
        min-height: 100dvh !important;
        max-height: 100dvh !important;
        overflow-y: auto !important;
        padding-bottom: 220px !important;
        -webkit-overflow-scrolling: touch !important;
    }
}

        /* Mobilde Yıldız Derecesi butonlarını düzgün şekilde yan yana tut */
        [data-testid="stSidebar"] div[class*="st-key-yildiz_pill_kutusu_form_"] [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 4px !important;
            width: 100% !important;
            align-items: center !important;
        }

        [data-testid="stSidebar"] div[class*="st-key-yildiz_pill_kutusu_form_"] [data-testid="stColumn"] {
            flex: 0 0 auto !important;
            width: auto !important;
            min-width: 0 !important;
        }

        [data-testid="stSidebar"] div[class*="st-key-yildiz_pill_kutusu_form_"] [data-testid="stColumn"]:nth-child(1),
        [data-testid="stSidebar"] div[class*="st-key-yildiz_pill_kutusu_form_"] [data-testid="stColumn"]:nth-child(2),
        [data-testid="stSidebar"] div[class*="st-key-yildiz_pill_kutusu_form_"] [data-testid="stColumn"]:nth-child(3),
        [data-testid="stSidebar"] div[class*="st-key-yildiz_pill_kutusu_form_"] [data-testid="stColumn"]:nth-child(4) {
            width: auto !important;
            flex: 0 0 auto !important;
        }

        [data-testid="stSidebar"] div[class*="st-key-yildiz_pill_kutusu_form_"] div.stButton {
            width: auto !important;
            min-width: 0 !important;
        }

        [data-testid="stSidebar"] div[class*="st-key-yildiz_pill_kutusu_form_"] div.stButton > button {
            width: auto !important;
            min-width: 0 !important;
            white-space: nowrap !important;
            padding-left: 8px !important;
            padding-right: 8px !important;
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
        font-family: 'Cinzel', serif !important;
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
            width: 50% !important;
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
        font-family: 'Cinzel', serif;
        font-size: 24px;
        font-weight: 700;
        color: var(--metin);
        letter-spacing: 0.4px;
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

    div[data-testid="stTextInput"]:has(input[aria-label="Hisse Ara"]) input,
    div[data-testid="stTextInput"]:has(input[aria-label="Şifre"]) input {
        border: 1.5px solid var(--altin) !important;
        border-radius: 12px !important;
        box-shadow: var(--neon-golge) !important;
        background-color: var(--yuzey-alt) !important;
        color: var(--metin) !important;
    }
    div[data-testid="stTextInput"]:has(input[aria-label="Hisse Ara"]) input:focus,
    div[data-testid="stTextInput"]:has(input[aria-label="Şifre"]) input:focus {
        border-color: var(--altin-parlak) !important;
        box-shadow: var(--neon-golge-hover) !important;
    }
   
    div[data-testid="stTextInput"]:has(input[aria-label="Şifre"]) button {
        display: none !important;
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
        align-items: center;
        gap: 8px;
        flex-wrap: nowrap;
        min-width: 0;
        overflow: hidden;
    }
    .hisse-kod {
        font-family: 'Cinzel', serif;
        font-size: 16px;
        font-weight: 700;
        color: var(--metin);
        white-space: nowrap;
        letter-spacing: 0.4px;
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
   
    .hisse-grid-icerik-5 {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 8px;
        font-size: 12px;
    }
    .hisse-grid-icerik-4 {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 8px;
        font-size: 12px;
    }
    @media (max-width: 600px) {
        .hisse-grid-icerik-5 {
            grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
            gap: 4px !important;
        }
        .hisse-grid-icerik-4 {
            grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
            gap: 4px !important;
        }
        .hisse-grid-icerik-5 span.badge, .hisse-grid-icerik-4 span.badge {
            font-size: 9px !important;
            padding: 2px 3px !important;
        }
        .grup-etiket {
            font-size: 9px !important;
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
    .badge-beklenti { background-color: rgba(232, 67, 147, 0.22); color: var(--pembe); border: 1.5px solid var(--pembe); box-shadow: 0 0 5px rgba(232, 67, 147, 0.45); }
   
    .badge-yon-yukselis { background-color: rgba(46, 204, 113, 0.22); color: var(--yesil) !important; border: 1.5px solid var(--yesil); box-shadow: 0 0 6px rgba(46, 204, 113, 0.6); cursor: pointer; text-decoration: none !important; }
    .badge-yon-dusus { background-color: rgba(231, 76, 60, 0.22); color: var(--kirmizi) !important; border: 1.5px solid var(--kirmizi); box-shadow: 0 0 6px rgba(231, 76, 60, 0.6); cursor: pointer; text-decoration: none !important; }
    .badge-yon-beklemede { background-color: rgba(149, 165, 166, 0.22); color: var(--gri) !important; border: 1.5px solid var(--gri); box-shadow: 0 0 6px rgba(149, 165, 166, 0.6); cursor: pointer; text-decoration: none !important; }
    .badge-yon-yukselis:hover, .badge-yon-dusus:hover, .badge-yon-beklemede:hover { opacity: 0.9; }
   
    .favori-btn {
        background-color: transparent;
        color: var(--gri);
        border: none;
        padding: 0;
        margin-right: 2px;
        font-size: 16px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        line-height: 1;
        box-shadow: none;
        text-decoration: none !important;
    }
    .favori-btn.aktif {
        color: var(--sari);
        background-color: transparent;
        box-shadow: none;
    }
    .favori-btn:hover {
        color: var(--altin-parlak);
        background-color: transparent;
        box-shadow: none;
    }

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

    div[class*="st-key-yildiz_pill_kutusu"] {
        margin-bottom: 6px;
    }
    div[class*="st-key-yildiz_pill_kutusu"] [data-testid="stHorizontalBlock"] {
        gap: 4px !important;
        margin-bottom: 4px !important;
    }
    div[class*="st-key-yildiz_pill_kutusu"] [data-testid="stColumn"] {
        width: auto !important;
        flex: 0 0 auto !important;
        min-width: 0 !important;
    }
    div[class*="st-key-yildiz_pill_kutusu"] div.stButton {
        width: auto !important;
        display: inline-block !important;
    }
    div[class*="st-key-yildiz_pill_kutusu"] div.stButton > button {
        height: 24px !important;
        min-height: 24px !important;
        width: auto !important;
        min-width: 0 !important;
        padding: 0px 8px !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        border-radius: 4px !important;
        border: 1.5px solid var(--altin) !important;
        color: var(--altin) !important;
        background-color: var(--yuzey-alt) !important;
        box-shadow: var(--neon-golge) !important;
        letter-spacing: 0px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[class*="st-key-yildiz_pill_kutusu"] div.stButton > button p {
        white-space: nowrap !important;
        overflow: visible !important;
        margin: 0 !important;
    }
    div[class*="st-key-yildiz_pill_kutusu"] div.stButton > button:hover {
        border-color: var(--altin-parlak) !important;
        color: var(--altin-parlak) !important;
        background-color: rgba(255, 122, 26, 0.12) !important;
        box-shadow: var(--neon-golge-hover) !important;
    }
    div[class*="st-key-yildiz_pill_kutusu"] div.stButton > button[kind="primary"] {
        background-color: rgba(255, 122, 26, 0.18) !important;
        color: var(--altin-parlak) !important;
        border-color: var(--altin-parlak) !important;
        box-shadow: var(--neon-golge-hover) !important;
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

    .giris-kutu-dis {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 40px 10px;
    }
    .giris-kutu-ic {
        background: linear-gradient(145deg, #15171b, #0c0d10);
        border: 1.5px solid var(--altin);
        border-radius: 20px;
        padding: 40px 30px;
        width: 100%;
        max-width: 420px;
        box-shadow: 0 0 25px rgba(255, 122, 26, 0.35);
        text-align: center;
    }
    .giris-ikon-kapsayici {
        font-size: 48px;
        margin-bottom: 12px;
        filter: drop-shadow(0 0 10px rgba(255, 122, 26, 0.6));
    }
    .giris-baslik {
        font-family: 'Cinzel', serif;
        font-size: 22px;
        font-weight: 700;
        color: var(--metin);
        letter-spacing: 1px;
        margin-bottom: 24px;
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
    return {
        "temizlendi": False,
        "son_kiran_sayisi": 0,
        "son_temizlenen_kiranlar": []
    }


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
        items = [
            str(x).strip()
            for x in val
            if str(x).strip() != "" and str(x).strip() != "-"
        ]
        return items if items else []
    elif isinstance(val, str):
        if "," in val or "|" in val:
            delim = "|" if "|" in val else ","
            items = [
                x.strip()
                for x in val.split(delim)
                if x.strip() != "" and x.strip() != "-"
            ]
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

favori_hedefi = query_params.get("favori_hisse")
if favori_hedefi:
    GuncelArsiv = arsiv_yukle()
    if favori_hedefi in GuncelArsiv:
        su_anki_fav = GuncelArsiv[favori_hedefi].get("favori", False)
        GuncelArsiv[favori_hedefi]["favori"] = not su_anki_fav
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
        futures = {
            executor.submit(fiyat_cek, h): h
            for h in arsiv.keys()
        }
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
        h_yildiz = h_val.get("yildiz", 0)
        h_mor = ", ".join([
            str(x)
            for x in h_val.get("mor", [])
            if str(x).strip() and str(x).strip() != "-"
        ])
        h_turuncu = ", ".join([
            str(x)
            for x in h_val.get("turuncu", [])
            if str(x).strip() and str(x).strip() != "-"
        ])
        h_mavi = ", ".join([
            str(x)
            for x in h_val.get("mavi", [])
            if str(x).strip() and str(x).strip() != "-"
        ])
        h_gri = ", ".join([
            str(x)
            for x in h_val.get("gri", [])
            if str(x).strip() and str(x).strip() != "-"
        ])
        h_beklenti = ", ".join([
            str(x)
            for x in h_val.get("beklenti", [])
            if str(x).strip() and str(x).strip() != "-"
        ])

        fiyat_val, yuzde_val = anlik_fiyatlar_cache.get(
            h_kodu, (None, None)
        )

        if fiyat_val is not None:
            fiyat_str = (
                f"{fiyat_val:,.2f} TL"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
            yuzde_isaret = "+" if yuzde_val > 0 else ""
            yuzde_str = (
                f"({yuzde_isaret}%{yuzde_val:.2f})"
                .replace(".", ",")
            )
            h_guncel_fiyat_bilgi = f"Fiyat: {fiyat_str} {yuzde_str}"
        else:
            h_guncel_fiyat_bilgi = "Fiyat: Veri Yok"

        satir = (
            f"Hisse: {h_kodu} | Yıldız: {h_yildiz} | "
            f"{h_guncel_fiyat_bilgi} | Yön: {h_yon} | Tarih: {h_tarih}\n"
            f"Alarm: [{h_mor}] | Kısa: [{h_turuncu}] | "
            f"Orta/Son: [{h_mavi}] | Test: [{h_gri}] | "
            f"Beklenti: [{h_beklenti}]\n"
        )
        tmp_list.append(satir)

    tum_hisseler_metin = "\n".join(tmp_list)


st.markdown(
    """
    <div class="baslik-kapsayici">
        <div>
            <h1 style="margin: 0; padding: 0; font-size: 1.6rem;">
                Canlı Hisse ve Bölge Takip Paneli
            </h1>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

safe_js_metin = json.dumps(
    tum_hisseler_metin,
    ensure_ascii=False
)

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

    if (
        "secilen_hisse_hedef" in st.session_state
        and st.session_state["secilen_hisse_hedef"]
    ):
        hedef_hisse = st.session_state["secilen_hisse_hedef"]
        st.session_state[input_key] = hedef_hisse
        st.session_state["secilen_hisse_hedef"] = ""

    hisse_input = (
        st.text_input(
            "Hisse Kodu",
            key=input_key,
            placeholder="",
            autocomplete="off"
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
            parts = [
                x.strip()
                for x in v.split("|")
                if x.strip() != ""
            ]

            if len(parts) == 1 and "," in v:
                parts = [
                    x.strip()
                    for x in v.split(",")
                    if x.strip() != ""
                ]

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
    yildiz_state_key = "secilen_yildiz_form"
    son_hisse_key = "son_yuklenen_hisse"

    if son_hisse_key not in st.session_state:
        st.session_state[son_hisse_key] = ""

    if hisse_input != st.session_state[son_hisse_key]:
        st.session_state[yon_state_key] = get_single_val(
            "yon",
            "▲ Yükseliş"
        )
        st.session_state[yildiz_state_key] = int(
            existing.get("yildiz", 0)
        )
        st.session_state[son_hisse_key] = hisse_input

    if yon_state_key not in st.session_state:
        st.session_state[yon_state_key] = "▲ Yükseliş"

    if yildiz_state_key not in st.session_state:
        st.session_state[yildiz_state_key] = 0

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
                        <span style="font-family: 'Cinzel', serif; font-size: 19px; font-weight: 700; color: #e9e6df;">{onizleme_fiyat:.2f} TL</span><br>
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

    secili_yon = st.session_state.get(
        yon_state_key,
        "▲ Yükseliş"
    )

    with col_b1:
        if st.button(
            "▲ Yükseliş",
            key=f"btn_yuk_{hisse_input}",
            use_container_width=True,
            type="primary"
            if secili_yon == "▲ Yükseliş"
            else "secondary"
        ):
            st.session_state[yon_state_key] = "▲ Yükseliş"
            st.rerun()

    with col_b2:
        if st.button(
            "▼ Düşüş",
            key=f"btn_dus_{hisse_input}",
            use_container_width=True,
            type="primary"
            if secili_yon == "▼ Düşüş"
            else "secondary"
        ):
            st.session_state[yon_state_key] = "▼ Düşüş"
            st.rerun()

    if st.button(
        "⏳ Beklemede",
        key=f"btn_bek_{hisse_input}",
        use_container_width=True,
        type="primary"
        if secili_yon == "⏳ Beklemede"
        else "secondary"
    ):
        st.session_state[yon_state_key] = "⏳ Beklemede"
        st.rerun()

    st.markdown(
        "<p style='color:#f1c40f; font-weight:600; font-size:12.5px; margin-top:8px; margin-bottom:2px;'>Yıldız Derecesi</p>",
        unsafe_allow_html=True,
    )

    secili_yildiz = st.session_state.get(
        yildiz_state_key,
        0
    )

    with st.container(
        key=f"yildiz_pill_kutusu_form_{hisse_input}"
    ):
        y_col1, y_col2, y_col3, y_col4, y_col_bosluk = st.columns(
            [1, 1, 1, 1, 6]
        )

        with y_col1:
            if st.button(
                "★",
                key=f"form_y1_{hisse_input}",
                use_container_width=False,
                type="primary"
                if secili_yildiz == 1
                else "secondary"
            ):
                st.session_state[yildiz_state_key] = (
                    0 if secili_yildiz == 1 else 1
                )
                st.rerun()

        with y_col2:
            if st.button(
                "★★",
                key=f"form_y2_{hisse_input}",
                use_container_width=False,
                type="primary"
                if secili_yildiz == 2
                else "secondary"
            ):
                st.session_state[yildiz_state_key] = (
                    0 if secili_yildiz == 2 else 2
                )
                st.rerun()

        with y_col3:
            if st.button(
                "★★★",
                key=f"form_y3_{hisse_input}",
                use_container_width=False,
                type="primary"
                if secili_yildiz == 3
                else "secondary"
            ):
                st.session_state[yildiz_state_key] = (
                    0 if secili_yildiz == 3 else 3
                )
                st.rerun()

        with y_col4:
            if st.button(
                "★★★★",
                key=f"form_y4_{hisse_input}",
                use_container_width=False,
                type="primary"
                if secili_yildiz == 4
                else "secondary"
            ):
                st.session_state[yildiz_state_key] = (
                    0 if secili_yildiz == 4 else 4
                )
                st.rerun()

    mor_defaults = get_val_list("mor")

    st.markdown(
        "<p style='color: #9b59b6; font-weight: 600; font-size:12.5px; margin-top:8px;'>Mor Alarm Seviyesi</p>",
        unsafe_allow_html=True,
    )

    m1, m2, m3 = st.columns(3)

    mor_1 = m1.text_input(
        "M1",
        value=mor_defaults[0],
        placeholder="1",
        key=f"m1_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    mor_2 = m2.text_input(
        "M2",
        value=mor_defaults[1],
        placeholder="2",
        key=f"m2_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    mor_3 = m3.text_input(
        "M3",
        value=mor_defaults[2],
        placeholder="3",
        key=f"m3_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    turuncu_defaults = get_val_list("turuncu")

    st.markdown(
        "<p style='color: #f1c40f; font-weight: 600; font-size:12.5px; margin-top:8px;'>Sarı / Kısa Vade</p>",
        unsafe_allow_html=True,
    )

    s1, s2, s3 = st.columns(3)

    sari_1 = s1.text_input(
        "S1",
        value=turuncu_defaults[0],
        placeholder="1",
        key=f"s1_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    sari_2 = s2.text_input(
        "S2",
        value=turuncu_defaults[1],
        placeholder="2",
        key=f"s2_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    sari_3 = s3.text_input(
        "S3",
        value=turuncu_defaults[2],
        placeholder="3",
        key=f"s3_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    mavi_defaults = get_val_list("mavi")

    st.markdown(
        "<p style='color: #3498db; font-weight: 600; font-size:12.5px; margin-top:8px;'>Mavi / Orta/Son</p>",
        unsafe_allow_html=True,
    )

    mv1, mv2, mv3 = st.columns(3)

    mavi_1 = mv1.text_input(
        "MV1",
        value=mavi_defaults[0],
        placeholder="1",
        key=f"mv1_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    mavi_2 = mv2.text_input(
        "MV2",
        value=mavi_defaults[1],
        placeholder="2",
        key=f"mv12_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    mavi_3 = mv3.text_input(
        "MV3",
        value=mavi_defaults[2],
        placeholder="3",
        key=f"mv3_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )


    gri_defaults = get_val_list("gri")

    st.markdown(
        "<p style='color: #95a5a6; font-weight: 600; font-size:12.5px; margin-top:8px;'>Gri Test Bölgesi</p>",
        unsafe_allow_html=True,
    )

    g1, g2, g3 = st.columns(3)

    gri_1 = g1.text_input(
        "G1",
        value=gri_defaults[0],
        placeholder="1",
        key=f"g1_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    gri_2 = g2.text_input(
        "G2",
        value=gri_defaults[1],
        placeholder="2",
        key=f"g2_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    gri_3 = g3.text_input(
        "G3",
        value=gri_defaults[2],
        placeholder="3",
        key=f"g3_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    beklenti_defaults = get_val_list("beklenti")

    st.markdown(
        "<p style='color: #fd79a8; font-weight: 600; font-size:12.5px; margin-top:8px;'>Beklenti Bölgesi</p>",
        unsafe_allow_html=True,
    )

    bk1, bk2, bk3 = st.columns(3)

    beklenti_1 = bk1.text_input(
        "BK1",
        value=beklenti_defaults[0],
        placeholder="1",
        key=f"bk1_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    beklenti_2 = bk2.text_input(
        "BK2",
        value=beklenti_defaults[1],
        placeholder="2",
        key=f"bk2_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    beklenti_3 = bk3.text_input(
        "BK3",
        value=beklenti_defaults[2],
        placeholder="3",
        key=f"bk3_{hisse_input}",
        label_visibility="collapsed",
        autocomplete="off"
    )

    st.markdown(
        "<div style='margin-top: 8px;'></div>",
        unsafe_allow_html=True
    )

    if st.button(
        "KAYDET / GÜNCELLE",
        key=f"btn_kaydet_{hisse_input}",
        use_container_width=True
    ):
        if hisse_input:
            current_arsiv = arsiv_yukle()
            bugun = datetime.now().strftime("%d.%m.%Y")
            eski_favori = current_arsiv.get(
                hisse_input,
                {}
            ).get("favori", False)

            current_arsiv[hisse_input] = {
                "mor": [
                    akilli_formatla(
                        mor_1,
                        anlik_fiyat_degeri
                    ),
                    akilli_formatla(
                        mor_2,
                        anlik_fiyat_degeri
                    ),
                    akilli_formatla(
                        mor_3,
                        anlik_fiyat_degeri
                    ),
                ],
                "turuncu": [
                    akilli_formatla(
                        sari_1,
                        anlik_fiyat_degeri
                    ),
                    akilli_formatla(
                        sari_2,
                        anlik_fiyat_degeri
                    ),
                    akilli_formatla(
                        sari_3,
                        anlik_fiyat_degeri
                    ),
                ],
                "mavi": [
                    akilli_formatla(
                        mavi_1,
                        anlik_fiyat_degeri
                    ),
                    akilli_formatla(
                        mavi_2,
                        anlik_fiyat_degeri
                    ),
                    akilli_formatla(
                        mavi_3,
                        anlik_fiyat_degeri
                    ),
                ],
                "gri": [
                    akilli_formatla(
                        gri_1,
                        anlik_fiyat_degeri
                    ),
                    akilli_formatla(
                        gri_2,
                        anlik_fiyat_degeri
                    ),
                    akilli_formatla(
                        gri_3,
                        anlik_fiyat_degeri
                    ),
                ],
                "beklenti": [
                    akilli_formatla(
                        beklenti_1,
                        anlik_fiyat_degeri
                    ),
                    akilli_formatla(
                        beklenti_2,
                        anlik_fiyat_degeri
                    ),
                    akilli_formatla(
                        beklenti_3,
                        anlik_fiyat_degeri
                    ),
                ],
                "yon": st.session_state.get(
                    yon_state_key,
                    "▲ Yükseliş"
                ),
                "yildiz": st.session_state.get(
                    yildiz_state_key,
                    0
                ),
                "tarih": bugun,
                "favori": eski_favori,
                "tetiklenen_seviyeler": []
            }

            arsiv_kaydet(current_arsiv)

            keys_to_clear = [
                input_key,
                son_hisse_key,
                yon_state_key,
                yildiz_state_key,
                f"m1_{hisse_input}",
                f"m2_{hisse_input}",
                f"m3_{hisse_input}",
                f"s1_{hisse_input}",
                f"s2_{hisse_input}",
                f"s3_{hisse_input}",
                f"mv1_{hisse_input}",
                f"mv12_{hisse_input}",
                f"mv3_{hisse_input}",
                f"g1_{hisse_input}",
                f"g2_{hisse_input}",
                f"g3_{hisse_input}",
                f"bk1_{hisse_input}",
                f"bk2_{hisse_input}",
                f"bk3_{hisse_input}"
            ]

            for k in keys_to_clear:
                if k in st.session_state:
                    del st.session_state[k]

            st.success(f"'{hisse_input}' kaydedildi ve güncellendi!")
            
            # time.sleep komutunu st.rerun()'dan ÖNCEYE alıyoruz ki 
            # GitHub API sunucuyla iletişim kurmak için yeterli süre bulabilsin.
            import time
            time.sleep(2) 

            st.rerun()

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
        st.info(
            "Sol menüyü kullanarak ilk hissenizi ekleyin."
        )
        return

    guncel_fiyatlar_cache = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(fiyat_cek, h): h
            for h in guncel_arsiv.keys()
        }

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
    arsiv_guncellendi = False

    for hisse, val in guncel_arsiv.items():

        fiyat, yuzde = guncel_fiyatlar_cache.get(
            hisse,
            (None, None)
        )

        veri_yok = fiyat is None
        fiyat = fiyat or 0.0
        yuzde = yuzde or 0.0

        if isinstance(val, dict):
            alarm = parse_dizi_deger(
                val.get("mor", [])
            )
            yon = val.get(
                "yon",
                "▲ Yükseliş"
            ).replace("-Aktif", "")
            yildiz = int(
                val.get("yildiz", 0)
            )
            turuncu_v = parse_dizi_deger(
                val.get("turuncu", [])
            )
            mavi_v = parse_dizi_deger(
                val.get("mavi", [])
            )
            gri_v = parse_dizi_deger(
                val.get("gri", [])
            )
            beklenti_v = parse_dizi_deger(
                val.get("beklenti", [])
            )
            tarih_v = val.get(
                "tarih",
                datetime.now().strftime("%d.%m.%Y")
            )
            favori_v = val.get(
                "favori",
                False
            )
            ham_tetiklenenler = val.get(
                "tetiklenen_seviyeler",
                []
            )

        else:
            alarm = []
            yon = "▲ Yükseliş"
            yildiz = 0
            turuncu_v = []
            mavi_v = []
            gri_v = []
            beklenti_v = []
            tarih_v = datetime.now().strftime(
                "%d.%m.%Y"
            )
            favori_v = False
            ham_tetiklenenler = []

        alarm_floats = []

        for a in alarm:
            try:
                clean_str = (
                    str(a)
                    .replace(".", "")
                    .replace(",", ".")
                )
                f_val = float(clean_str)

                if f_val > 0:
                    alarm_floats.append(f_val)

            except Exception:
                pass

        tetiklenenler = []

        for t in ham_tetiklenenler:
            try:
                tetiklenenler.append(
                    float(t)
                )
            except Exception:
                pass

        is_alarmli = len(alarm_floats) > 0
        is_kiran = False
        yeni_tetiklenenler = list(
            tetiklenenler
        )
        if is_alarmli and not veri_yok and fiyat > 0:

            for af in alarm_floats:

                if fiyat >= af:
                    is_kiran = True

                    if af not in yeni_tetiklenenler:
                        yeni_tetiklenenler.append(
                            af
                        )

                else:
                    if af in yeni_tetiklenenler:
                        yeni_tetiklenenler.remove(
                            af
                        )

            if len(yeni_tetiklenenler) > 0:
                is_kiran = True

            if set(tetiklenenler) != set(
                yeni_tetiklenenler
            ):
                guncel_arsiv[hisse][
                    "tetiklenen_seviyeler"
                ] = yeni_tetiklenenler

                arsiv_guncellendi = True

            if is_kiran:
                kiran_sayisi += 1
                kiran_hisseler.append(hisse)
            else:
                alarmli_sayisi += 1

        elif is_alarmli:

            if len(tetiklenenler) > 0:
                is_kiran = True
                kiran_sayisi += 1
                kiran_hisseler.append(hisse)
            else:
                alarmli_sayisi += 1

        fiyat_metni = (
            "Veri Yok"
            if veri_yok
            else f"{fiyat:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        data_rows.append({
            "Hisse": hisse,
            "Fiyat": fiyat_metni,
            "Yuzde": f"%{yuzde:.2f}".replace(
                ".",
                ","
            ),
            "YuzdeVal": yuzde,
            "VeriYok": veri_yok,
            "Alarm": alarm,
            "Yon": str(yon).replace(
                "-Aktif",
                ""
            ),
            "Yildiz": yildiz,
            "Turuncu": turuncu_v,
            "Mavi": mavi_v,
            "Gri": gri_v,
            "Beklenti": beklenti_v,
            "Tarih": str(tarih_v),
            "is_alarmli": is_alarmli,
            "is_kiran": is_kiran,
            "favori": favori_v,
        })

    if arsiv_guncellendi:
        arsiv_kaydet(guncel_arsiv)

    bildirim_data = bildirim_durumu_yukle()

    temizlendi_mi = bildirim_data.get(
        "temizlendi",
        False
    )

    eski_kiran_sayisi = bildirim_data.get(
        "son_kiran_sayisi",
        0
    )

    gosterilecek_mavi_isik = False

    if kiran_sayisi > eski_kiran_sayisi:

        gosterilecek_mavi_isik = True

        bildirim_durumu_kaydet({
            "temizlendi": False,
            "son_kiran_sayisi": kiran_sayisi,
            "son_temizlenen_kiranlar": kiran_hisseler
        })

    elif (
        kiran_sayisi == eski_kiran_sayisi
        and not temizlendi_mi
    ):

        gosterilecek_mavi_isik = True

    else:

        bildirim_durumu_kaydet({
            "temizlendi": temizlendi_mi,
            "son_kiran_sayisi": kiran_sayisi,
            "son_temizlenen_kiranlar": kiran_hisseler
        })

    mavi_nokta_html = (
        '<span class="mavi-nokta-animasyon"></span>'
        if gosterilecek_mavi_isik
        else ''
    )

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
                <div class="istatistik-etiket">
                    <span>Alarmı Kıranlar</span>{mavi_nokta_html}
                </div>
                <div class="istatistik-deger">{kiran_sayisi}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Tüm Hisseler",
        "Hisseler",
        "Alarmlı Hisseler",
        "Alarmı Kıranlar",
        "Hisselerim"
    ])

    sekmeler = [
        ("📈 Tüm Hisseler", tab1, 0),
        ("📋 Hisseler", tab2, 1),
        ("🚨 Alarmlı Hisseler", tab3, 2),
        ("⚡ Alarmı Kıranlar", tab4, 3),
        ("⭐ Hisselerim", tab5, 4)
    ]

    for sekme_adi, sekme_nesnesi, sekme_index in sekmeler:

        with sekme_nesnesi:

            if sekme_adi == "⭐ Hisselerim":

                if "hisselerim_giris_yapildi" not in st.session_state:
                    st.session_state[
                        "hisselerim_giris_yapildi"
                    ] = False

                if not st.session_state[
                    "hisselerim_giris_yapildi"
                ]:

                    st.markdown(
                        """
                        <style>
                        div[data-testid="stForm"] {
                            background: linear-gradient(145deg, #15171b, #0c0d10) !important;
                            border: 1.5px solid #ff7a1a !important;
                            border-radius: 12px !important;
                            padding: 16px 18px !important;
                            max-width: 280px !important;
                            margin: 0 auto !important;
                            box-shadow: 0 0 12px rgba(255, 122, 26, 0.25) !important;
                        }
                        div[data-testid="stForm"] div[data-testid="stTextInput"] button {
                            display: none !important;
                        }
                        div[data-testid="stForm"] input {
                            background-color: #1a1c21 !important;
                            color: #e9e6df !important;
                            border: 1.5px solid #ff7a1a !important;
                            border-radius: 6px !important;
                            text-align: center !important;
                            font-size: 13px !important;
                            box-shadow: 0 0 6px rgba(255, 122, 26, 0.45) !important;
                        }
                        div[data-testid="stForm"] button {
                            width: 100% !important;
                            background-color: #1a1c21 !important;
                            color: #e9e6df !important;
                            border: 1.5px solid #ff7a1a !important;
                            border-radius: 6px !important;
                            font-weight: 600 !important;
                            font-size: 12px !important;
                            cursor: pointer !important;
                            box-shadow: 0 0 6px rgba(255, 122, 26, 0.45) !important;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

                    with st.form(
                        "hisselerim_sifre_formu"
                    ):

                        st.markdown(
                            """
                            <div style="text-align: center;">
                                <div style="font-size: 20px; margin-bottom: 4px; filter: drop-shadow(0 0 5px rgba(255, 122, 26, 0.6));">🔒</div>
                                <div style="font-family: 'Cinzel', serif; font-size: 13px; font-weight: 700; color: #e9e6df; letter-spacing: 0.6px; margin-bottom: 12px;">ŞİFRE GİRİŞİ</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        girilen_sifre = st.text_input(
                            "Şifre",
                            type="password",
                            placeholder="",
                            label_visibility="collapsed"
                        )

                        submitted = st.form_submit_button(
                            "GİRİŞ YAP",
                            use_container_width=True
                        )

                        if submitted:

                            if girilen_sifre == SIFRE_KORUMASI:
                                st.session_state[
                                    "hisselerim_giris_yapildi"
                                ] = True
                                st.rerun()

                            else:
                                st.error(
                                    "Hatalı şifre!"
                                )

                    continue

            arama_key = f"arama_{sekme_adi}"
            yildiz_filtre_key = (
                f"yildiz_filtre_{sekme_index}"
            )
            temizle_click_key = (
                f"temizle_tiklandi_{sekme_index}"
            )

            if yildiz_filtre_key not in st.session_state:
                st.session_state[
                    yildiz_filtre_key
                ] = 0

            if st.session_state.get(
                temizle_click_key,
                False
            ):
                st.session_state[
                    arama_key
                ] = ""

                st.session_state[
                    yildiz_filtre_key
                ] = 0

                st.session_state[
                    temizle_click_key
                ] = False

            arama_col, temizle_col = st.columns(
                [5, 2]
            )

            with arama_col:

                arama_kriteri = (
                    st.text_input(
                        "Hisse Ara",
                        key=arama_key,
                        placeholder="Hisse ara...",
                        label_visibility="collapsed",
                        autocomplete="off"
                    )
                    .strip()
                    .upper()
                )

            with temizle_col:

                if st.button(
                    "Temizle",
                    key=f"temizle_btn_{sekme_index}",
                    use_container_width=True,
                    type="secondary"
                ):

                    st.session_state[
                        temizle_click_key
                    ] = True

                    if sekme_adi == "⚡ Alarmı Kıranlar":

                        bildirim_durumu_kaydet({
                            "temizlendi": True,
                            "son_kiran_sayisi": kiran_sayisi,
                            "son_temizlenen_kiranlar": kiran_hisseler
                        })

                    st.rerun()

            if sekme_adi == "📋 Hisseler":

                secili_yildiz_filtre = st.session_state.get(
                    yildiz_filtre_key,
                    0
                )

                with st.container(
                    key=f"yildiz_pill_kutusu_{sekme_index}"
                ):

                    ya1, ya2, ya3, ya4, ya_bosluk = st.columns(
                        [1, 1, 1, 1, 6]
                    )

                    with ya1:
                        if st.button(
                            "★",
                            key=f"y1_btn_{sekme_index}",
                            use_container_width=False,
                            type="primary"
                            if secili_yildiz_filtre == 1
                            else "secondary"
                        ):
                            st.session_state[
                                yildiz_filtre_key
                            ] = (
                                0
                                if secili_yildiz_filtre == 1
                                else 1
                            )
                            st.rerun()

                    with ya2:
                        if st.button(
                            "★★",
                            key=f"y2_btn_{sekme_index}",
                            use_container_width=False,
                            type="primary"
                            if secili_yildiz_filtre == 2
                            else "secondary"
                        ):
                            st.session_state[
                                yildiz_filtre_key
                            ] = (
                                0
                                if secili_yildiz_filtre == 2
                                else 2
                            )
                            st.rerun()

                    with ya3:
                        if st.button(
                            "★★★",
                            key=f"y3_btn_{sekme_index}",
                            use_container_width=False,
                            type="primary"
                            if secili_yildiz_filtre == 3
                            else "secondary"
                        ):
                            st.session_state[
                                yildiz_filtre_key
                            ] = (
                                0
                                if secili_yildiz_filtre == 3
                                else 3
                            )
                            st.rerun()

                    with ya4:
                        if st.button(
                            "★★★★",
                            key=f"y4_btn_{sekme_index}",
                            use_container_width=False,
                            type="primary"
                            if secili_yildiz_filtre == 4
                            else "secondary"
                        ):
                            st.session_state[
                                yildiz_filtre_key
                            ] = (
                                0
                                if secili_yildiz_filtre == 4
                                else 4
                            )
                            st.rerun()

            is_alarm_tab = sekme_adi in [
                "📈 Tüm Hisseler",
                "🚨 Alarmlı Hisseler",
                "⚡ Alarmı Kıranlar",
                "⭐ Hisselerim",
            ]

            def kutu_html_uret(liste, css_class):

                temiz_liste = [
                    str(x).strip()
                    for x in liste
                    if str(x).strip()
                    not in ["", "-", "None"]
                ]

                if not temiz_liste:
                    return (
                        '<div class="badge-container">'
                        f'<span class="badge {css_class}">-</span>'
                        '</div>'
                    )

                parcalar = [
                    '<div class="badge-container">'
                ]

                for item in temiz_liste:
                    parcalar.append(
                        f'<span class="badge {css_class}">'
                        f'{html.escape(item)}'
                        '</span>'
                    )

                parcalar.append(
                    '</div>'
                )

                return "".join(parcalar)

            gosterilen_sayi = 0
            kartlar_html = []

            secili_yildiz_filtre = st.session_state.get(
                yildiz_filtre_key,
                0
            )

            for d in data_rows:

                kosul_saglandi = False

                if sekme_adi == "📈 Tüm Hisseler":
                    kosul_saglandi = True

                elif (
                    sekme_adi == "📋 Hisseler"
                    and not d["is_alarmli"]
                ):
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

                elif (
                    sekme_adi == "⭐ Hisselerim"
                    and d["favori"]
                ):
                    kosul_saglandi = True

                if (
                    arama_kriteri
                    and arama_kriteri not in d["Hisse"]
                ):
                    kosul_saglandi = False

                if (
                    sekme_adi == "📋 Hisseler"
                    and secili_yildiz_filtre > 0
                ):
                    if d["Yildiz"] != secili_yildiz_filtre:
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

                    isaret = (
                        "+"
                        if d["YuzdeVal"] > 0
                        else ""
                    )

                    alarm_html = (
                        kutu_html_uret(
                            d["Alarm"],
                            "badge-mor"
                        )
                        if is_alarm_tab
                        else ""
                    )

                    kisa_html = kutu_html_uret(
                        d["Turuncu"],
                        "badge-kisa"
                    )

                    orta_html = kutu_html_uret(
                        d["Mavi"],
                        "badge-orta"
                    )

                    test_html = kutu_html_uret(
                        d["Gri"],
                        "badge-test"
                    )

                    beklenti_html = kutu_html_uret(
                        d["Beklenti"],
                        "badge-beklenti"
                    )

                    yon_val = d["Yon"]

                    if "Düşüş" in yon_val:
                        yon_class = "badge-yon-dusus"

                    elif "Beklemede" in yon_val:
                        yon_class = "badge-yon-beklemede"

                    else:
                        yon_class = "badge-yon-yukselis"

                    clean_yon = yon_val.replace(
                        "-Aktif",
                        ""
                    )

                    hisse_guvenli = html.escape(
                        d["Hisse"]
                    )

                    fiyat_guvenli = html.escape(
                        d["Fiyat"]
                    )

                    yuzde_guvenli = html.escape(
                        d["Yuzde"]
                    )

                    yon_guvenli = html.escape(
                        clean_yon
                    )

                    tarih_guvenli = html.escape(
                        d["Tarih"]
                    )

                    hisse_url = urllib.parse.quote(
                        d["Hisse"]
                    )

                    favori_aktif_class = (
                        " aktif"
                        if d["favori"]
                        else ""
                    )

                    favori_ikon = (
                        "★"
                        if d["favori"]
                        else "☆"
                    )

                    yildiz_metin = (
                        "★" * d["Yildiz"]
                        if d["Yildiz"] > 0
                        else ""
                    )

                    yildiz_html = (
                        f'<span style="color:#f1c40f; font-size:12px;">'
                        f'{yildiz_metin}'
                        f'</span>'
                        if yildiz_metin
                        else ""
                    )

                    alarm_bolumu_html = (
                        f'<div>'
                        f'<span class="grup-etiket">ALARM</span>'
                        f'{alarm_html}'
                        f'</div>'
                        if is_alarm_tab
                        else ''
                    )

                    grid_class = (
                        "hisse-grid-icerik-5"
                        if is_alarm_tab
                        else "hisse-grid-icerik-4"
                    )

                    fiyat_satiri = (
                        f'<span class="hisse-fiyat" style="font-style: italic;">Veri Yok</span>'
                        if d.get("VeriYok")
                        else (
                            f'<span class="hisse-fiyat">'
                            f'{fiyat_guvenli} TL'
                            f'</span>'
                            f'<span class="hisse-yuzde" '
                            f'style="color: {renk_cl};">'
                            f'({isaret}{yuzde_guvenli})'
                            f'</span>'
                        )
                    )

                    kartlar_html.append(
                        f'<div class="hisse-karti">'
                        f'<div class="hisse-karti-ust">'
                        f'<div class="hisse-kimlik">'
                        f'<a href="?favori_hisse={hisse_url}" '
                        f'target="_self" '
                        f'class="favori-btn{favori_aktif_class}" '
                        f'title="Favori">{favori_ikon}</a>'
                        f'<span class="hisse-kod">'
                        f'{hisse_guvenli}'
                        f'</span>'
                        f'{fiyat_satiri}'
                        f'</div>'
                        f'<div class="hisse-aksiyonlar">'
                        f'{yildiz_html}'
                        f'<a href="?secilen_hisse={hisse_url}&tab={sekme_index}" '
                        f'target="_self" '
                        f'class="badge {yon_class}">'
                        f'{yon_guvenli}'
                        f'</a>'
                        f'<span class="hisse-tarih">'
                        f'{tarih_guvenli}'
                        f'</span>'
                        f'<a href="?silinecek_hisse={hisse_url}" '
                        f'target="_self" '
                        f'class="delete-btn" '
                        f'title="Sil">🗑️</a>'
                        f'</div>'
                        f'</div>'
                        f'<div class="{grid_class}">'
                        f'{alarm_bolumu_html}'
                        f'<div>'
                        f'<span class="grup-etiket">KISA VADE</span>'
                        f'{kisa_html}'
                        f'</div>'
                        f'<div>'
                        f'<span class="grup-etiket">ORTA/SON</span>'
                        f'{orta_html}'
                        f'</div>'
                        f'<div>'
                        f'<span class="grup-etiket">TEST EDİLEBİR</span>'
                        f'{test_html}'
                        f'</div>'
                        f'<div>'
                        f'<span class="grup-etiket">BEKLENTİ BÖLGESİ</span>'
                        f'{beklenti_html}'
                        f'</div>'
                        f'</div>'
                        f'</div>'
                    )

            if kartlar_html:

                for html_parca in kartlar_html:

                    st.markdown(
                        html_parca,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "<div style='height: 12px;'></div>",
                        unsafe_allow_html=True
                    )

            if gosterilen_sayi == 0:
                st.info(
                    "Aradığınız kriterlere uygun hisse bulunamadı."
                )


canli_veri_ve_tablo_alani()
