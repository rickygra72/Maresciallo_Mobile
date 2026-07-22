import streamlit as st
import os
import re
import base64
import json
import datetime
import urllib.request
from google import genai
from google.genai import types

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import pypdf
except ImportError:
    pypdf = None

# ==========================================
# CONFIGURAZIONE PAGINA STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Maresciallo AI - Mobile Terminal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

PASSWORD_APPLICATIVO = "GdiF_117"
DEFAULT_COST_INPUT_1M_EUR = 0.069   # ~$0.075 USD
DEFAULT_COST_OUTPUT_1M_EUR = 0.276  # ~$0.300 USD


# ==========================================
# GESTIONE SESSION STATE (MEMORIA MOBILE)
# ==========================================
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if "storico_chat" not in st.session_state:
    st.session_state.storico_chat = []

if "sess_token_in" not in st.session_state:
    st.session_state.sess_token_in = 0

if "sess_token_out" not in st.session_state:
    st.session_state.sess_token_out = 0

if "sess_costo_eur" not in st.session_state:
    st.session_state.sess_costo_eur = 0.0

if "costo_input_1m_eur" not in st.session_state:
    st.session_state.costo_input_1m_eur = DEFAULT_COST_INPUT_1M_EUR

if "costo_output_1m_eur" not in st.session_state:
    st.session_state.costo_output_1m_eur = DEFAULT_COST_OUTPUT_1M_EUR


# ==========================================
# UTILITY FUNZIONALI
# ==========================================
def registra_consumo_token(token_in, token_out):
    costo_in = (token_in / 1_000_000.0) * st.session_state.costo_input_1m_eur
    costo_out = (token_out / 1_000_000.0) * st.session_state.costo_output_1m_eur
    costo_tot = costo_in + costo_out

    st.session_state.sess_token_in += token_in
    st.session_state.sess_token_out += token_out
    st.session_state.sess_costo_eur += costo_tot
    return costo_tot

def correggi_ortografia_italiana(testo):
    correzioni = [
        (r"\bDallesame\b", "Dall'esame"),
        (r"\bdImposta\b", "d'imposta"),
        (r"\bdimposta\b", "d'imposta"),
        (r"\bdimpresa\b", "d'impresa"),
        (r"\bdAffari\b", "d'affari"),
        (r"\bdaffari\b", "d'affari"),
        (r"\bSOSTITUTO DIMPOSTA\b", "SOSTITUTO D'IMPOSTA"),
        (r"\bLanalisi\b", "L'analisi"),
        (r"\bdallesame\b", "dall'esame"),
        (r"\blesercizio\b", "l'esercizio"),
        (r"\bLesercizio\b", "L'esercizio")
    ]
    for pattern, sostituto in correzioni:
        testo = re.sub(pattern, sostituto, testo, flags=re.IGNORECASE)
    return testo

def pulisci_testo_preventivo(testo):
    righe = [r.strip() for r in testo.split('\n') if r.strip()]
    return "\n".join(righe)

def leggi_file_caricati(uploaded_files):
    testo = ""
    immagini = []
    tot_pagine = 0

    if not uploaded_files:
        return testo, immagini, tot_pagine

    for f in uploaded_files:
        nome_file = f.name
        est = nome_file.split('.')[-1].lower()

        if est in ["jpg", "jpeg", "png"]:
            bytes_data = f.read()
            mime = "image/jpeg" if est in ["jpg", "jpeg"] else "image/png"
            immagini.append(types.Part.from_bytes(data=bytes_data, mime_type=mime))
            continue

        testo += f"\n[ESTRATTO FILE FISCALE: {nome_file}]\n"
        try:
            if est == "txt":
                testo += f.read().decode("utf-8", errors="ignore")
            elif est == "pdf" and pypdf:
                reader = pypdf.PdfReader(f)
                tot_pagine += len(reader.pages)
                for num_p, page in enumerate(reader.pages, start=1):
                    t = page.extract_text()
                    if t:
                        testo += f"--- Pagina {num_p} di {len(reader.pages)} ---\n" + t + "\n"
                    else:
                        testo += f"⚠️ [Pagina {num_p} del file {nome_file} risulta priva di testo selezionabile]\n"
            elif est == "xlsx" and openpyxl:
                ws = openpyxl.load_workbook(f, data_only=True).active
                for row in ws.iter_rows(values_only=True):
                    if any(row):
                        testo += " | ".join([str(c) if c is not None else "" for c in row]) + "\n"
        except Exception as e:
            testo += f"[Errore di lettura locale su {nome_file}: {str(e)}]\n"

    return pulisci_testo_preventivo(testo), immagini, tot_pagine


# ==========================================
# 1. SCHERMATA DI LOGIN MOBILE
# ==========================================
if not st.session_state.autenticato:
    st.title("🔒 ACCESSO RISERVATO")
    st.subheader("Unità Analisi Economico-Finanziaria - Terminale Mobile")
    
    pwd = st.text_input("Password di Sicurezza Operativa:", type="password")
    if st.button("🔓 SBLOCCA TERMINALE MOBILE", use_container_width=True):
        if pwd.strip() == PASSWORD_APPLICATIVO:
            st.session_state.autenticato = True
            st.rerun()
        else:
            st.error("❌ Chiave di sblocco errata.")
    st.stop()


