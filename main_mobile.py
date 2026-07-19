import streamlit as st
import os
from google import genai
from google.genai import types

# Librerie per l'estrazione testuale dei documenti d'ufficio
import pypdf
import docx
import openpyxl

# Librerie per la generazione dei report esportabili
from fpdf import FPDF
from io import BytesIO
import docx as docx_gen

st.set_page_config(
    page_title="🛡️ Terminale Tattico - Maresciallo AI",
    page_icon="🛡️",
    layout="wide"  
)

if "storico_chat" not in st.session_state:
    st.session_state.storico_chat = []

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

# --- FUNZIONI DI ESPORTAZIONE REPORT POTENZIATE ---
def genera_pdf_report(testo_relazione):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "RELAZIONE TECNICA ISPETTIVA - COMPLIANCE", ln=True, align="C")
    pdf.ln(8)
    
    testo_pulito = testo_relazione.replace("?", "€").replace("€", "EUR")
    righe = testo_pulito.split("\n")
    in_tabella = False
    
    for riga in righe:
        if riga.strip().startswith("|"):
            if "---" in riga:
                continue
            in_tabella = True
            pdf.set_font("Courier", "B", 9)
            colonne = [col.strip() for col in riga.split("|") if col.strip()]
            
            riga_tabella = ""
            for i, col in enumerate(colonne):
                if i == 0:
                    riga_tabella += f"{col[:22]:<24}" 
                elif i in [1, 2, 3]:
                    riga_tabella += f"{col[:12]:<14}" 
                else:
                    riga_tabella += f" {col[:30]}"     
            pdf.cell(0, 5, riga_tabella, ln=True)
        else:
            if in_tabella:
                pdf.ln(3) 
                in_tabella = False
            
            if riga.strip().startswith("###") or riga.strip().startswith("**"):
                pdf.set_font("Helvetica", "B", 11)
                pdf.ln(2)
                pdf.cell(0, 6, riga.replace("#", "").replace("**", "").strip(), ln=True)
                pdf.ln(2)
            else:
                pdf.set_font("Helvetica", size=10)
                riga_codificata = riga.encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 5, riga_codificata)
                
    return bytes(pdf.output())

def genera_docx_report(testo_relazione):
    doc = docx_gen.Document()
    
    p_titolo = doc.add_paragraph()
    run_titolo = p_titolo.add_run("RELAZIONE TECNICA ISPETTIVA - COMPLIANCE\n")
    run_titolo.font.name = 'Arial'
    run_titolo.font.size = docx_gen.shared.Pt(14)
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
                    run.font.size = docx_gen.shared.Pt(11)
                else:
                    run.font.size = docx_gen.shared.Pt(10)
                    
    target = BytesIO()
    doc.save(target)
    return target.getvalue()

