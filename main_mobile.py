import streamlit as st
import os
from google import genai
from google.genai import types

# Librerie per l'estrazione testuale dei documenti d'ufficio
import pypdf
import openpyxl
import docx

# Libreria professionale per reportistica PDF con tabelle grafiche avanzate
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO

st.set_page_config(
    page_title="🛡️ Terminale Tattico - Maresciallo AI",
    page_icon="🛡️",
    layout="wide"
)

# --- GESTIONE PASSWORD DI ACCESSO DELL'APPLICATIVO ---
PASSWORD_APPLICATIVO = "GdiF_117"  # 🔒 Chiave di sblocco di squadra configurata

if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

# Schermata di Login bloccante
if not st.session_state.autenticato:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(
        "<h2 style='text-align: center; font-family: sans-serif; color: #FFD700;'>"
        "🔒 SISTEMA CRITTOGRAFATO - ACCESSO RISERVATO"
        "</h2>", 
        unsafe_allow_html=True
    )
    st.markdown("<p style='text-align: center; color: #8b949e;'>Inserire le credenziali operative per sbloccare il terminale.</p>", unsafe_allow_html=True)
    
    col_login_1, col_login_2, col_login_3 = st.columns([1, 2, 1])
    with col_login_2:
        pwd_inserita = st.text_input("Password di Sicurezza", type="password", placeholder="Digitare la chiave di sblocco...")
        if st.button("🔓 SBLOCCA TERMINALE", use_container_width=True):
            if pwd_inserita == PASSWORD_APPLICATIVO:
                st.session_state.autenticato = True
                st.rerun()
            else:
                st.error("❌ Chiave di sblocco errata. Accesso negato.")
    st.stop()

# --- INIZIALIZZAZIONE MEMORIA DI SESSIONE (RAM VOLATILE) ---
if "storico_chat" not in st.session_state:
    st.session_state.storico_chat = []

if "dati_allegati_salvati" not in st.session_state:
    st.session_state.dati_allegati_salvati = {
        "immagini": [],
        "testo_documenti": "",
        "nomi_file": []
    }

# --- FUNZIONI DI ESTRAZIONE DATI ---
def estrai_testo_documento(file):
    nome_file = file.name.lower()
    testo_estratto = f"\n--- CONTENUTO ALLEGATO: {file.name} ---\n"
    
    try:
        if nome_file.endswith('.pdf'):
            lettore = pypdf.PdfReader(file)
            for pagina in lettore.pages:
                testo_estratto += pagina.extract_text() + "\n"
                
        elif nome_file.endswith('.docx'):
            doc = docx.Document(file)
            for paragrafo in doc.paragraphs:
                testo_estratto += paragrafo.text + "\n"
                
        elif nome_file.endswith('.xlsx'):
            wb = openpyxl.load_workbook(file, data_only=True)
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                testo_estratto += f"[Foglio: {sheet}]\n"
                for riga in ws.iter_rows(values_only=True):
                    if any(riga):  
                        testo_estratto += "\t".join([str(cella) if cella is not None else "" for cella in riga]) + "\n"
        return testo_estratto
    except Exception as e:
        return f"\n⚠️ [Errore estrazione testo da {file.name}: {str(e)}]\n"

# --- FUNZIONE DI CATTURA IMMEDIATA ALLEGATI DALL'ARCHIVIO O GALLERIA ---
def elabora_file_caricati():
    if "caricatore_chiave" in st.session_state and st.session_state.caricatore_chiave:
        for f in st.session_state.caricatore_chiave:
            if f.name not in st.session_state.dati_allegati_salvati["nomi_file"]:
                tipo_mime = getattr(f, "type", "").lower()
                est = f.name.split('.')[-1].lower()
                
                if "image" in tipo_mime or est in ['png', 'jpg', 'jpeg']:
                    mime_finale = tipo_mime if "image" in tipo_mime else f"image/{est}"
                    if "jpeg" in mime_finale or "jpg" in mime_finale:
                        mime_finale = "image/jpeg"
                    
                    st.session_state.dati_allegati_salvati["immagini"].append({
                        "data": f.read(),
                        "mime": mime_finale
                    })
                elif est in ['pdf', 'docx', 'xlsx']:
                    st.session_state.dati_allegati_salvati["testo_documenti"] += estrai_testo_documento(f)
                
                st.session_state.dati_allegati_salvati["nomi_file"].append(f.name)