# ==========================================
# 2. BARRA LATERALE (SIDEBAR MOBILE)
# ==========================================
with st.sidebar:
    st.title("🛡️ Maresc[İA]llo")
    st.caption("Consultazione Normativa & Compliance On-The-Field")
    st.divider()

    api_key = st.text_input("Chiave API Google:", type="password", key="api_key_input")

    stile_interfaccia = st.selectbox(
        "💬 Modalità Interfaccia IA:",
        ["🤝 Collega (Naturale & Dettagliato)", "⚡ Sintetico (Solo Dati Essenziali)"]
    )

    st.divider()

    # EXPANDER CONTO ECONOMICO & COSTI API MOBILE
    with st.expander("💶 Gestione Costi API (€)", expanded=False):
        tot_sess_t = st.session_state.sess_token_in + st.session_state.sess_token_out
        st.write(f"**Token Elaborati:** {tot_sess_t:,}")
        st.write(f"**Spesa Sessione:** {st.session_state.sess_costo_eur:.4f} €")
        st.caption("Tariffe Gemini Flash: ~0.069 € / 1M token In | ~0.276 € / 1M token Out")

    st.divider()

    if st.button("🔄 Nuova Indagine (Reset)", use_container_width=True, type="secondary"):
        st.session_state.storico_chat = []
        st.success("Memoria di lavoro azzerata.")
        st.rerun()


# ==========================================
# 3. INTERFACCIA PRINCIPALE CHAT & ALLEGATI
# ==========================================
st.markdown("### 📂 Documentazione e Quesiti Ispettivi")

uploaded_files = st.file_uploader(
    "Carica atti, registri (PDF/Excel) o foto (OCR):",
    type=["pdf", "xlsx", "txt", "png", "jpg", "jpeg"],
    accept_multiple_files=True
)

# AVVISO OCR FORMATO FILE
if uploaded_files:
    ha_immagini = any(f.name.split('.')[-1].lower() in ["png", "jpg", "jpeg"] for f in uploaded_files)
    if ha_immagini:
        st.info("ℹ️ **Avviso OCR (Immagini):** I file immagine scansionati richiedono l'elaborazione visiva e aumentano il consumo di token. Se disponibile, prediligi il formato PDF testuale nativo o Excel.")

st.divider()

# MONITOR CHAT STORICO
for msg in st.session_state.storico_chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# INPUT UTENTE (CHAT INPUT)
if prompt := st.chat_input("Inserisci il quesito o l'atto da analizzare..."):
    if not api_key:
        st.error("⚠️ Inserire prima la Chiave API Google nella barra laterale.")
        st.stop()

    # Visualizza quesito utente
    st.session_state.storico_chat.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Elaborazione risposta IA
    with st.chat_message("assistant"):
        with st.spinner("Maresciallo AI: Esame dei flussi contabili in corso..."):
            try:
                testo_atti, immagini, tot_pagine = leggi_file_caricati(uploaded_files)
                p_completo = prompt
                if testo_atti:
                    p_completo += f"\n\n[DOCUMENTAZIONE ISPETTIVA ALLEGATA]\n{testo_atti}"

                client = genai.Client(api_key=api_key)

                istruzione_stile = "Esponi con tono naturale, collaborativo e articolato, mantenendo elevata precisione tecnica."
                if "Sintetico" in stile_interfaccia:
                    istruzione_stile = "Esponi in modo estremamente sintetico, schematico e diretto, fornendo solo i dati e le conclusioni essenziali."

                sys_prompt = (
                    f"Sei un Assistente Virtuale Avanzato per l'Analisi Economico-Finanziaria e la Compliance Tributaria sul campo.\n\n"
                    f"--- STILE DI INTERAZIONE ---\n{istruzione_stile}\n\n"
                    "--- DIRETTIVE OPERATIVE ---\n"
                    "1. DICHIARAZIONE OBBLIGATORIA DEL PERIMETRO DI LETTURA: Inizia TASSATIVAMENTE la risposta dichiarando la quantita' esatta di file ed eventualmente di pagine analizzate.\n"
                    "2. ALERT DI TRONCATURA O ANOMALIA: Qualora rilevi pagine illeggibili o incomplete, apponi subito l'avviso di attenzione.\n"
                    "3. INTEGRITÀ DEI DATI: Mantieni intatti tutti i dati identificativi reali (Denominazioni, Codici Fiscali, Partite IVA, IBAN, date e importi).\n"
                    "4. FORMATTAZIONE TABELLARE: Qualsiasi confronto o riepilogo numerico DEVE essere espresso in forma di tabella Markdown classica.\n\n"
                    "--- STRUTTURA DELLA RISPOSTA ---\n"
                    "- 📌 PERIMETRO DI ANALISI ED ESAME PAGINE\n"
                    "- 📍 QUESITO / OGGETTO\n"
                    "- 📊 SINTESI DEI DATI ED INCROCIO FLUSSI\n"
                    "- 🔍 RILIEVI E ANOMALIE EVIDENZIATE\n"
                    "- 📝 CONCLUSIONI TECNICHE"
                )

                contents = []
                for m in st.session_state.storico_chat[:-1]:
                    contents.append(types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part.from_text(text=m["content"])]))
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=p_completo)] + immagini))

                res = client.models.generate_content(
                    model='gemini-flash-latest',
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=sys_prompt, temperature=0.2)
                )

                costo_operazione = 0.0
                if hasattr(res, 'usage_metadata') and res.usage_metadata:
                    t_in = res.usage_metadata.prompt_token_count or 0
                    t_out = res.usage_metadata.candidates_token_count or 0
                    costo_operazione = registra_consumo_token(t_in, t_out)

                risposta_corretta = correggi_ortografia_italiana(res.text)
                risposta_finale = risposta_corretta + f"\n\n---\n*💶 Spesa API per questo atto: {costo_operazione:.5f} €*"

                st.markdown(risposta_finale)
                st.session_state.storico_chat.append({"role": "assistant", "content": risposta_finale})

            except Exception as e:
                st.error(f"⚠️ Sospensione durante l'elaborazione: {str(e)}")