# --- TESTATA ---
st.markdown(
    "<h1 style='text-align: center; margin-bottom: 0; font-family: sans-serif;'>"
    "<span style='color: #00E676; font-style: italic; font-weight: bold;'>Maresc</span>"
    "<span style='color: #FFD700; font-weight: bold;'>[İA]</span>"
    "<span style='color: #00E676; font-style: italic; font-weight: bold;'>llo</span>"
    "</h1>", 
    unsafe_allow_html=True
)
st.markdown("<p style='text-align: center; font-style: italic; color: #8b949e; margin-top: 0;'>Unità Tattica Mobile - Terminale Operativo di Compliance</p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color: #2d3748; margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

# --- CONFIGURAZIONE CHIAVE API ---
entry_key = st.text_input("Chiave API Crittografata", type="password")

# --- DISPOSITIVA PRIVACY & SICUREZZA ---
with st.expander("🔒 NOTA OPERATIVA: PRIVACY E PROTOCOLLI DI SICUREZZA"):
    st.markdown("""
    ### 🛡️ Misure di Protezione e Trattamento Dati sul Campo
    Il presente applicativo è configurato per operare in conformità alle severe direttive di riservatezza necessarie durante le attività ispettive e di verifica fiscale:
    
    * **Assenza di Persistenza Remota:** Nessun dato inserito o file allegato viene salvato in database esterni o registri cloud. 
    * **Volatilità della Sessione (RAM):** Lo storico risiede esclusivamente nella memoria temporanea locale. All'azzeramento dell'indagine, viene definitivamente cancellato.
    """)

# --- STRUMENTI DI ACQUISIZIONE MULTI-FORMATO ---
allegati = st.file_uploader(
    "📷 Acquisisci Atti, Foto o Documenti", 
    type=["png", "jpg", "jpeg", "pdf", "docx", "xlsx"], 
    accept_multiple_files=True
)

if st.button("🔄 Nuova Indagine (Reset)", use_container_width=True):
    st.session_state.storico_chat = []
    st.rerun()

if allegati:
    for file in allegati:
        st.markdown(f"<span style='color: #FFD700;'>🔹 {file.name} caricato e pronto per l'analisi.</span>", unsafe_allow_html=True)

# --- REGISTRO CHAT ---
st.markdown("### 🖥️ Registro Chat Tattica")

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
        .chat-box table {
            display: block;
            width: 100%;
            overflow-x: auto;
        }
    </style>
""", unsafe_allow_html=True)

ultima_relazione = ""

if not st.session_state.storico_chat:
    st.markdown("<div class='chat-box'><span style='color: #00E676;'>Maresciallo AI: Pronto all'esame sul campo...</span></div>", unsafe_allow_html=True)
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

# --- FORM DI TRATTAMENTO QUESITO ---
st.markdown("---")
prompt = st.text_area("Quesito operativo / Note di verifica", placeholder="Inserisci le direttive d'esame o il quesito d'incrocio...")

if st.button("🚀 INVIA ATTO TATTICO", use_container_width=True):
    if not entry_key.strip():
        st.error("⚠️ Inserire prima una chiave API valida!")
    elif not prompt.strip():
        st.warning("⚠️ Il testo del quesito non Biochemical può essere vuoto.")
    else:
        with st.spinner("Analisi in corso ed incrocio flussi..."):
            try:
                client = genai.Client(api_key=entry_key.strip())
                
                immagini_parts = []
                testo_documenti_cumulato = ""
                
                if allegati:
                    for f in allegati:
                        est = f.name.split('.')[-1].lower()
                        if est in ['png', 'jpg', 'jpeg']:
                            immagini_parts.append(
                                types.Part.from_bytes(data=f.read(), mime_type=f"image/{est}")
                            )
                        elif est in ['pdf', 'docx', 'xlsx']:
                            testo_documenti_cumulato += estrai_testo_documento(f)

                sys_prompt = (
                    "Sei un Assistente Virtuale Avanzato per l'Analisi Economico-Finanziaria sul campo. "
                    "Mantieni intatti i dati reali di bilancio, codici fiscali e partite IVA. DIRETTIVA STRITTAMENTE IMPERATIVA: "
                    "Produci l'output in forma di relazione tecnica asettica e formale per gli ufficiali, senza preamboli o saluti. "
                    "REGOLA DI SINTESI: Se l'utente chiede tabelle o riepiloghi di dati massivi (es. libri giornali), aggrega i totali per fornitore "
                    "o per conto. È TASSATIVAMENTE VIETATO elencare singolarmente decine di righe od operazioni ripetitive. Genera direttamente "
                    "la tabella finale ordinata con i dati richiesti e rispondi in modo sintetico e definitivo."
                )

                contents = []
                for m in st.session_state.storico_chat:
                    contents.append(types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part.from_text(text=m["content"])]))
                
                prompt_completo = prompt
                if testo_documenti_cumulato:
                    prompt_completo += "\n\n" + testo_documenti_cumulato

                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt_completo)] + immagini_parts))

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