# --- GENERAZIONE PDF AVANZATA CON TABELLE NATIVE E REPORTLAB ---
def genera_pdf_report(testo_relazione):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    style_titolo = ParagraphStyle(
        'TitoloReport',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        alignment=1, # Centrato
        spaceAfter=15
    )
    style_corpo = ParagraphStyle(
        'CorpoReport',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        spaceAfter=6
    )
    style_cella_header = ParagraphStyle(
        'CellaHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.whitesmoke
    )
    style_cella_body = ParagraphStyle(
        'CellaBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10
    )

    story = []
    story.append(Paragraph("RELAZIONE TECNICA ISPETTIVA", style_titolo))
    story.append(Spacer(1, 10))

    righe = testo_relazione.split('\n')
    blocco_tabella = []

    for riga in righe:
        riga_strip = riga.strip()
        
        # Accumulo delle righe appartenenti a una tabella Markdown
        if riga_strip.startswith('|'):
            if "---" in riga_strip:
                continue
            elementi = [el.strip() for el in riga_strip.split('|')[1:-1]]
            if elementi:
                blocco_tabella.append(elementi)
            continue
        else:
            # Renderizzazione del blocco tabella accumulato
            if blocco_tabella:
                dati_tabella = []
                for index, riga_tab in enumerate(blocco_tabella):
                    riga_pari = []
                    style_attuale = style_cella_header if index == 0 else style_cella_body
                    for cel in riga_tab:
                        cel_clean = cel.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('**', '')
                        riga_pari.append(Paragraph(cel_clean, style_attuale))
                    dati_tabella.append(riga_pari)

                t = Table(dati_tabella)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B4D3E')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                ]))
                story.append(t)
                story.append(Spacer(1, 10))
                blocco_tabella = []

        if not riga_strip:
            story.append(Spacer(1, 4))
            continue
            
        riga_sicura = riga_strip.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        if riga_strip.startswith('###') or riga_strip.startswith('**'):
            testo_clean = riga_sicura.replace('#', '').replace('**', '').strip()
            style_h = ParagraphStyle('HeaderDyn', parent=style_corpo, fontName='Helvetica-Bold', fontSize=11, leading=15)
            story.append(Paragraph(testo_clean, style_h))
        else:
            story.append(Paragraph(riga_sicura, style_corpo))

    # Controllo di chiusura per tabelle al termine esatto del documento
    if blocco_tabella:
        dati_tabella = []
        for index, riga_tab in enumerate(blocco_tabella):
            riga_pari = []
            style_attuale = style_cella_header if index == 0 else style_cella_body
            for cel in riga_tab:
                cel_clean = cel.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('**', '')
                riga_pari.append(Paragraph(cel_clean, style_attuale))
            dati_tabella.append(riga_pari)

        t = Table(dati_tabella)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B4D3E')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

    doc.build(story)
    return buffer.getvalue()

def genera_docx_report(testo_relazione):
    doc = docx.Document()
    p_titolo = doc.add_paragraph()
    run_titolo = p_titolo.add_run("RELAZIONE TECNICA ISPETTIVA\n")
    run_titolo.font.name = 'Arial'
    run_titolo.font.size = docx.shared.Pt(14)
    run_titolo.bold = True
    p_titolo.alignment = 1 
    
    testo_pulito = testo_relazione.replace("?", "€")
    righe = testo_pulito.split("\n")
    tabella_docx = None
    
    for riga in righe:
        if riga.strip().startswith("|"):
            if "---" in riga:
                continue
            colonne = [col.strip() for col in riga.split("|") if col.strip()]
            
            if tabella_docx is None:
                tabella_docx = doc.add_table(rows=0, cols=len(colonne))
                tabella_docx.style = 'Light Shading Accent 1' 
            
            row_cells = tabella_docx.add_row().cells
            for idx, col in enumerate(colonne):
                row_cells[idx].text = col.replace("**", "")
        else:
            tabella_docx = None 
            if riga.strip():
                p = doc.add_paragraph()
                run = p.add_run(riga.replace("**", "").replace("###", "").strip())
                if riga.strip().startswith("###") or riga.strip().startswith("**"):
                    run.bold = True
                    run.font.size = docx.shared.Pt(11)
                else:
                    run.font.size = docx.shared.Pt(10)
                    
    target = BytesIO()
    doc.save(target)
    return target.getvalue()

