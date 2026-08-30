import concurrent.futures
from datetime import datetime
import json
import os
import random
import urllib.request
import streamlit as st
import streamlit.components.v1 as components

VERI_DOSYASI = "hisse_arsivi.json"

st.set_page_config(
    page_title="Canlı Hisse ve Bölge Takip Paneli",
    page_icon="📈",
    layout="wide",
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
    
    [data-testid="stSidebar"] button {
        background-color: #161b22 !important;
        color: #ffffff !important;
        border: 1.5px solid #ff7700 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        box-shadow: 0 0 6px rgba(255, 119, 0, 0.35) !important;
        transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #ff7700 !important;
        color: #0b0f19 !important;
        border-color: #ff7700 !important;
        box-shadow: 0 0 12px rgba(255, 119, 0, 0.8) !important;
    }

    /* Tablo içi hisse seçme butonlarını saf yazı gibi gösterir */
    div[data-testid="column"] button {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 15px !important;
        padding: 0 !important;
        margin: 0 !important;
        text-align: left !important;
        min-height: unset !important;
    }
    div[data-testid="column"] button:hover {
        background-color: transparent !important;
        color: #ff7700 !important;
        border: none !important;
        box-shadow: none !important;
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
        gap: 4px;
    }
    .badge {
        display: inline-block;
        padding: 3px 7px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-mor { background-color: rgba(192, 132, 252, 0.15); color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.3); }
    .badge-kisa { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-orta { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-test { background-color: rgba(156, 163, 175, 0.15); color: #d1d5db; border: 1px solid rgba(156, 163, 175, 0.3); }
    .badge-yon-yukselis { background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-yon-dusus { background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-tarih { color: #9ca3af; font-size: 11px; font-weight: 600; }
    .header-row {
        background-color: #161e2e;
        padding: 10px 14px;
        border-radius: 8px;
        color: #9ca3af;
        font-weight: 700;
        font-size: 11px;
        text-transform: uppercase;
        margin-bottom: 10px;
        border: 1px solid #1f2937;
    }
    </style>
""",
    unsafe_allow_html=True,
)

components.html(
    """
    <script>
        const fixInputsAndButtons = () => {
            const doc = window.parent.document;
            
            doc.querySelectorAll('input').forEach(input => {
                input.setAttribute('autocomplete', 'off');
                input.setAttribute('autocorrect', 'off');
                input.setAttribute('spellcheck', 'false');
            });

            doc.querySelectorAll('button').forEach(btn => {
                if (btn.innerText.includes('ARAMAYI TEMİZLE')) {
                    btn.style.backgroundColor = '#161b22';
                    btn.style.color = '#ffffff';
                    btn.style.border = '1.5px solid #ff7700';
                    btn.style.borderRadius = '8px';
                    btn.style.fontWeight = '700';
                    btn.style.fontSize = '12px';
                    btn.style.letterSpacing = '1px';
                    btn.style.boxShadow = '0 0 6px rgba(255, 119, 0, 0.35)';
                    btn.style.width = '100%';
                    btn.style.maxWidth = '280px';
                    btn.style.height = '38px';
                    btn.style.transition = 'background-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease';
                    
                    if (!btn.hasAttribute('data-hover-fixed')) {
                        btn.setAttribute('data-hover-fixed', 'true');
                        btn.onmouseover = () => {
                            btn.style.backgroundColor = '#ff7700';
                            btn.style.color = '#0b0f19';
                            btn.style.boxShadow = '0 0 12px rgba(255, 119, 0, 0.8)';
                        };
                        btn.onmouseout = () => {
                            btn.style.backgroundColor = '#161b22';
                            btn.style.color = '#ffffff';
                            btn.style.boxShadow = '0 0 6px rgba(255, 119, 0, 0.35)';
                        };
                    }
                }
            });
        };
        fixInputsAndButtons();
        setInterval(fixInputsAndButtons, 500);
    </script>
""",
    height=0,
    width=0,
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


def arama_temizle(key):
    if key in st.session_state:
        st.session_state[key] = ""


@st.cache_data(ttl=20, show_spinner=False)
def fiyat_cek(hisse_kodu):
    if not hisse_kodu:
        return 0.0, 0.0
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{hisse_kodu}.IS?interval=1m"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
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
        items = [str(x) for x in val if str(x).strip() != ""]
        return items if items else []
    elif isinstance(val, str) and ("," in val or "|" in val):
        delim = "|" if "|" in val else ","
        items = [x.strip() for x in val.split(delim) if x.strip() != ""]
        return items if items else []
    else:
        v = str(val).strip()
        return [v] if v and v not in ["None", "-"] else []


def akilli_formatla(ham_deger, guncel_fiyat=0):
    if not ham_deger:
        return ""
    ham_deger = str(ham_deger).strip()
    if ham_deger == "-" or not ham_deger:
        return ham_deger
    sadece_rakam = "".join([c for c in ham_deger if c.isdigit()])
    if not sadece_rakam:
        return ham_deger
    if len(sadece_rakam) <= 2:
        tam_kisim = "0"
        ondalik = sadece_rakam.zfill(2)
    else:
        tam_kisim = sadece_rakam[:-2]
        ondalik = sadece_rakam[-2:]
    try:
        tam_kisim_int = int(tam_kisim)
        tam_kisim_formatli = f"{tam_kisim_int:,}".replace(",", ".")
    except Exception:
        tam_kisim_formatli = tam_kisim
    return f"{tam_kisim_formatli},{ondalik}"


def on_fiyat_change(key):
    if key in st.session_state:
        val = st.session_state[key]
        if val:
            st.session_state[key] = akilli_formatla(val, 0)


arsiv = arsiv_yukle()

st.title("📈 Canlı Hisse ve Bölge Takip Paneli")
st.markdown("---")

with st.sidebar:
    st.subheader("🎯 Hisse Ekle / Güncelle")

    if "rastgele_input_id" not in st.session_state:
        st.session_state["rastgele_input_id"] = "hisse_giris_input"

    if "secilen_hisse_hedef" in st.session_state and st.session_state["secilen_hisse_hedef"]:
        st.session_state[st.session_state["rastgele_input_id"]] = st.session_state["secilen_hisse_hedef"]
        st.session_state["secilen_hisse_hedef"] = ""

    hisse_input = (
        st.text_input(
            "Hisse Kodu", key=st.session_state["rastgele_input_id"], placeholder=""
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


    if "son_yuklenen_hisse" not in st.session_state:
        st.session_state["son_yuklenen_hisse"] = ""

    if hisse_input != st.session_state["son_yuklenen_hisse"]:
        st.session_state["secilen_yon"] = get_single_val("yon", "▲ Yükseliş")
        st.session_state["son_yuklenen_hisse"] = hisse_input

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
                    <div style="background-color: #1f2937; padding: 10px; border-radius: 8px; border: 1.5px solid #ff7700; text-align: center; margin-bottom: 10px; box-shadow: 0 0 6px rgba(255, 119, 0, 0.35);">
                        <span style="font-size: 22px; font-weight: 800; color: #f8fafc;">{onizleme_fiyat:.2f} TL</span><br>
                        <span style="font-size: 13px; font-weight: 700; color: {renk_bg};">{isaret}%{onizleme_yuzde:.2f}</span>
                    </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning("⚠️ Fiyat yükleniyor veya kod hatalı.")

    st.markdown(
        "<p style='color:#ffffff; font-weight:bold; margin-bottom:5px;'>Öngörülen Yön</p>",
        unsafe_allow_html=True,
    )
    col_b1, col_b2 = st.columns(2)

    with col_b1:
        if st.button("▲ Yükseliş", use_container_width=True):
            st.session_state["secilen_yon"] = "▲ Yükseliş"

    with col_b2:
        if st.button("▼ Düşüş", use_container_width=True):
            st.session_state["secilen_yon"] = "▼ Düşüş"

    mor_defaults = get_val_list("mor")
    st.markdown(
        "<p style='color: #c084fc; font-weight: bold; margin-top:10px;'>💜 Mor Alarm Seviyesi</p>",
        unsafe_allow_html=True,
    )
    m1, m2, m3 = st.columns(3)
    mor_1 = m1.text_input(
        "M1",
        value=mor_defaults[0],
        placeholder="1",
        key=f"m1_{hisse_input}",
        label_visibility="collapsed",
        on_change=on_fiyat_change,
        args=(f"m1_{hisse_input}",),
    )
    mor_2 = m2.text_input(
        "M2",
        value=mor_defaults[1],
        placeholder="2",
        key=f"m2_{hisse_input}",
        label_visibility="collapsed",
        on_change=on_fiyat_change,
        args=(f"m2_{hisse_input}",),
    )
    mor_3 = m3.text_input(
        "M3",
        value=mor_defaults[2],
        placeholder="3",
        key=f"m3_{hisse_input}",
        label_visibility="collapsed",
        on_change=on_fiyat_change,
        args=(f"m3_{hisse_input}",),
    )

    turuncu_defaults = get_val_list("turuncu")
    st.markdown(
        "<p style='color: #fbbf24; font-weight: bold; margin-top:10px;'>💛 Sarı / Kısa Vade</p>",
        unsafe_allow_html=True,
    )
    s1, s2, s3 = st.columns(3)
    sari_1 = s1.text_input(
        "S1",
        value=turuncu_defaults[0],
        placeholder="1",
        key=f"s1_{hisse_input}",
        label_visibility="collapsed",
        on_change=on_fiyat_change,
        args=(f"s1_{hisse_input}",),
    )
    sari_2 = s2.text_input(
        "S2",
        value=turuncu_defaults[1],
        placeholder="2",
        key=f"s2_{hisse_input}",
        label_visibility="collapsed",
        on_change=on_fiyat_change,
        args=(f"s2_{hisse_input}",),
    )
    sari_3 = s3.text_input(
        "S3",
        value=turuncu_defaults[2],
        placeholder="3",
        key=f"s3_{hisse_input}",
        label_visibility="collapsed",
        on_change=on_fiyat_change,
        args=(f"s3_{hisse_input}",),
    )

    mavi_defaults = get_val_list("mavi")
    st.markdown(
        "<p style='color: #60a5fa; font-weight: bold; margin-top:10px;'>💙 Mavi / Orta Bölge</p>",
        unsafe_allow_html=True,
    )
    mv1, mv2, mv3 = st.columns(3)
    mavi_1 = mv1.text_input(
        "MV1",
        value=mavi_defaults[0],
        placeholder="1",
        key=f"mv1_{hisse_input}",
        label_visibility="collapsed",
        on_change=on_fiyat_change,
        args=(f"mv1_{hisse_input}",),
    )
    mavi_2 = mv2.text_input(
        "MV2",
        value=mavi_defaults[1],
        placeholder="2",
        key=f"mv2_{hisse_input}",
        label_visibility="collapsed",
        on_change=on_fiyat_change,
        args=(f"mv2_{hisse_input}",),
    )
    mavi_3 = mv3.text_input(
        "MV3",
        value=mavi_defaults[2],
        placeholder="3",
        key=f"mv3_{hisse_input}",
        label_visibility="collapsed",
        on_change=on_fiyat_change,
        args=(f"mv3_{hisse_input}",),
    )

    gri_defaults = get_val_list("gri")
    st.markdown(
        "<p style='color: #d1d5db; font-weight: bold; margin-top:10px;'>🤍 Gri Test Bölgesi</p>",
        unsafe_allow_html=True,
    )
    g1, g2, g3 = st.columns(3)
    gri_1 = g1.text_input(
        "G1",
        value=gri_defaults[0],
        placeholder="1",
        key=f"g1_{hisse_input}",
        label_visibility="collapsed",
        on_change=on_fiyat_change,
        args=(f"g1_{hisse_input}",),
    )
    gri_2 = g2.text_input(
        "G2",
        value=gri_defaults[1] if len(gri_defaults) > 1 else "",
        placeholder="2",
        key=f"g2_{hisse_input}",
        label_visibility="collapsed",
        on_change=on_fiyat_change,
        args=(f"g2_{hisse_input}",),
    )
    gri_3 = g3.text_input(
        "G3",
        value=gri_defaults[2] if len(gri_defaults) > 2 else "",
        placeholder="3",
        key=f"g3_{hisse_input}",
        label_visibility="collapsed",
        on_change=on_fiyat_change,
        args=(f"g3_{hisse_input}",),
    )

    if st.button("KAYDET / GÜNCELLE", use_container_width=True):
        if hisse_input:
            bugun = datetime.now().strftime("%d.%m.%Y")
            arsiv[hisse_input] = {
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
                "yon": st.session_state.get("secilen_yon", "▲ Yükseliş"),
                "tarih": bugun,
            }
            arsiv_kaydet(arsiv)
            st.success(f"'{hisse_input}' kaydedildi ve güncellendi!")
            st.rerun()

if not arsiv:
    st.info("Sol menüyü kullanarak ilk hissenizi ekleyin.")
else:
    data_rows = []
    alarmli_sayisi = 0
    kiran_sayisi = 0

    hisseler = list(arsiv.keys())
    fiyat_sonuclari = {}
    
    # Eşzamanlı (multi-threaded) istek havuzu ile hız artırıldı (max_workers=10)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
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
            yon = val.get("yon", "▲ Yükseliş")
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
                f_val = float(str(a).replace(".", "").replace(",", "."))
                if f_val > 0:
                    alarm_floats.append(f_val)
            except Exception:
                pass

        is_alarmli = len(alarm_floats) > 0
        is_kiran = False

        if is_alarmli and fiyat > 0:
            alarmli_sayisi += 1
            if any(fiyat >= af for af in alarm_floats):
                is_kiran = True
                kiran_sayisi += 1

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
            "Yon": str(yon),
            "Turuncu": turuncu_v,
            "Mavi": mavi_v,
            "Gri": gri_v,
            "Tarih": str(tarih_v),
            "is_alarmli": is_alarmli,
            "is_kiran": is_kiran,
        })

    c1, c2 = st.columns(2)
    c1.metric("🚨 Alarmlı Hisseler", alarmli_sayisi)
    c2.metric("⚡ Alarmı Kıranlar", kiran_sayisi)
    st.markdown("<br>", unsafe_allow_html=True)

    sekmeler = [
        "📈 Tüm Hisseler",
        "📋 Hisseler",
        "🚨 Alarmlı Hisseler",
        "⚡ Alarmı Kıranlar",
    ]
    secilen_tab = st.tabs(sekmeler)

    def render_tab_icerigi(secilen_sekme_adi):
        arama_key = f"arama_{secilen_sekme_adi}"
        
        arama_kriteri = (
            st.text_input("Hisse Ara", key=arama_key, placeholder="Hisse Ara...")
            .strip()
            .upper()
        )

        st.markdown('<div class="clear-btn-wrapper"><div class="clear-btn-container">', unsafe_allow_html=True)
        st.button(
            "🧹 ARAMAYI TEMİZLE",
            key=f"btn_clear_{secilen_sekme_adi}",
            use_container_width=True,
            on_click=arama_temizle,
            args=(arama_key,),
        )
        st.markdown('</div></div>', unsafe_allow_html=True)

        is_alarm_tab = secilen_sekme_adi in [
            "🚨 Alarmlı Hisseler",
            "⚡ Alarmı Kıranlar",
            "📈 Tüm Hisseler",
        ]

        if is_alarm_tab:
            st.markdown(
                """
                    <div class="header-row">
                        <div style="display: grid; grid-template-columns: 1.4fr 1.2fr 1.3fr 1.3fr 1.3fr 0.9fr 0.9fr 0.5fr; align-items: center; text-align: left;">
                            <div>HİSSE / FİYAT</div>
                            <div>ALARM</div>
                            <div>KISA VADE</div>
                            <div>ORTA / SON</div>
                            <div>TEST EDİLEBİR</div>
                            <div>DURUM</div>
                            <div>TARİH</div>
                            <div style="text-align: right;">İŞLEM</div>
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                    <div class="header-row">
                        <div style="display: grid; grid-template-columns: 1.5fr 1.5fr 1.5fr 1.5fr 1fr 1fr 0.6fr; align-items: center; text-align: left;">
                            <div>HİSSE / FİYAT</div>
                            <div>KISA VADE</div>
                            <div>ORTA / SON</div>
                            <div>TEST EDİLEBİR</div>
                            <div>DURUM</div>
                            <div>TARİH</div>
                            <div style="text-align: right;">İŞLEM</div>
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )

        def kutu_html_uret(liste, css_class):
            if not liste:
                return '<span class="badge badge-test">-</span>'
            html = '<div class="badge-container">'
            for item in liste:
                html += f'<span class="badge {css_class}">{item}</span>'
            html += "</div>"
            return html

        gosterilen_sayi = 0
        for d in data_rows:
            kosul_saglandi = False
            if secilen_sekme_adi == "📈 Tüm Hisseler":
                kosul_saglandi = True
            elif secilen_sekme_adi == "📋 Hisseler" and not d["is_alarmli"]:
                kosul_saglandi = True
            elif (
                secilen_sekme_adi == "🚨 Alarmlı Hisseler"
                and d["is_alarmli"]
                and not d["is_kiran"]
            ):
                kosul_saglandi = True
            elif (
                secilen_sekme_adi == "⚡ Alarmı Kıranlar"
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
                yon_class = (
                    "badge-yon-yukselis"
                    if "Yükseliş" in d["Yon"] or "Yukarı" in d["Yon"]
                    else "badge-yon-dusus"
                )

                if is_alarm_tab:
                    col1, col_alarm, col2, col3, col4, col5, col6, col7 = st.columns(
                        [1.4, 1.2, 1.3, 1.3, 1.3, 0.9, 0.9, 0.5]
                    )
                else:
                    col1, col2, col3, col4, col5, col6, col7 = st.columns(
                        [1.5, 1.5, 1.5, 1.5, 1, 1, 0.6]
                    )

                with col1:
                    if st.button(f"{d['Hisse']}", key=f"sec_{secilen_sekme_adi}_{d['Hisse']}"):
                        st.session_state["secilen_hisse_hedef"] = d["Hisse"]
                        st.rerun()
                    st.markdown(
                        f"""
                                <div style="line-height: 1.2; margin-top: -8px;">
                                    <span style="font-size: 13px; font-weight: 600; color: #d1d5db;">{d['Fiyat']} TL</span> 
                                    <span style="font-size: 12px; font-weight: 700; color: {renk_cl};">({isaret}{d['Yuzde']})</span>
                                </div>
                            """,
                        unsafe_allow_html=True,
                    )

                if is_alarm_tab:
                    with col_alarm:
                        st.markdown(
                            kutu_html_uret(d["Alarm"], "badge-mor"), unsafe_allow_html=True
                        )

                with col2:
                    st.markdown(
                        kutu_html_uret(d["Turuncu"], "badge-kisa"), unsafe_allow_html=True
                    )
                with col3:
                    st.markdown(
                        kutu_html_uret(d["Mavi"], "badge-orta"), unsafe_allow_html=True
                    )
                with col4:
                    st.markdown(
                        kutu_html_uret(d["Gri"], "badge-test"), unsafe_allow_html=True
                    )
                with col5:
                    st.markdown(
                        f'<span class="badge {yon_class}">{d["Yon"]}</span>',
                        unsafe_allow_html=True,
                    )
                with col6:
                    st.markdown(
                        f'<span class="badge-tarih">📅 {d["Tarih"]}</span>',
                        unsafe_allow_html=True,
                    )
                with col7:
                    if st.button("🗑️", key=f"del_{secilen_sekme_adi}_{d['Hisse']}"):
                        del arsiv[d["Hisse"]]
                        arsiv_kaydet(arsiv)
                        st.rerun()

                st.markdown(
                    "<hr style='margin: 8px 0; border-color: #1f2937;'>",
                    unsafe_allow_html=True,
                )

        if gosterilen_sayi == 0:
            st.info("Aradığınız kriterlere uygun hisse bulunamadı.")

    for idx, tab_adi in enumerate(sekmeler):
        with secilen_tab[idx]:
            render_tab_icerigi(tab_adi)