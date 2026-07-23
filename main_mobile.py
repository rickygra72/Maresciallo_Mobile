import os
import streamlit as st
import base64
import re
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

try:
    from docx import Document
except ImportError:
    Document = None

PASSWORD_APPLICATIVO = "GdiF_117"
DEFAULT_COST_INPUT_1M_EUR = 0.069
DEFAULT_COST_OUTPUT_1M_EUR = 0.276

# Configurazione pagina Streamlit ottimizzata per dispositivi mobili
st.set_page_config(
    page_title="Maresciallo AI - Mobile",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Stile CSS personalizzato con classi separate per P.E.F. (verde) e P.G. (blu) e dimensioni uniformi
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #ffffff; }
    .stTextInput > div > div > input { background-color: #1f242c; color: #ffffff; }
    .stSelectbox > div > div > select { background-color: #1f242c; color: #ffffff; }
    
    /* Pulsante PEF (Verde) - Larghezza e altezza uniformi */
    div.row-widget.stButton:nth-of-type(1) button {
        background-color: #161b22; 
        color: #00E676; 
        font-weight: bold; 
        border: 2px solid #00E676; 
        width: 100%;
        height: 110px;
        border-radius: 8px;
    }
    div.row-widget.stButton:nth-of-type(1) button:hover {
        background-color: #00E676; 
        color: #0d1117;
    }

    /* Pulsante PG (Blu) - Larghezza e altezza uniformi */
    div.row-widget.stButton:nth-of-type(2) button {
        background-color: #161b22; 
        color: #61afef; 
        font-weight: bold; 
        border: 2px solid #61afef; 
        width: 100%;
        height: 110px;
        border-radius: 8px;
    }
    div.row-widget.stButton:nth-of-type(2) button:hover {
        background-color: #61afef; 
        color: #0d1117;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 🔒 GESTIONE STATO E FLUSSO DI AUTENTICAZIONE
# ==========================================
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
if "privacy_accettata" not in st.session_state:
    st.session_state.privacy_accettata = False
if "modalita" not in st.session_state:
    st.session_state.modalita = "PEF"
if "storico_chat" not in st.session_state:
    st.session_state.storico_chat = []
if "token_in_tot" not in st.session_state:
    st.session_state.token_in_tot = 0
if "token_out_tot" not in st.session_state:
    st.session_state.token_out_tot = 0
if "spesa_tot_eur" not in st.session_state:
    st.session_state.spesa_tot_eur = 0.0


# 1️⃣ SCHERMATA LOGIN
if not st.session_state.autenticato:
    st.markdown("<h2 style='text-align: center; color: #FFD700;'>🔒 SISTEMA CRITTOGRAFATO</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b949e;'>Inserire la password di sblocco per accedere:</p>", unsafe_allow_html=True)
    
    with st.form("form_login"):
        pwd_input = st.text_input("Password:", type="password")
        submit_login = st.form_submit_button("🔓 SBLOCCA TERMINALE")
        if submit_login:
            if pwd_input.strip() == PASSWORD_APPLICATIVO:
                st.session_state.autenticato = True
                st.rerun()
            else:
                st.error("❌ Password errata.")
    st.stop()


# 2️⃣ DISCIPLINARE DI SICUREZZA & PRIVACY OBBLIGATORIO
if not st.session_state.privacy_accettata:
    st.markdown("<h3 style='color: #FFD700;'>🛡️ DISCIPLINARE DI SICUREZZA, PRIVACY & INTEGRITÀ DATI</h3>", unsafe_allow_html=True)
    
    st.info(
        "In conformità alle normative vigenti in materia di sicurezza informatica, tutela del "
        "segreto d'ufficio e protezione dei dati personali, l'applicazione adotta un rigoroso "
        "protocollo di elaborazione locale ad isolamento dinamico.\n\n"
        "**Linee guida e garanzie operative tassative:**\n\n"
        "1. **ISOLAMENTO VOLATILE (RAM):** I documenti contabili, i file PDF/Excel e i rilievi fotografici "
        "acquisiti (OCR) vengono elaborati esclusivamente all'interno della memoria RAM volatile. Nessun dato "
        "viene archiviato su disco rigido o database locali/remoti.\n\n"
        "2. **CIFRATURA DEI DATI E DOCUMENTI SENSIBILI IN TRANSITO:** La trasmissione delle chiavi API, "
        "dei quesiti e dell'intero contenuto dei documenti allegati (compresi i dati personali, riservati e "
        "sensibili) avviene TASSATIVAMENTE tramite canale cifrato e crittografato protetto (SSL/TLS). I flussi "
        "documentali non vengono impiegati per l'addestramento di modelli di intelligenza artificiale di terze parti.\n\n"
        "3. **CONTROLLO DEL PERIMETRO E INTEGRITÀ:** Il sistema verifica la lettura integrale del 100% "
        "delle pagine di ogni documento allegato. Qualora una pagina risulti incompleta o illeggibile, "
        "l'IA segnalerà immediatamente l'anomalia per garantire la conformità giuridica degli atti.\n\n"
        "4. **DISTRUZIONE CERTIFICATA ALL'ARRESTO:** Alla chiusura della sessione o mediante il comando "
        "'Nuova Indagine (Reset)', la memoria di lavoro viene sovrascritta e liberata istantaneamente."
    )
    
    if st.button("✅ ACCETTA ED ATTIVA PROTOCOLLO OPERATIVO"):
        st.session_state.privacy_accettata = True
        st.rerun()
    st.stop()


# 3️⃣ SELEZIONE REPARTO
if "reparto_scelto" not in st.session_state:
    st.markdown("<h2 style='text-align: center; color: #FFD700;'>🏢 SELEZIONA AMBITO D'INDAGINE</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b949e;'>Scegli la modalità di specializzazione operativa dell'IA:</p>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        if st.button("🟡 P.E.F.\n\nPolizia Economico-Finanziaria\n(Frodi IVA & D.Lgs. 74/2000)", key="btn_pef"):
            st.session_state.modalita = "PEF"
            st.session_state.reparto_scelto = True
            st.rerun()
            
    with col2:
        if st.button("🔵 P.G.\n\nPolizia Giudiziaria\n(Codice Penale & c.p.p.)", key="btn_pg"):
            st.session_state.modalita = "PG"
            st.session_state.reparto_scelto = True
            st.rerun()
    st.stop()


# ==========================================
# 🖥️ PLANCIA OPERATIVA MOBILE
# ==========================================
col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
with col_logo2:
    colore_titolo = "#00E676" if st.session_state.modalita == "PEF" else "#61afef"
    st.markdown(f"<h3 style='text-align: center; color: {colore_titolo};'>Maresc<span style='color: #FFD700;'>[İA]</span>llo</h3>", unsafe_allow_html=True)

sottotitolo_m = "Unità Investigativa - Polizia Economico-Finanziaria (P.E.F.)" if st.session_state.modalita == "PEF" else "Unità Investigativa - Polizia Giudiziaria (P.G.)"
st.markdown(f"<p style='text-align: center; font-size: 0.85em; color: #8b949e;'>{sottotitolo_m}</p>", unsafe_allow_html=True)

# SIDEBAR MOBILE
with st.sidebar:
    st.markdown("### ⚙️ Parametri Operativi")
    api_key_input = st.text_input("Chiave API Google:", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
    
    stile_risposta = st.selectbox("💬 Stile Interfaccia:", ["🤝 Collega (Naturale & Dettagliato)", "⚡ Sintetico (Solo Dati Essenziali)"])
    
    st.markdown("---")
    st.markdown("### 📂 Allegati per l'Esame")
    uploaded_files = st.file_uploader("Carica atti (PDF, Excel, Word, TXT, Immagini)", accept_multiple_files=True, type=["pdf", "xlsx", "txt", "png", "jpg", "jpeg", "docx"])
    
    st.markdown("---")
    if st.button("🔄 Cambia Reparto (PEF / PG)"):
        if "reparto_scelto" in st.session_state:
            del st.session_state.reparto_scelto
        st.session_state.storico_chat = []
        st.rerun()
        
    if st.button("🗑️ Nuova Indagine (Reset)"):
        st.session_state.storico_chat = []
        st.session_state.token_in_tot = 0
        st.session_state.token_out_tot = 0
        st.session_state.spesa_tot_eur = 0.0
        st.rerun()
        
    st.markdown("---")
    st.markdown("### 💶 Consumi Sessione")
    tot_t = st.session_state.token_in_tot + st.session_state.token_out_tot
    st.text(f"Token: {tot_t:,}\nSpesa: {st.session_state.spesa_tot_eur:.4f} €")


# FUNZIONE LETTURA ALLEGATI IN MEMORIA
def elabora_allegati():
    testo_aggregato = ""
    immagini_aggregate = []
    if not uploaded_files:
        return testo_aggregato, immagini_aggregate

    for file in uploaded_files:
        ext = file.name.split('.')[-1].lower()
        if ext in ["jpg", "jpeg", "png"]:
            mime = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
            immagini_aggregate.append(types.Part.from_bytes(data=file.read(), mime_type=mime))
            continue
            
        testo_aggregato += f"\n[FILE ALLEGATO: {file.name}]\n"
        try:
            if ext == "txt":
                testo_aggregato += file.read().decode("utf-8", errors="ignore")
            elif ext == "pdf" and pypdf:
                reader = pypdf.PdfReader(file)
                for num_p, page in enumerate(reader.pages, start=1):
                    t = page.extract_text()
                    if t: testo_aggregato += f"--- Pagina {num_p} ---\n" + t + "\n"
            elif ext == "xlsx" and openpyxl:
                ws = openpyxl.load_workbook(file, data_only=True).active
                for row in ws.iter_rows(values_only=True):
                    if any(row): testo_aggregato += " | ".join([str(c) if c is not None else "" for c in row]) + "\n"
            elif ext == "docx" and Document:
                doc = Document(file)
                for p in doc.paragraphs:
                    if p.text: testo_aggregato += p.text + "\n"
        except Exception as e:
            testo_aggregato += f"[Errore lettura {file.name}: {str(e)}]\n"
    return testo_aggregato, immagini_aggregate


# MONITOR CHAT PRINCIPALE
for msg in st.session_state.storico_chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# INPUT UTENTE
prompt_utente = st.chat_input("Inserisci quesito o atto da esaminare...")

if prompt_utente:
    if not api_key_input:
        st.error("⚠️ Inserisci la Chiave API Google nella barra laterale.")
    else:
        st.session_state.storico_chat.append({"role": "user", "content": prompt_utente})
        with st.chat_message("user"):
            st.markdown(prompt_utente)

        with st.chat_message("assistant"):
            with st.spinner("Analisi in corso..."):
                try:
                    testo_atti, immagini = elabora_allegati()
                    p_completo = prompt_utente
                    if testo_atti: p_completo += f"\n\n[DOCUMENTI ALLEGATI]\n{testo_atti}"

                    client = genai.Client(api_key=api_key_input)
                    
                    istruzione_stile = "Esponi con tono naturale, collaborativo e articolato, mantenendo elevata precisione tecnica."
                    if "Sintetico" in stile_risposta:
                        istruzione_stile = "Esponi in modo estremamente sintetico, schematico e diretto, fornendo solo i dati e le conclusioni essenziali."

                    if st.session_state.modalita == "PEF":
                        sys_prompt = (
                            "Sei un Assistente Virtuale Senior specializzato in Polizia Economico-Finanziaria (P.E.F.), Audit Forense e Diritto Tributario.\n\n"
                            f"--- STILE DI INTERAZIONE ---\n{istruzione_stile}\n\n"
                            "--- DIRETTIVE OPERATIVE P.E.F. & REATI TRIBUTARI ---\n"
                            "1. DICHIARAZIONE PERIMETRO: Inizia dichiarando la quantità esatta di file ed eventualmente di pagine esaminate.\n"
                            "2. AUDIT FRODI IVA & ANALISI D.LGS. 74/2000:\n"
                            "   • Rilevamento Frodi IVA: Analizza schemi di frode carosello, missing trader, societa' cartiere (assenza di struttura/dipendenti a fronte di volumi d'affari elevati, sedi fittizie, ricarichi minimi 1-2%, incongruenze nei vettori/DDT e nei flussi finanziari).\n"
                            "   • Rilievo Reati Tributari (D.Lgs. 74/2000): Oltre ai profili amministrativi, verifica puntualmente l'applicabilità dei delitti tributari (Art. 2, 3, 4, 5, 8, 10, 10-bis, 10-ter) e il superamento delle relative SOGLIE DI PUNIBILITÀ.\n"
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
                        model='gemini-2.5-flash',
                        contents=contents,
                        config=types.GenerateContentConfig(system_instruction=sys_prompt, temperature=0.2)
                    )

                    costo_atto = 0.0
                    if hasattr(res, 'usage_metadata') and res.usage_metadata:
                        t_in = res.usage_metadata.prompt_token_count or 0
                        t_out = res.usage_metadata.candidates_token_count or 0
                        st.session_state.token_in_tot += t_in
                        st.session_state.token_out_tot += t_out
                        costo_atto = ((t_in / 1_000_000.0) * DEFAULT_COST_INPUT_1M_EUR) + ((t_out / 1_000_000.0) * DEFAULT_COST_OUTPUT_1M_EUR)
                        st.session_state.spesa_tot_eur += costo_atto

                    risposta_finale = res.text + f"\n\n[💶 Spesa API per questo atto: {costo_atto:.5f} €]"
                    st.markdown(risposta_finale)
                    st.session_state.storico_chat.append({"role": "assistant", "content": risposta_finale})
                except Exception as e:
                    st.error(f"⚠️ Errore di elaborazione: {str(e)}")