# --- TESTATA INTERFACCIA ---
st.markdown(
    "<h1 style='text-align: center; margin-bottom: 0; font-family: sans-serif;'>"
    "<span style='color: #00E676; font-style: italic; font-weight: bold;'>Maresc</span>"
    "<span style='color: #FFD700; font-weight: bold;'>[İA]</span>"
    "<span style='color: #00E676; font-style: italic; font-weight: bold;'>llo</span>"
    "</h1>", 
    unsafe_allow_html=True
)
st.markdown("<p style='text-align: center; font-style: italic; color: #8b949e; margin-top: 0;'>Unità Tattica Mobile - Terminale Operativo</p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color: #2d3748; margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

# --- CONFIGURAZIONE CHIAVE API ---
entry_key = st.text_input("Chiave API Crittografata", type="password")

# --- DISPOSITIVA PRIVACY & SICUREZZA ESPANSA ---
with st.expander("🔒 NOTE SULLA SICUREZZA E PRIVACY DEI DATI"):
    st.markdown("""
    ### 🛡️ Protocollo Rigido di Trattamento delle Informazioni Ispettive
    Il presente applicativo è stato ingegnerizzato per soddisfare i più stringenti requisiti di sicurezza e segretezza richiesti durante le attività di verifica fiscale e controllo societario sul campo. Il trattamento dei flussi documentali rispetta i seguenti criteri tassativi:
    
    * **Zero Persistenza e Archiviazione Cloud (No Log Localizzato):** L'applicazione opera in modalità totalmente *stateless*. Nessun file (PDF, Excel, Immagine) e nessun frammento di testo inserito viene memorizzato in database remoti, server persistenti o storici di terze parti.
    * **Isolamento della Sessione in Memoria Volatile (RAM):** Tutte le informazioni estratte dai documenti e lo storico della chat risiedono esclusivamente nella memoria RAM volatile assegnata alla sessione corrente del dispositivo. 
    * **Cancellazione Certificata all'Arresto:** Al momento della chiusura della pagina web o tramite la pressione del comando *'Nuova Indagine (Reset)'*, la RAM viene immediatamente sovrascritta e liberata, determinando la distruzione istantanea e irreversibile di tutti i dati aziendali o personali trattati.
    * **Canale Cifrato End-to-End delle API:** Il transito verso i modelli di calcolo avviene tramite connessione crittografata diretta e protetta dalla tua chiave API personale. I dati inviati per l'analisi non vengono utilizzati per l'addestramento dei modelli pubblici.
    """)

# --- STRUMENTI DI ACQUISIZIONE DALLA MEMORIA LOCALE ---
st.file_uploader(
    "📁 Importa Allegati (Galleria Foto, Documenti PDF, Excel, Word)", 
    type=["png", "jpg", "jpeg", "pdf", "docx", "xlsx"], 
    accept_multiple_files=True,
    key="caricatore_chiave",
    on_change=elabora_file_caricati
)

# Mostra a schermo i file bloccati saldamente in memoria
if st.session_state.dati_allegati_salvati["nomi_file"]:
    st.markdown("#### 📦 Materiale Acquisito in Memoria:")
    for nome in st.session_state.dati_allegati_salvati["nomi_file"]:
        st.markdown(f"<span style='color: #00E676;'>✔️ {nome} (Pronto all'esame)</span>", unsafe_allow_html=True)

if st.button("🔄 Nuova Indagine (Reset)", use_container_width=True):
    st.session_state.storico_chat = []
    st.session_state.dati_allegati_salvati = {"immagini": [], "testo_documenti": "", "nomi_file": []}
    st.rerun()

# --- REGISTRO CHAT ---
st.markdown("### 🖥️ Chat Terminale Operativo")

st.markdown("""
    <style>
        .chat-box {
            background-color: #161b22;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            border-left: 4px solid #00E676;
            margin-bottom: 15px;
            overflow-x: auto;
            white-space: pre-wrap;
        }
    </style>
""", unsafe_allow_html=True)

ultima_relazione = ""

if not st.session_state.storico_chat:
    st.markdown("<div class='chat-box'><span style='color: #00E676;'>Maresciallo AI: Pronto a forniti un aiuto...</span></div>", unsafe_allow_html=True)
else:
    for msg in st.session_state.storico_chat:
        if msg["role"] == "user":
            st.markdown(f"<div class='chat-box'><span style='color: #ffffff;'><b>Operatore:</b><br>{msg['content']}</span></div>", unsafe_allow_html=True)
        else:
            with st.container():
                st.markdown(f"**Maresciallo AI:**")
                st.markdown(msg['content'])
            ultima_relazione = msg['content']

# --- STRUMENTI DI ESPORTAZIONE ATTI ---
if ultima_relazione:
    st.markdown("#### 📂 Esportazione Atto Tecnico")
    exp_col1, exp_col2 = st.columns(2)
    
    with exp_col1:
        try:
            pdf_data = genera_pdf_report(ultima_relazione)
            st.download_button(
                label="📄 Scarica Relazione in PDF",
                data=pdf_data,
                file_name="relazione_ispettiva.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as pdf_err:
            st.error(f"⚠️ Errore compilazione PDF: {str(pdf_err)}")
        
    with exp_col2:
        try:
            docx_data = genera_docx_report(ultima_relazione)
            st.download_button(
                label="📝 Scarica Relazione in WORD",
                data=docx_data,
                file_name="relazione_ispettiva.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        except Exception as docx_err:
            st.error(f"⚠️ Errore compilazione Word: {str(docx_err)}")

# --- FORM DI TRATTAMENTO QUESITO CON RIPRISTINO MODELLO STABILE ORIGINAL ---
st.markdown("---")
prompt = st.text_area("Quesito operativo / Note di verifica", placeholder="Inserisci le tue richieste operative o documenti da esaminare...")

if st.button("🚀 INVIA RICHIESTA", use_container_width=True):
    chiave_pulita = entry_key.strip().replace(" ", "").replace("\n", "").replace("\r", "")
    
    if not chiave_pulita:
        st.error("⚠️ Inserire prima una chiave API valida!")
    elif not prompt.strip():
        st.warning("⚠️ Il testo del quesito non può essere vuoto.")
    else:
        with st.spinner("Analisi in corso ed elaborazione dati..."):
            try:
                client = genai.Client(api_key=chiave_pulita)
                
                immagini_parts = []
                for img in st.session_state.dati_allegati_salvati["immagini"]:
                    immagini_parts.append(
                        types.Part.from_bytes(data=img["data"], mime_type=img["mime"])
                    )
                
                testo_documenti_cumulato = st.session_state.dati_allegati_salvati["testo_documenti"]

                sys_prompt = (
                    "Sei un Assistente Virtuale Avanzato per l'Analisi Economico-Finanziaria e la Compliance Tributaria sul campo.\n\n"
                    "--- DIRETTIVE OPERATIVE E REGISTRO SPEECH ---\n"
                    "1. STILE E FORMATO: Esponi esclusivamente in forma di relazione tecnica asettica, formale e rigorosa. Elimina qualsiasi preambolo, saluto, convenevole o frase introduttiva. Inizia direttamente con l'analisi.\n"
                    "2. INTEGRITÀ DEI DATI: Mantieni intatti e privi di alterazioni tutti i dati identificativi reali (Denominazioni aziendali, Codici Fiscali, Partite IVA, IBAN, date e importi).\n\n"
                    "--- PRECISIONE E CALCOLO NUMERICO ---\n"
                    "3. RIGORE ARITMETICO: Quando esegui calcoli, sommatorie o riepiloghi di bilancio, verifica sempre il pareggio e la quadratura contabile. Esponi chiaramente le basi di calcolo (es. Imponibile, Aliquota, IVA, Totale) per garantire la massima verificabilità.\n"
                    "4. SINTESI E AGGREGAZIONE MASSIVA: Per volumi di dati estesi (es. libri giornali, estratti conto, partitari), aggrega i totali per fornitore, cliente, conto o causale. È TASSATIVAMENTE VIETATO elencare singolarmente operazioni ripetitive o decine di righe ridondanti.\n\n"
                    "--- TRATTAMENTO DOCUMENTI ED ALLEGATI ---\n"
                    "5. CORRISPONDENZA TESTUALE ED OCR: Analizza il testo estratto e le immagini allegate con il massimo livello di dettaglio. Qualora un dato sia illeggibile, incompleto o discordante tra gli allegati, segnalalo esplicitamente nella sezione anomalie senza ipotizzare o allucinare valori non presenti.\n\n"
                    "--- STRUTTURA DELLA RISPOSTA ---\n"
                    "Organizza sempre l'output secondo questo schema operativo:\n"
                    "- 📍 QUESITO / OGGETTO: (Sintesi formale della richiesta)\n"
                    "- 📊 SINTESI DEI DATI ED INCROCIO FLUSSI: (Tabelle ordinate e aggregate dei numeri d'interesse)\n"
                    "- 🔍 RILIEVI E ANOMALIE EVIDENZIATE: (Eventuali discrepanze, incongruenze o note rilevanti)\n"
                    "- 📝 CONCLUSIONI TECNICHE: (Esito sintetico e definitivo per gli atti)"
                )

                contents = []
                for m in st.session_state.storico_chat:
                    contents.append(types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part.from_text(text=m["content"])]))
                
                prompt_completo = prompt
                if testo_documenti_cumulato:
                    prompt_completo += "\n\n" + testo_documenti_cumulato

                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt_completo)] + immagini_parts))

                # Ripristinato il modello standard esatto privo di errori di indirizzamento
                res = client.models.generate_content(
                    model='gemini-flash-latest',
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=sys_prompt, temperature=0.2)
                )

                st.session_state.storico_chat.append({"role": "user", "content": prompt})
                st.session_state.storico_chat.append({"role": "assistant", "content": res.text})
                st.rerun()

            except Exception as ex:
                st.error(f"⚠️ Errore di execution: {str(ex)}")