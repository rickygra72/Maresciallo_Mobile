import streamlit as st
import os
import re
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

try:
    from docx import Document
except ImportError:
    Document = None

# Configurazione Pagina Streamlit
st.set_page_config(
    page_title="Maresciallo AI - Unità Investigativa",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Stile CSS personalizzato per la plancia mobile
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    .sidebar .stSidebar { background-color: #161b22; }
    h1, h2, h3 { color: #FFD700 !important; }
    .stButton>button { width: 100%; border-radius: 4px; font-weight: bold; background-color: #2d3748; color: #ffffff; border: 1px solid #4a5568; }
    .stButton>button:hover { background-color: #00E676; color: #0d1117; border: 1px solid #00E676; }
    </style>
""", unsafe_allow_html=True)

PASSWORD_APPLICATIVO = "GdiF_117"
DEFAULT_COST_INPUT_1M_EUR = 0.069
DEFAULT_COST_OUTPUT_1M_EUR = 0.276

# Gestione Autenticazione con campo password ben visibile
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #FFD700;'>🔒 SISTEMA CRITTOGRAFATO - ACCESSO RISERVATO</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b949e;'>Inserire la password di sblocco per accedere alla plancia operativa:</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd_input = st.text_input("Password:", type="password", label_visibility="collapsed", placeholder="Inserisci password...")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔓 SBLOCCA TERMINALE"):
            if pwd_input.strip() == PASSWORD_APPLICATIVO:
                st.session_state.autenticato = True
                st.rerun()
            else:
                st.error("❌ Password errata.")
    st.stop()

# Inizializzazione Stati di Sessione
if "storico_chat" not in st.session_state:
    st.session_state.storico_chat = []
if "sess_token_in" not in st.session_state:
    st.session_state.sess_token_in = 0
if "sess_token_out" not in st.session_state:
    st.session_state.sess_token_out = 0
if "sess_costo_eur" not in st.session_state:
    st.session_state.sess_costo_eur = 0.0

# --- SIDEBAR OPERATIVA ---
with st.sidebar:
    st.markdown("### 🛡️ Maresciallo AI [Mobile]")
    
    # Selezione Reparto (PEF / PG)
    modalita = st.selectbox(
        "🏢 Reparto Operativo:",
        options=["PEF", "PG"],
        format_func=lambda x: "🟡 Polizia Economico-Finanziaria (P.E.F.)" if x == "PEF" else "🔵 Polizia Giudiziaria (P.G.)"
    )
    
    api_key_input = st.text_input("Chiave API Google:", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
    
    stile_interfaccia = st.selectbox(
        "💬 Stile Interfaccia:",
        options=["Collega (Naturale & Dettagliato)", "Sintetico (Solo Dati Essenziali)"]
    )
    
    st.markdown("---")
    st.markdown("### 📂 ALLEGATI")
    uploaded_files = st.file_uploader(
        "Carica atti, verbali o file contabili",
        type=["pdf", "xlsx", "txt", "png", "jpg", "jpeg", "docx"],
        accept_multiple_files=True
    )
    
    presenza_immagini = False
    if uploaded_files:
        for f in uploaded_files:
            if f.name.split('.')[-1].lower() in ["jpg", "jpeg", "png"]:
                presenza_immagini = True
        if presenza_immagini:
            st.warning("⚠️ Rilevate immagini/scansioni: l'elaborazione visiva (OCR) inciderà sui token.")

    st.markdown("---")
    st.markdown("### 💶 CONSUMI SESSIONE")
    tot_token = st.session_state.sess_token_in + st.session_state.sess_token_out
    st.info(f"• Token Elaborati: {tot_token:,}\n• Spesa Stimata: {st.session_state.sess_costo_eur:.4f} €")
    
    st.markdown("---")
    if st.button("🔄 Nuova Indagine (Reset)"):
        st.session_state.storico_chat = []
        st.session_state.sess_token_in = 0
        st.session_state.sess_token_out = 0
        st.session_state.sess_costo_eur = 0.0
        st.rerun()

# --- CORPO PRINCIPALE CHAT ---
titolo_plancia = "Polizia Economico-Finanziaria (P.E.F.)" if modalita == "PEF" else "Polizia Giudiziaria (P.G.)"
st.markdown(f"## 🛡️ Unità Investigativa - {titolo_plancia}")
st.markdown("<div style='font-size: 0.9em; color: #8b949e; margin-bottom: 15px;'>Protocollo di analisi forense e riscontro normativo attivo.</div>", unsafe_allow_html=True)

# Visualizzazione Storico Chat
for msg in st.session_state.storico_chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input Utente
prompt_utente = st.chat_input("Inserisci il quesito o l'atto da esaminare...")

if prompt_utente:
    if not api_key_input:
        st.error("⚠️ Inserisci la Chiave API Google nella barra laterale per procedere.")
        st.stop()
        
    st.session_state.storico_chat.append({"role": "user", "content": prompt_utente})
    with st.chat_message("user"):
        st.markdown(prompt_utente)
        
    with st.chat_message("assistant"):
        with st.spinner("Elaborazione e riscontro in corso..."):
            try:
                testo_atti = ""
                immagini = []
                
                if uploaded_files:
                    for f in uploaded_files:
                        ext = f.name.split('.')[-1].lower()
                        if ext in ["jpg", "jpeg", "png"]:
                            mime = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
                            immagini.append(types.Part.from_bytes(data=f.read(), mime_type=mime))
                            continue
                        
                        testo_atti += f"\n[FILE ALLEGATO: {f.name}]\n"
                        try:
                            if ext == "txt":
                                testo_atti += f.read().decode("utf-8", errors="ignore")
                            elif ext == "pdf" and pypdf:
                                reader = pypdf.PdfReader(f)
                                for num_p, page in enumerate(reader.pages, start=1):
                                    t = page.extract_text()
                                    if t: testo_atti += f"--- Pagina {num_p} ---\n" + t + "\n"
                            elif ext == "xlsx" and openpyxl:
                                ws = openpyxl.load_workbook(f, data_only=True).active
                                for row in ws.iter_rows(values_only=True):
                                    if any(row): testo_atti += " | ".join([str(c) if c is not None else "" for c in row]) + "\n"
                            elif ext == "docx" and Document:
                                doc = Document(f)
                                for p in doc.paragraphs:
                                    if p.text: testo_atti += p.text + "\n"
                        except Exception as e:
                            testo_atti += f"[Errore lettura file: {str(e)}]\n"

                p_completo = prompt_utente
                if testo_atti:
                    p_completo += f"\n\n[DOCUMENTI ALLEGATI]\n{testo_atti}"

                client = genai.Client(api_key=api_key_input)
                
                istruzione_stile = "Esponi con tono naturale, collaborativo e articolato, mantenendo elevata precisione tecnica."
                if "Sintetico" in stile_interfaccia:
                    istruzione_stile = "Esponi in modo estremamente sintetico, schematico e diretto, fornendo solo i dati e le conclusioni essenziali."

                if modalita == "PEF":
                    sys_prompt = (
                        "Sei un Assistente Virtuale Senior specializzato in Polizia Economico-Finanziaria (P.E.F.), Audit Forense e Diritto Tributario.\n\n"
                        f"--- STILE DI INTERAZIONE ---\n{istruzione_stile}\n\n"
                        "--- DIRETTIVE OPERATIVE P.E.F. & REATI TRIBUTARI ---\n"
                        "1. DICHIARAZIONE PERIMETRO: Inizia dichiarando la quantità esatta di file ed eventualmente di pagine esaminate.\n"
                        "2. AUDIT FRODI IVA & ANALISI D.LGS. 74/2000:\n"
                        "   • Rilevamento Frodi IVA: Analizza schemi di frode carosello, missing trader, societa' cartiere (assenza di struttura/dipendenti a fronte di volumi d'affari elevati, sedi fittizie, ricarichi minimi 1-2%, incongruenze nei vettori/DDT e nei flussi finanziari).\n"
                        "   • Rilievo Reati Tributari (D.Lgs. 74/2000): Oltre ai profili amministrativi, verifica puntualmente l'applicabilità dei delitti tributari:\n"
                        "     - Art. 2 (Dichiarazione fraudolenta mediante fatture per operazioni inesistenti - FOI)\n"
                        "     - Art. 3 (Dichiarazione fraudolenta mediante altri artifici)\n"
                        "     - Art. 4 e 5 (Dichiarazione infedele e omessa dichiarazione, con verifica del superamento delle relative SOGLIE DI PUNIBILITÀ)\n"
                        "     - Art. 8 (Emissione di fatture per operazioni inesistenti)\n"
                        "     - Art. 10 (Occultamento o distruzione di documenti contabili)\n"
                        "     - Art. 10-bis e 10-ter (Omesso versamento di ritenute e IVA).\n"
                        "   • Calcolo dell'Imposta Evasa e Quadratura: Esponi sempre in tabella Markdown i prospetti di ricostruzione dell'Imponibile, dell'IVA e delle Imposte Dirette Evasa/Indebitamente Detratta.\n\n"
                        "--- STRUTTURA DELLA RISPOSTA ---\n"
                        "- 📌 PERIMETRO DI ANALISI ED ESAME DOCUMENTALE\n"
                        "- 📍 QUESITO / FATTISPECIE ISPETTIVA\n"
                        "- 📊 QUADRO COMPARATIVO E TABELLA DELLE IMPOSTE EVASE / SOGLIE\n"
                        "- 🔍 RILIEVI FISCALI ED EVENTUALI PROFILI PENALI (D.Lgs. 74/2000)\n"
                        "- 📝 CONCLUSIONI TECNICHE ED APPROFONDIMENTI ISPETTIVI SUGGERITI"
                    )
                else:
                    sys_prompt = (
                        "Sei un Assistente Virtuale Senior specializzato in Polizia Giudiziaria (P.G.), Diritto Penale e Procedura Penale (c.p.p.).\n\n"
                        f"--- STILE DI INTERAZIONE ---\n{istruzione_stile}\n\n"
                        "--- DIRETTIVE OPERATIVE POLIZIA GIUDIZIARIA ---\n"
                        "1. DICHIARAZIONE PERIMETRO: Inizia dichiarando la quantità esatta di atti penali ed elementi di prova esaminati.\n"
                        "2. QUALIFICAZIONE PENALE E NORMATIVA PROCEDURALE:\n"
                        "   • Inquadramento Penale Rigoroso: Qualifica giuridicamente le condotte penalmente rilevanti (D.Lgs. 74/2000, Reati Societari ex art. 2621 e ss. c.c., Reati Fallimentari/Bancarotta ex CCII, Reati contro la P.A. o il Patrimonio).\n"
                        "   • Elemento Soggettivo e Materiale: Analizza il dolo specifico di evasione o di profitto e la condotta materiale con riferimenti alle più recenti sentenze di Cassazione Penale.\n"
                        "   • Procedura Penale (c.p.p.): Verifica la regolarità degli atti di P.G. (art. 347 c.p.p. Informativa di Reato, art. 352 c.p.p. Perquisizione, art. 354 c.p.p. Sequestro probatorio/preventivo) e il rispetto tassativo delle GARANZIE DIFENSIVE ex art. 356 c.p.p. per evitare eccezioni di inutilizzabilità.\n"
                        "3. REDAZIONE ATTI DI P.G.: Fornisci indicazioni formali chiare e bozze di clausole giuridiche per la redazione di Annotazioni e Informative di Reato a perfetta tenuta dibattimentale.\n\n"
                        "--- STRUTTURA DELLA RISPOSTA ---\n"
                        "- 📌 PERIMETRO DI ANALISI ED ESAME ATTI DI P.G.\n"
                        "- 📍 REATO / FATTISPECIE PENALE CONTESTATA\n"
                        "- ⚖️ QUALIFICAZIONE GIURIDICA (Fattispecie, Dolo, Giurisprudenza & Soglie Penali)\n"
                        "- 🔍 RISCONTRO PROCEDURALE PENALE (c.p.p., Garanzie & Tenuta Probatoria)\n"
                        "- 📝 DIRETTIVE FORMALI PER LA REDAZIONE DEGLI ATTI DI P.G."
                    )

                contents = []
                for m in st.session_state.storico_chat[:-1]:
                    contents.append(types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part.from_text(text=m["content"])]))
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=p_completo)] + immagini))

                res = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=sys_prompt, temperature=0.2)
                )

                costo_atto = 0.0
                if hasattr(res, 'usage_metadata') and res.usage_metadata:
                    t_in = res.usage_metadata.prompt_token_count or 0
                    t_out = res.usage_metadata.candidates_token_count or 0
                    st.session_state.sess_token_in += t_in
                    st.session_state.sess_token_out += t_out
                    costo_atto = (t_in / 1_000_000.0) * DEFAULT_COST_INPUT_1M_EUR + (t_out / 1_000_000.0) * DEFAULT_COST_OUTPUT_1M_EUR
                    st.session_state.sess_costo_eur += costo_atto

                risposta_ia = res.text + f"\n\n[💶 Spesa API per questo atto: {costo_atto:.5f} €]"
                
                st.markdown(risposta_ia)
                st.session_state.storico_chat.append({"role": "assistant", "content": risposta_ia})

            except Exception as e:
                st.error(f"⚠️ Errore durante l'elaborazione: {str(e)}")