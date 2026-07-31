import streamlit as st
import pandas as pd
import datetime
import os
import io
import json
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from google import genai

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# --- CONFIGURAZIONE E SICUREZZA ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
PASSWORD_R4 = "Test"
PASSWORD_MEMBRI = "Member"
LOG_FILE = "access_log.txt"
CONFIG_FILE = "config_settimana.json"

ID_FOGLIO_DRIVE = "1igENI9rB2Lyqy8EUtnIWuWxwfRQZKyhCXpAnve3Wtrk"
FILE_CHIAVE_JSON = "chiave_drive.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "tipo_settimana": "SPINTA COMPLETA", "target_push_str": "100000000",
        "limite_save_str": "45000000", "target_tech_str": "10000",
        "tot_eventi_programmati": 5
    }

def save_config(config_dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, indent=4)

TEXTS = {
    "🇮🇹 🇮🇹 Italiano": {
        "welcome_title": "🇮🇹 Seleziona la Lingua", "welcome_btn": "Conferma e Continua",
        "title": "🛡️ Pannello di Controllo Alleanza", "login_title": "🔒 Accesso Gestionale Alleanza",
        "nick_label": "Nickname In-Game", "nick_placeholder": "Inserisci il tuo nick",
        "pass_label": "Password di Accesso", "login_btn": "Accedi", "logout_btn": "Logout",
        "sidebar_settings": "⚙️ Impostazioni Settimana", "sidebar_mode_lbl": "Modalità",
        "sidebar_limit_save": "Limite di Risparmio", "sidebar_target_tech": "Target Donazioni Tech",
        "sidebar_obj_vs": "Obiettivo VS Spinta", "sidebar_events_lbl": "Eventi Programmati",
        "sidebar_btn_edit_params": "⚙️ Modifica Parametri Settimanali", "sidebar_btn_edit_squads": "⚔️ Inserisci / Modifica mie Squadre",
        "sidebar_reset_title": "🚨 Reset Totale Software", "sidebar_reset_desc": "Attenzione: questo comando azzererà completamente il database su Google Drive.",
        "sidebar_reset_chk": "Confermo reset totale", "sidebar_reset_btn": "🔴 AZZERA TUTTO", "sidebar_reset_success": "✅ Software azzerato con successo!",
        "wizard_title": "🧙‍♂️ Configurazione Iniziale Settimanale", "wizard_subtitle": "Imposta i parametri tattici.",
        "strat_choice": "Strategia VS Settimanale", "opt_spinta": "SPINTA COMPLETA", "opt_risparmio": "RISPARMIA / PROFILO BASSO",
        "target_vs_push": "Obiettivo VS Spinta", "limite_save_txt": "Limite di Risparmio", "target_tech": "Target Donazioni Tech",
        "ev_planning_header": "📅 Pianificazione Eventi Settimanali:", "tot_ev_planned_lbl": "Totale Eventi di Gruppo Programmati",
        "confirm_config": "💾 Salva e Torna alla Dashboard", "tab_dati": "📊 Inserimento Punteggi (Prospetto Unificato)",
        "tab_classifica": "🏆 Classifica", "tab_regole": "📚 Regolamento", "tab_squadre": "⚔️ Potenza Squadre",
        "tab_crescita": "📈 Crescita Squadre", "tab_chat": "🤖 Assistente IA", "tab_log": "📜 Registro Log",
        "save_drive_btn": "💾 SALVA TUTTI I CAMBIAMENTI SU GOOGLE DRIVE", "calc_btn": "🧮 CALCOLA CLASSIFICA SETTIMANALE",
        "download_pdf_btn": "📄 SCARICA REPORT SETTIMANALE IN PDF", "squadre_header": "⚔️ Gestione Potenza delle 4 Squadre",
        "crescita_header": "📈 Analisi Percentuale di Crescita Mensile", "save_squadre_btn": "💾 SALVA SQUADRE DEL MESE",
        "export_xls_btn": "📊 SCARICA IN FORMATO EXCEL (.xlsx)", "export_pdf_btn": "📄 SCARICA IN FORMATO PDF (.pdf)",
        "success_drive": "✅ Connessione attiva al file su Google Drive!", "month_curr_label": "🗓️ Mese di Rilevazione Attuale",
        "month_prev_label": "🔍 Mese Precedente per Confronto", "month_edit_title": "📝 Inserimento / Modifica Potenza",
        "month_analysis_title": "📈 Crescita Registrata:", "ai_prompt_label": "Domanda per l'assistente tattico su Last War:",
        "ai_send_btn": "Invia Domanda Tattica", "btn_empty_log": "🗑️ Svuota Registro Log",
        "rule_goal_title": "🎯 L'Obiettivo della Formula", "rule_goal_desc": "La formula premia l'aderenza alle direttive.",
        "rule_vs_title": "1. ⚔️ Punteggio VS", "rule_vs_desc": "FULL PUSH o SAVE", "rule_ev_title": "2. 📅 Presenza agli Eventi",
        "rule_ev_desc": "Somma presenze", "rule_tech_title": "3. 🔬 Donazioni Tecnologiche", "rule_tech_desc": "Target tech",
        "rule_bonus_title": "4. ⭐ Bonus Stella", "rule_bonus_desc": "+3 punti per stella", "rule_pen_title": "5. 🛑 Penalità",
        "rule_pen_desc": "Scudo e assenze", "m_portal_title": "⚔️ Portale Aggiornamento Potenza", "m_connected_as": "Connesso come:",
        "m_member_role": "(Membro)", "m_month_info": "🗓️ Mese:", "m_format_info": "💡 In milioni (M).",
        "m_pending_warn": "⌛ In attesa di approvazione.", "m_approved_success": "✅ Approvato!", "m_not_submitted": "ℹ️ Non inviato.",
        "m_sq1_label": "Squadra 1", "m_sq2_label": "Squadra 2", "m_sq3_label": "Squadra 3", "m_sq4_label": "Squadra 4",
        "m_input_squad_power": "Potenza", "m_submit_btn": "💾 INVIA", "m_save_success_approval": "Inviato!",
        "m_save_success_direct": "Salvato!", "pending_requests_warn": "🚨 **Ci sono {count} richieste in attesa!**",
        "btn_approve": "✅ Approva", "btn_approve_all": "✅ Approva Tutto", "btn_reject": "❌ Rifiuta",
        "opt_yes": "si", "opt_no": "no", "tipo_squadra_opzioni": ["", "Carri", "Missili", "Aerei", "Mista"],
        "db_legend_text": "Inserisci i dati nei campi sottostanti. I totali verranno calcolati automaticamente nel prospetto classifica.",
        "col_n": "N.", "col_nickname": "Nickname", "col_punti_vs": "VS", "col_combattente": "Comb.",
        "col_eventi": "Eventi", "col_donazioni": "Tech", "col_premi": "Stelle", "col_pen_scudo": "Scudo",
        "col_assenza": "Ass.", "col_mancata_risp": "No R4", "col_inattivita": "Inattiv.",
        "col_punteggio_tot": "Punteggio Totale", "col_pot_tot": "Potenza Totale", "col_growth_tot": "Crescita Totale %"
    },
    "🇬🇧 🇬🇧 English": {
        "welcome_title": "🇬🇧 Select Language", "welcome_btn": "Confirm", "title": "🛡️ Alliance Control Panel", "login_title": "🔒 Login",
        "nick_label": "Nickname", "nick_placeholder": "Nick", "pass_label": "Password", "login_btn": "Login", "logout_btn": "Logout",
        "sidebar_settings": "⚙️ Settings", "sidebar_mode_lbl": "Mode", "sidebar_limit_save": "Save Limit", "sidebar_target_tech": "Tech Target",
        "sidebar_obj_vs": "VS Target", "sidebar_events_lbl": "Events", "sidebar_btn_edit_params": "⚙️ Edit", "sidebar_btn_edit_squads": "⚔️ Squads",
        "sidebar_reset_title": "🚨 Reset", "sidebar_reset_desc": "Reset DB", "sidebar_reset_chk": "Confirm", "sidebar_reset_btn": "RESET",
        "sidebar_reset_success": "Reset OK", "wizard_title": "Setup", "wizard_subtitle": "Setup", "strat_choice": "Strategy",
        "opt_spinta": "FULL PUSH", "opt_risparmio": "SAVE", "target_vs_push": "VS Target", "limite_save_txt": "Save Limit",
        "target_tech": "Tech Target", "ev_planning_header": "Events:", "tot_ev_planned_lbl": "Total Events", "confirm_config": "Save",
        "tab_dati": "📊 Scores Form", "tab_classifica": "🏆 Leaderboard", "tab_regole": "📚 Rules", "tab_squadre": "⚔️ Squads",
        "tab_crescita": "📈 Growth", "tab_chat": "🤖 AI", "tab_log": "📜 Log", "save_drive_btn": "💾 SAVE", "calc_btn": "🧮 CALCULATE",
        "download_pdf_btn": "📄 PDF", "squadre_header": "Squads", "crescita_header": "Growth", "save_squadre_btn": "💾 SAVE",
        "export_xls_btn": "📊 Excel", "export_pdf_btn": "📄 PDF", "success_drive": "Connected", "month_curr_label": "Month",
        "month_prev_label": "Prev", "month_edit_title": "Edit", "month_analysis_title": "Growth", "ai_prompt_label": "Ask",
        "ai_send_btn": "Send", "btn_empty_log": "Clear", "rule_goal_title": "Goal", "rule_goal_desc": "Desc", "rule_vs_title": "1. VS",
        "rule_vs_desc": "Desc", "rule_ev_title": "2. Events", "rule_ev_desc": "Desc", "rule_tech_title": "3. Tech", "rule_tech_desc": "Desc",
        "rule_bonus_title": "4. Star", "rule_bonus_desc": "Desc", "rule_pen_title": "5. Penalty", "rule_pen_desc": "Desc",
        "m_portal_title": "Portal", "m_connected_as": "Connected:", "m_member_role": "(Member)", "m_month_info": "Month:",
        "m_format_info": "Format", "m_pending_warn": "Pending", "m_approved_success": "Approved", "m_not_submitted": "Not submitted",
        "m_sq1_label": "Sq 1", "m_sq2_label": "Sq 2", "m_sq3_label": "Sq 3", "m_sq4_label": "Sq 4", "m_input_squad_power": "Power",
        "m_submit_btn": "SUBMIT", "m_save_success_approval": "OK", "m_save_success_direct": "OK", "pending_requests_warn": "Pending {count}",
        "btn_approve": "Approve", "btn_approve_all": "Approve All", "btn_reject": "Reject", "opt_yes": "yes", "opt_no": "no",
        "tipo_squadra_opzioni": ["", "Tanks", "Missiles", "Aircraft", "Mixed"], "db_legend_text": "Legend",
        "col_n": "N.", "col_nickname": "Nickname", "col_punti_vs": "VS", "col_combattente": "Fighter", "col_eventi": "Events",
        "col_donazioni": "Tech", "col_premi": "Stars", "col_pen_scudo": "Shield", "col_assenza": "Absence", "col_mancata_risp": "No R4",
        "col_inattivita": "Inactive", "col_punteggio_tot": "Total Score", "col_pot_tot": "Total Power", "col_growth_tot": "Total Growth %"
    },
    "🇩🇪 🇩🇪 Deutsch": {
        "welcome_title": "🇩🇪 Sprache auswählen", "welcome_btn": "Bestätigen", "title": "🛡️ Allianz-Kontrollzentrum", "login_title": "🔒 Anmeldung",
        "nick_label": "Nickname", "nick_placeholder": "Name", "pass_label": "Passwort", "login_btn": "Anmelden", "logout_btn": "Abmelden",
        "sidebar_settings": "⚙️ Einstellungen", "sidebar_mode_lbl": "Modus", "sidebar_limit_save": "Limit", "sidebar_target_tech": "Tech",
        "sidebar_obj_vs": "VS", "sidebar_events_lbl": "Events", "sidebar_btn_edit_params": "⚙️ Bearbeiten", "sidebar_btn_edit_squads": "⚔️ Truppen",
        "sidebar_reset_title": "🚨 Reset", "sidebar_reset_desc": "Reset", "sidebar_reset_chk": "Bestätigen", "sidebar_reset_btn": "RESET",
        "sidebar_reset_success": "OK", "wizard_title": "Setup", "wizard_subtitle": "Setup", "strat_choice": "Strategie",
        "opt_spinta": "FULL PUSH", "opt_risparmio": "SAVE", "target_vs_push": "VS Ziel", "limite_save_txt": "Limit",
        "target_tech": "Tech Ziel", "ev_planning_header": "Events:", "tot_ev_planned_lbl": "Events", "confirm_config": "Speichern",
        "tab_dati": "📊 Punkte Formular", "tab_classifica": "🏆 Rangliste", "tab_regole": "📚 Regeln", "tab_squadre": "⚔️ Truppen",
        "tab_crescita": "📈 Wachstum", "tab_chat": "🤖 KI", "tab_log": "📜 Log", "save_drive_btn": "💾 SPEICHERN", "calc_btn": "🧮 BERECHNEN",
        "download_pdf_btn": "📄 PDF", "squadre_header": "Truppen", "crescita_header": "Wachstum", "save_squadre_btn": "💾 SPEICHERN",
        "export_xls_btn": "📊 Excel", "export_pdf_btn": "📄 PDF", "success_drive": "Verbunden", "month_curr_label": "Monat",
        "month_prev_label": "Vormonat", "month_edit_title": "Bearbeiten", "month_analysis_title": "Wachstum", "ai_prompt_label": "Frage",
        "ai_send_btn": "Senden", "btn_empty_log": "Leeren", "rule_goal_title": "Ziel", "rule_goal_desc": "Desc", "rule_vs_title": "1. VS",
        "rule_vs_desc": "Desc", "rule_ev_title": "2. Events", "rule_ev_desc": "Desc", "rule_tech_title": "3. Tech", "rule_tech_desc": "Desc",
        "rule_bonus_title": "4. Sterne", "rule_bonus_desc": "Desc", "rule_pen_title": "5. Strafen", "rule_pen_desc": "Desc",
        "m_portal_title": "Portal", "m_connected_as": "Verbunden als:", "m_member_role": "(Mitglied)", "m_month_info": "Monat:",
        "m_format_info": "Format", "m_pending_warn": "Wartet", "m_approved_success": "Genehmigt", "m_not_submitted": "Nicht eingereicht",
        "m_sq1_label": "Truppe 1", "m_sq2_label": "Truppe 2", "m_sq3_label": "Truppe 3", "m_sq4_label": "Truppe 4", "m_input_squad_power": "Stärke",
        "m_submit_btn": "SENDEN", "m_save_success_approval": "OK", "m_save_success_direct": "OK", "pending_requests_warn": "Wartet {count}",
        "btn_approve": "Genehmigen", "btn_approve_all": "Alle genehmigen", "btn_reject": "Ablehnen", "opt_yes": "ja", "opt_no": "nein",
        "tipo_squadra_opzioni": ["", "Panzer", "Raketen", "Flieger", "Gemischt"], "db_legend_text": "Legende",
        "col_n": "Nr.", "col_nickname": "Nickname", "col_punti_vs": "VS", "col_combattente": "Kämpfer", "col_eventi": "Events",
        "col_donazioni": "Tech", "col_premi": "Sterne", "col_pen_scudo": "Schild", "col_assenza": "Abwes.",
        "col_mancata_risp": "Keine R4", "col_inattivita": "Inaktiv", "col_punteggio_tot": "Gesamtpunkte",
        "col_pot_tot": "Gesamtstärke", "col_growth_tot": "Gesamtwachstum %"
    }
}

MAPPA_TIPI_SQUADRA_ITA_EN = {"Carri": "Tanks", "Missili": "Missiles", "Aerei": "Aircraft", "Mista": "Mixed"}
MAPPA_TIPI_SQUADRA_ITA_DE = {"Carri": "Panzer", "Missili": "Raketen", "Aerei": "Flieger", "Mista": "Gemischt"}

def traduci_tipo_squadra(val_tipo, lang):
    if not val_tipo or pd.isna(val_tipo):
        return ""
    val_str = str(val_tipo).strip()
    if "English" in lang:
        return MAPPA_TIPI_SQUADRA_ITA_EN.get(val_str, val_str)
    elif "Deutsch" in lang:
        return MAPPA_TIPI_SQUADRA_ITA_DE.get(val_str, val_str)
    return val_str

def converti_in_numero_puro(val):
    if val is None or pd.isna(val):
        return 0
    val_str = str(val).upper().replace('M', '').replace('K', '').replace('.', '').replace(',', '').strip()
    digs = ''.join(filter(str.isdigit, val_str))
    try:
        return int(digs) if digs else 0
    except ValueError:
        return 0

def formatta_con_puntini(val):
    num = converti_in_numero_puro(val)
    if num == 0:
        return "0"
    return f"{num:,}".replace(",", ".")

def normalizza_valore_potenza(val_str):
    if val_str is None or pd.isna(val_str) or str(val_str).strip() == "" or str(val_str).strip() == "0":
        return "0M"
    val_clean = str(val_str).strip().upper()
    has_k = val_clean.endswith('K')
    val_num_str = val_clean.rstrip('MK').replace(',', '.')
    try:
        num = float(val_num_str)
        if np.isnan(num) or np.isinf(num):
            return "0M"
        if has_k:
            return f"{num:.1f}k".replace('.0k', 'k')
        else:
            return f"{num:.2f}M".replace('.00M', 'M')
    except ValueError:
        return "0M"

def parse_compact_number(val_str, default_val=0.0):
    return float(converti_in_numero_puro(val_str))

def format_compact_number(val):
    if val is None or np.isnan(val) or np.isinf(val):
        return "0.00M"
    if val >= 1_000_000:
        return f"{val / 1_000_000:.2f}M".replace('.00M', 'M')
    elif val >= 1_000:
        return f"{val / 1_000:.1f}k".replace('.0k', 'k')
    return f"{val:.2f}M"

def connetti_google_drive():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    cartella_script = os.path.dirname(os.path.abspath(__file__))
    percorso_chiave = os.path.join(cartella_script, FILE_CHIAVE_JSON)
    if os.path.exists(percorso_chiave):
        try:
            creds = Credentials.from_service_account_file(percorso_chiave, scopes=scopes)
            return gspread.authorize(creds)
        except Exception as e:
            st.error(f"❌ Errore caricamento file JSON: {e}")
            return None
    st.error(f"⚠️ Impossibile trovare il file '{FILE_CHIAVE_JSON}' nel percorso: {percorso_chiave}")
    return None

def pulisci_dataframe(df):
    if df is None:
        return pd.DataFrame()
    if df.empty:
        return df.copy()
    df_clean = df.replace({np.nan: "", None: ""}).copy()
    if len(df_clean.columns) > 0:
        col_nick = "Nickname" if "Nickname" in df_clean.columns else df_clean.columns[0]
        df_clean[col_nick] = df_clean[col_nick].astype(str).str.strip()
        df_clean = df_clean[(df_clean[col_nick] != "") & (df_clean[col_nick] != "0") & (df_clean[col_nick] != "nan") & (df_clean[col_nick] != "NAN")]
    return df_clean

def carica_dati_da_drive():
    try:
        client = connetti_google_drive()
        if client:
            sh = client.open_by_key(ID_FOGLIO_DRIVE)
            sheet = sh.get_worksheet(0)
            rows = sheet.get_all_values()
            if rows and len(rows) > 0:
                headers = rows[0]
                data = rows[1:]
                headers_univoci = []
                conteggio = {}
                for idx, h in enumerate(headers):
                    h_clean = h.strip() if h.strip() != "" else f"Colonna_{idx}"
                    if h_clean in conteggio:
                        conteggio[h_clean] += 1
                        headers_univoci.append(f"{h_clean}_{conteggio[h_clean]}")
                    else:
                        conteggio[h_clean] = 0
                        headers_univoci.append(h_clean)
                df = pd.DataFrame(data, columns=headers_univoci)
                df = pulisci_dataframe(df)

                if "Nickname" not in df.columns and len(df.columns) > 0:
                    df = df.rename(columns={df.columns[0]: "Nickname"})
                
                if "Nickname" in df.columns:
                    active_r4 = st.session_state.get("ruolo") == "R4" or st.session_state.get("ruolo_originale") == "R4"
                    current_user = st.session_state.get("nome_utente", "").strip().lower()
                    df["Nickname"] = df["Nickname"].apply(lambda x: f"🔴 {x}" if (active_r4 and str(x).replace("🔴 ", "").strip().lower() == current_user) else str(x).replace("🔴 ", ""))

                cols = list(df.columns)
                if "Nickname" in cols and "Punti_VS" in cols:
                    cols.remove("Punti_VS")
                    idx_nick = cols.index("Nickname")
                    cols.insert(idx_nick + 1, "Punti_VS")
                    df = df[cols]
                    
                col_n_str = TEXTS[list(TEXTS.keys())[0]]["col_n"]
                if col_n_str in df.columns:
                    df = df.drop(columns=[col_n_str])
                df.insert(0, col_n_str, range(1, len(df) + 1))
                    
                if "Eventi_Totali" not in df.columns:
                    df["Eventi_Totali"] = "0"

                colonne_richieste = ["Eventi_Totali", "Donazioni_Tech", "Premi_Stella", "Penalita_Scudo", "Assenza_Evento", "Mancata_Risposta_R4", "Giorni_Inattivita"]
                for c in colonne_richieste:
                    if c not in df.columns:
                        df[c] = "0" if c in ["Eventi_Totali", "Giorni_Inattivita", "Premi_Stella"] else ("no" if c != "Donazioni_Tech" else "10000")

                return df, sheet, sh
    except Exception as e:
        st.error(f"❌ Errore lettura Google Drive: {e}")
    return pd.DataFrame(columns=["N.", "Nickname", "Punti_VS", "Eventi_Totali"]), None, None

def salva_dati_su_drive(sheet, df):
    try:
        client_fresco = connetti_google_drive()
        if client_fresco:
            sh_fresco = client_fresco.open_by_key(ID_FOGLIO_DRIVE)
            sheet_fresco = sh_fresco.get_worksheet(0)
            
            df_pulito = df.copy()
            if "Nickname" in df_pulito.columns:
                df_pulito["Nickname"] = df_pulito["Nickname"].astype(str).str.replace("🔴 ", "").str.strip()

            for col_f in ["Punti_VS", "Donazioni_Tech", "Premi_Stella"]:
                if col_f in df_pulito.columns:
                    df_pulito[col_f] = df_pulito[col_f].apply(lambda x: str(converti_in_numero_puro(x)))

            for col_cand in ["N.", "N", "Colonna_0"]:
                if col_cand in df_pulito.columns:
                    df_pulito = df_pulito.drop(columns=[col_cand])
            df_clean = pulisci_dataframe(df_pulito)
            
            sheet_fresco.clear()
            valori = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
            sheet_fresco.update(range_name="A1", values=valori)
            st.cache_data.clear()
            return True
    except Exception as e:
        st.error(f"Errore salvataggio Google Drive: {e}")
    return False

def carica_squadre_da_drive(sh):
    try:
        sheet_squadre = sh.worksheet("Registro_Squadre")
        rows = sheet_squadre.get_all_values()
    except Exception:
        return pd.DataFrame(), None

    headers_base = ["Mese_Anno", "Nickname", "Tipo_Squadra_1", "Squadra_1", "Tipo_Squadra_2", "Squadra_2", "Tipo_Squadra_3", "Squadra_3", "Tipo_Squadra_4", "Squadra_4", "Stato_Approvazione"]
    if not rows or len(rows) == 0:
        return pd.DataFrame(columns=headers_base), sheet_squadre

    headers = [str(h).strip() for h in rows[0]]
    data = rows[1:]
    df = pd.DataFrame(data, columns=headers[:len(data[0])] if data and len(data) > 0 else headers)
    
    for col in headers_base:
        if col not in df.columns:
            df[col] = "Approvato" if col == "Stato_Approvazione" else (datetime.datetime.now().strftime("%Y-%m") if col == "Mese_Anno" else "")
            
    df = pulisci_dataframe(df)
    return df, sheet_squadre

def salva_squadre_su_drive(sheet_squadre, df):
    try:
        sheet_squadre.clear()
        df_clean = pulisci_dataframe(df)
        valori = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
        sheet_squadre.update(range_name="A1", values=valori)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio Registro Squadre: {e}")
    return False

def registra_log(utente, azione):
    ora_attuale = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ora_attuale}] Utente: {utente} | Azione: {azione}\n")

def svuota_log():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")

def calcola_punteggi_alleanza(df, config_dict):
    df = df.copy()
    tipo_settimana = config_dict.get("tipo_settimana", "SPINTA COMPLETA")
    
    target_push = parse_compact_number(config_dict.get("target_push_str", "100000000"), 100_000_000.0)
    limite_save = parse_compact_number(config_dict.get("limite_save_str", "45000000"), 45_000_000.0)
    target_tech = parse_compact_number(config_dict.get("target_tech_str", "10000"), 10_000.0)
    
    tot_ev_planned = config_dict.get("tot_eventi_programmati", 5)
    if tot_ev_planned <= 0:
        tot_ev_planned = 1

    colonne_default = {
        "Punti_VS": 0, "Combattente_Sabato": "no", "Eventi_Totali": 0, 
        "Donazioni_Tech": 0, "Premi_Stella": 0, "Penalita_Scudo": "no", 
        "Assenza_Evento": "no", "Mancata_Risposta_R4": "no", "Giorni_Inattivita": 0
    }
    for col, def_val in colonne_default.items():
        if col not in df.columns:
            df[col] = def_val

    punteggi_totali = []
    for _, row in df.iterrows():
        p_vs = parse_compact_number(row.get("Punti_VS", 0))
        combattente = str(row.get("Combattente_Sabato", "no")).lower() in ["true", "1", "si", "yes", "ja", "sì"]
        
        try:
            tot_eventi_presenze = float(str(row.get("Eventi_Totali", 0)).strip() or 0)
        except ValueError:
            tot_eventi_presenze = 0.0
            
        donazioni = parse_compact_number(row.get("Donazioni_Tech", 0))
        premi_stella = int(converti_in_numero_puro(row.get("Premi_Stella", 0)))
        
        penalita_scudo = str(row.get("Penalita_Scudo", "no")).lower() in ["true", "1", "si", "yes", "ja", "sì"]
        assenza_evento = str(row.get("Assenza_Evento", "no")).lower() in ["true", "1", "si", "yes", "ja", "sì"]
        mancata_risposta = str(row.get("Mancata_Risposta_R4", "no")).lower() in ["true", "1", "si", "yes", "ja", "sì"]
        
        try:
            giorni_inattivita = int(float(str(row.get("Giorni_Inattivita", 0)).strip() or 0))
        except ValueError:
            giorni_inattivita = 0

        if tipo_settimana in ["SPINTA COMPLETA", "FULL PUSH"]:
            s_vs = min(40.0, (p_vs / target_push) * 40.0) if target_push > 0 else 0.0
        else:
            if p_vs <= limite_save or combattente:
                s_vs = 40.0
            else:
                soglia_sforamento = limite_save * 0.5
                s_vs = max(0.0, 40.0 - ((p_vs - limite_save) / soglia_sforamento) * 20.0)

        s_eventi = min(30.0, (tot_eventi_presenze / tot_ev_planned) * 30.0)
        s_tech = min(20.0, (donazioni / target_tech) * 20.0) if target_tech > 0 else 0.0
        b_stella = premi_stella * 3.0
        
        malus_inattivita = max(0, (giorni_inattivita - 3) * 5.0) if giorni_inattivita > 3 else 0.0
        penalita = (30.0 if penalita_scudo else 0.0) + (15.0 if assenza_evento else 0.0) + (10.0 if mancata_risposta else 0.0) + malus_inattivita
        
        punteggio_finale = s_vs + s_eventi + s_tech + b_stella - penalita
        punteggi_totali.append(round(max(0.0, punteggio_finale), 2))

    df["Punteggio_Totale"] = punteggi_totali
    return df

def genera_report_pdf(df, tipo_settimana):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor("#1A365D"), spaceAfter=12, alignment=1)
    subtitle_style = ParagraphStyle('DocSubTitle', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor("#4A5568"), spaceAfter=20, alignment=1)
    
    story.append(Paragraph("🛡️ REPORT SETTIMANALE ALLEANZA", title_style))
    story.append(Paragraph(f"Data: {datetime.datetime.now().strftime('%d/%m/%Y')} | Modalità: <b>{tipo_settimana}</b>", subtitle_style))
    story.append(Spacer(1, 10))
    
    df_sorted = df.sort_values(by="Punteggio_Totale", ascending=False)
    col_nome = "Nickname" if "Nickname" in df_sorted.columns else df_sorted.columns[0]
    table_data = [["N.", "Pos", "Giocatore", "Punti VS", "Donazioni", "Premi", "Punteggio Totale"]]
    for pos, (_, row) in enumerate(df_sorted.iterrows(), start=1):
        clean_nick = str(row[col_nome]).replace("🔴 ", "")
        table_data.append([
            str(pos), str(pos), clean_nick,
            formatta_con_puntini(row.get('Punti_VS', 0)),
            formatta_con_puntini(row.get('Donazioni_Tech', 0)),
            str(converti_in_numero_puro(row.get('Premi_Stella', 0))),
            f"{row.get('Punteggio_Totale', 0):.2f}"
        ])
        
    t = Table(table_data, colWidths=[25, 35, 120, 90, 75, 45, 95])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#EDF2F7")]),
    ]))
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer

def genera_pdf_squadre(df_squadre, mese_cur, mese_cmp=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#1A365D"), spaceAfter=10, alignment=1)
    subtitle_style = ParagraphStyle('DocSubTitle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#4A5568"), spaceAfter=15, alignment=1)
    
    if mese_cmp:
        story.append(Paragraph("⚔️ REPORT CRESCITA POTENZA SQUADRE", title_style))
        story.append(Paragraph(f"Mese: <b>{mese_cur}</b> | Confronto: <b>{mese_cmp}</b>", subtitle_style))
    else:
        story.append(Paragraph("⚔️ REPORT POTENZA SQUADRE", title_style))
        story.append(Paragraph(f"Mese: <b>{mese_cur}</b>", subtitle_style))
        
    story.append(Spacer(1, 5))
    df_pdf = df_squadre.copy()
    if "Nickname" in df_pdf.columns:
        df_pdf["Nickname"] = df_pdf["Nickname"].astype(str).str.replace("🔴 ", "").str.strip()

    cols = list(df_pdf.columns)
    table_data = [cols]
    for _, row in df_pdf.iterrows():
        table_data.append([str(row.get(c, '')) for c in cols])
        
    col_width = max(28, min(60, int(750 / max(1, len(cols)))))
    t = Table(table_data, colWidths=[col_width]*len(cols))
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#EDF2F7")]),
    ]))
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer

if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
if "ruolo" not in st.session_state:
    st.session_state.ruolo = None
if "lang" not in st.session_state:
    st.session_state.lang = None
if "config_settimana" not in st.session_state:
    st.session_state.config_settimana = load_config()

st.set_page_config(page_title="Gestionale Last War Alleanza", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    @keyframes slideInFromLeft {
        0% { transform: translateX(-100%); opacity: 0; }
        100% { transform: translateX(0); opacity: 1; }
    }
    .welcome-banner {
        animation: 1s ease-out 0s 1 slideInFromLeft;
        font-size: 32px;
        font-weight: 800;
        color: #1A365D;
        text-align: center;
        margin-bottom: 25px;
        background: linear-gradient(90deg, #E2E8F0 0%, #EDF2F7 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 6px solid #2B6CB0;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.05);
    }
    h1 {
        font-size: 24px !important;
        color: #1A365D !important;
        font-weight: 700 !important;
        padding-bottom: 5px !important;
        border-bottom: 2px solid #CBD5E0;
        margin-bottom: 20px !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #EDF2F7;
        padding: 8px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #FFFFFF;
        border-radius: 6px;
        padding: 0px 16px;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #CBD5E0;
    }
    .stTabs [data-baseweb="tab"] [data-testid="stMarkdownContainer"] p {
        font-size: 15px !important;
        font-weight: 700 !important;
        color: #2B6CB0 !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2B6CB0 !important;
        border: 1px solid #1A365D !important;
    }
    .stTabs [aria-selected="true"] [data-testid="stMarkdownContainer"] p {
        color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

if st.session_state.lang is None:
    st.markdown('<div class="welcome-banner">⚔️ WELCOME TO LAST WAR PROJECT ⚔️</div>', unsafe_allow_html=True)
    col_w1, col_w2, col_w3 = st.columns([1, 2, 1])
    with col_w2:
        scelta_lingua = st.selectbox(
            "🌐 Seleziona la lingua / Select Language / Sprache auswählen",
            ["🇮🇹 🇮🇹 Italiano", "🇬🇧 🇬🇧 English", "🇩🇪 🇩🇪 Deutsch"]
        )
        st.markdown("")
        if st.button("Conferma / Confirm / Bestätigen", type="primary", width="stretch"):
            st.session_state.lang = scelta_lingua
            st.rerun()
    st.stop()

T = TEXTS[st.session_state.lang]
OPZIONI_TIPO_SQUADRA = T["tipo_squadra_opzioni"]

if not st.session_state.autenticato:
    st.title(T["login_title"])
    col1, _ = st.columns([1, 1])
    with col1:
        nome_utente = st.text_input(T["nick_label"], placeholder=T["nick_placeholder"])
        password_inserita = st.text_input(T["pass_label"], type="password")
        if st.button(T["login_btn"], type="primary"):
            if nome_utente.strip() != "":
                if password_inserita == PASSWORD_R4:
                    st.session_state.autenticato = True
                    st.session_state.ruolo = "R4"
                    st.session_state.nome_utente = nome_utente.strip()
                    registra_log(st.session_state.nome_utente, "Login R4")
                    st.rerun()
                elif password_inserita == PASSWORD_MEMBRI:
                    st.session_state.autenticato = True
                    st.session_state.ruolo = "Membro"
                    st.session_state.nome_utente = nome_utente.strip()
                    registra_log(st.session_state.nome_utente, "Login Membro")
                    st.rerun()
                else:
                    st.error("Password errata.")
            else:
                st.warning("⚠️ Inserisci il nickname.")
    st.stop()

spreadsheet_obj = connetti_google_drive().open_by_key(ID_FOGLIO_DRIVE) if connetti_google_drive() else None

if st.session_state.ruolo == "Membro":
    is_r4_origin = (st.session_state.get("ruolo_originale") == "R4")
    st.title(f"{T['m_portal_title']} - {'Ufficiale (R4)' if is_r4_origin else 'Player'}: {st.session_state.nome_utente}")
    with st.sidebar:
        st.write(f"{T['m_connected_as']} **{st.session_state.nome_utente}** {'(R4)' if is_r4_origin else T['m_member_role']}")
        if is_r4_origin:
            if st.button("🔙 Torna al Pannello Ufficiali R4"):
                st.session_state.ruolo = "R4"
                del st.session_state["ruolo_originale"]
                st.rerun()
        if st.button(T["logout_btn"]):
            st.session_state.autenticato = False
            st.session_state.ruolo = None
            st.session_state.lang = None
            if "ruolo_originale" in st.session_state:
                del st.session_state["ruolo_originale"]
            st.rerun()

    if spreadsheet_obj:
        df_squadre, sheet_squadre_obj = carica_squadre_da_drive(spreadsheet_obj)
        mese_attuale_def = datetime.datetime.now().strftime("%Y-%m")
        st.info(f"{T['m_month_info']} **{mese_attuale_def}**")
        st.write(T['m_format_info'])
        nick_user = st.session_state.nome_utente.strip()
        
        df_squadre["Nickname_Clean"] = df_squadre["Nickname"].astype(str).str.replace("🔴 ", "").str.strip().str.lower()
        df_user_row = df_squadre[(df_squadre["Mese_Anno"] == mese_attuale_def) & (df_squadre["Nickname_Clean"] == nick_user.lower())]
        
        if not df_user_row.empty:
            t1_val = df_user_row.iloc[0].get("Tipo_Squadra_1", None)
            s1_val = df_user_row.iloc[0].get("Squadra_1", "0M")
            t2_val = df_user_row.iloc[0].get("Tipo_Squadra_2", None)
            s2_val = df_user_row.iloc[0].get("Squadra_2", "0M")
            t3_val = df_user_row.iloc[0].get("Tipo_Squadra_3", None)
            s3_val = df_user_row.iloc[0].get("Squadra_3", "0M")
            t4_val = df_user_row.iloc[0].get("Tipo_Squadra_4", None)
            s4_val = df_user_row.iloc[0].get("Squadra_4", "0M")
            stato_att = df_user_row.iloc[0].get("Stato_Approvazione", "Approvato")
            has_submitted = True
        else:
            t1_val = t2_val = t3_val = t4_val = None
            s1_val = s2_val = s3_val = s4_val = "0M"
            stato_att = None
            has_submitted = False
            
        with st.form("form_potenza_membro"):
            col_s1, col_s2 = st.columns(2)
            lbl_potenza = T["m_input_squad_power"]
            with col_s1:
                idx_t1 = OPZIONI_TIPO_SQUADRA.index(t1_val) if t1_val in OPZIONI_TIPO_SQUADRA else 0
                in_t1 = st.selectbox(T['m_sq1_label'], OPZIONI_TIPO_SQUADRA, index=idx_t1)
                in_s1 = st.text_input(f"{lbl_potenza} 1", value=str(s1_val))
                st.markdown("---")
                idx_t2 = OPZIONI_TIPO_SQUADRA.index(t2_val) if t2_val in OPZIONI_TIPO_SQUADRA else 0
                in_t2 = st.selectbox(T['m_sq2_label'], OPZIONI_TIPO_SQUADRA, index=idx_t2)
                in_s2 = st.text_input(f"{lbl_potenza} 2", value=str(s2_val))
            with col_s2:
                idx_t3 = OPZIONI_TIPO_SQUADRA.index(t3_val) if t3_val in OPZIONI_TIPO_SQUADRA else 0
                in_t3 = st.selectbox(T['m_sq3_label'], OPZIONI_TIPO_SQUADRA, index=idx_t3)
                in_s3 = st.text_input(f"{lbl_potenza} 3", value=str(s3_val))
                st.markdown("---")
                idx_t4 = OPZIONI_TIPO_SQUADRA.index(t4_val) if t4_val in OPZIONI_TIPO_SQUADRA else 0
                in_t4 = st.selectbox(T['m_sq4_label'], OPZIONI_TIPO_SQUADRA, index=idx_t4)
                in_s4 = st.text_input(f"{lbl_potenza} 4", value=str(s4_val))
                
            tipi_inseriti = [t for t in [in_t1, in_t2, in_t3, in_t4] if t and t != ""]
            duplicati_presenti = len(tipi_inseriti) != len(set(tipi_inseriti))

            conferma_anomalia = False
            if duplicati_presenti:
                st.markdown("---")
                st.error("⚠️ **ATTENZIONE:** Hai inserito due o più squadre dello stesso tipo!")
                conferma_anomalia = st.checkbox("Confermo di voler procedere nonostante l'anomalia di tipo duplicato")

            btn_salva_membro = st.form_submit_button(T['m_submit_btn'], type="primary", width="stretch")
            
        if btn_salva_membro:
            if duplicati_presenti and not conferma_anomalia:
                st.error("🚫 Invio bloccato: spunta la casella di conferma.")
                st.stop()

            stato_richiesta = "Approvato" if is_r4_origin else ("In Attesa (⚠️ Duplicati)" if duplicati_presenti else "In Attesa")
            norm_s1 = normalizza_valore_potenza(in_s1)
            norm_s2 = normalizza_valore_potenza(in_s2)
            norm_s3 = normalizza_valore_potenza(in_s3)
            norm_s4 = normalizza_valore_potenza(in_s4)
            
            if "Nickname_Clean" in df_squadre.columns:
                df_squadre = df_squadre.drop(columns=["Nickname_Clean"])
            
            df_squadre["Nick_Cmp"] = df_squadre["Nickname"].astype(str).str.replace("🔴 ", "").str.strip().str.lower()
            maschera = (df_squadre["Mese_Anno"] == mese_attuale_def) & (df_squadre["Nick_Cmp"] == nick_user.lower())
            if "Nick_Cmp" in df_squadre.columns:
                df_squadre = df_squadre.drop(columns=["Nick_Cmp"])

            if df_squadre[maschera].shape[0] > 0:
                df_squadre.loc[maschera, "Tipo_Squadra_1"] = in_t1
                df_squadre.loc[maschera, "Squadra_1"] = norm_s1
                df_squadre.loc[maschera, "Tipo_Squadra_2"] = in_t2
                df_squadre.loc[maschera, "Squadra_2"] = norm_s2
                df_squadre.loc[maschera, "Tipo_Squadra_3"] = in_t3
                df_squadre.loc[maschera, "Squadra_3"] = norm_s3
                df_squadre.loc[maschera, "Tipo_Squadra_4"] = in_t4
                df_squadre.loc[maschera, "Squadra_4"] = norm_s4
                df_squadre.loc[maschera, "Stato_Approvazione"] = stato_richiesta
                df_squadre_agg = df_squadre
            else:
                nuova_riga = pd.DataFrame([{
                    "Mese_Anno": mese_attuale_def, "Nickname": nick_user,
                    "Tipo_Squadra_1": in_t1, "Squadra_1": norm_s1, "Tipo_Squadra_2": in_t2, "Squadra_2": norm_s2,
                    "Tipo_Squadra_3": in_t3, "Squadra_3": norm_s3, "Tipo_Squadra_4": in_t4, "Squadra_4": norm_s4,
                    "Stato_Approvazione": stato_richiesta
                }])
                df_squadre_agg = pd.concat([df_squadre, nuova_riga], ignore_index=True)
            
            if salva_squadre_su_drive(sheet_squadre_obj, df_squadre_agg):
                st.success("Squadre salvate con successo!")
                st.stop()
    st.stop()

st.title(f"{T['title']} - Ufficiale: {st.session_state.nome_utente}")
is_admin = (st.session_state.get("nome_utente", "").lower().strip() == "rickygra72")

oggi = datetime.datetime.now()
is_lunedi = (oggi.weekday() == 0 and oggi.hour == 4) or st.session_state.get("forza_wizard_modifica", False)

if is_lunedi:
    st.markdown("---")
    st.subheader(T["wizard_title"])
    st.info(T["wizard_subtitle"])
    with st.form("form_wizard_mod"):
        cfg_old = st.session_state.config_settimana
        w_tipo = st.radio(T["strat_choice"], [T["opt_spinta"], T["opt_risparmio"]], index=0 if cfg_old["tipo_settimana"]==T["opt_spinta"] else 1)
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            w_target_vs = st.text_input(T["target_vs_push"], value=cfg_old["target_push_str"])
            w_limite_vs = st.text_input(T["limite_save_txt"], value=cfg_old["limite_save_str"])
            w_target_tech = st.text_input(T["target_tech"], value=cfg_old["target_tech_str"])
        with col_w2:
            st.markdown(f"**{T['ev_planning_header']}**")
            w_tot_ev = st.number_input(T["tot_ev_planned_lbl"], value=cfg_old.get("tot_eventi_programmati", 5), min_value=1)
            
        c_salva, c_chiudi = st.columns(2)
        with c_salva:
            btn_salva_wiz = st.form_submit_button(T["confirm_config"], type="primary")
        with c_chiudi:
            btn_chiudi_wiz = st.form_submit_button("❌ Chiudi")
            
        if btn_salva_wiz:
            new_config = {
                "tipo_settimana": w_tipo, 
                "target_push_str": str(converti_in_numero_puro(w_target_vs)),
                "limite_save_str": str(converti_in_numero_puro(w_limite_vs)), 
                "target_tech_str": str(converti_in_numero_puro(w_target_tech)),
                "tot_eventi_programmati": w_tot_ev
            }
            st.session_state.config_settimana = new_config
            save_config(new_config)
            st.session_state.forza_wizard_modifica = False
            st.success("🎉 Parametri salvati con successo!")
            st.rerun()
        if btn_chiudi_wiz:
            st.session_state.forza_wizard_modifica = False
            st.rerun()
    st.stop()

with st.sidebar:
    st.header(T["sidebar_settings"])
    cfg_attiva = st.session_state.get("config_settimana")
    is_push_mode = cfg_attiva['tipo_settimana'] in ["SPINTA COMPLETA", "FULL PUSH"]
    tot_ev_correnti = cfg_attiva.get("tot_eventi_programmati", 5)

    if is_push_mode:
        st.markdown(f"**{T['sidebar_mode_lbl']}:** {cfg_attiva['tipo_settimana']}  \n**{T['sidebar_obj_vs']}:** {cfg_attiva['target_push_str']}  \n**{T['sidebar_target_tech']}:** {cfg_attiva['target_tech_str']}  \n**{T['sidebar_events_lbl']}:** 📅 {tot_ev_correnti}")
    else:
        st.markdown(f"**{T['sidebar_mode_lbl']}:** {cfg_attiva['tipo_settimana']}  \n**{T['sidebar_limit_save']}:** {cfg_attiva['limite_save_str']}  \n**{T['sidebar_target_tech']}:** {cfg_attiva['target_tech_str']}  \n**{T['sidebar_events_lbl']}:** 📅 {tot_ev_correnti}")

    if st.button(T["sidebar_btn_edit_params"]):
        st.session_state.forza_wizard_modifica = True
        st.rerun()

    st.markdown("---")
    if st.button(T["sidebar_btn_edit_squads"]):
        st.session_state.ruolo_originale = "R4"
        st.session_state.ruolo = "Membro"
        st.rerun()

    st.markdown("---")
    with st.expander(T["sidebar_reset_title"]):
        st.warning(T["sidebar_reset_desc"])
        conferma_reset_totale = st.checkbox(T["sidebar_reset_chk"], key="chk_reset_totale_sb")
        if st.button(T["sidebar_reset_btn"], type="primary", width="stretch"):
            if conferma_reset_totale:
                try:
                    client_res = connetti_google_drive()
                    if client_res:
                        sh_res = client_res.open_by_key(ID_FOGLIO_DRIVE)
                        try:
                            sheet_sq = sh_res.worksheet("Registro_Squadre")
                            sheet_sq.clear()
                            sheet_sq.update(range_name="A1", values=[["Mese_Anno", "Nickname", "Tipo_Squadra_1", "Squadra_1", "Tipo_Squadra_2", "Squadra_2", "Tipo_Squadra_3", "Squadra_3", "Tipo_Squadra_4", "Squadra_4", "Stato_Approvazione"]])
                        except Exception:
                            pass
                        sheet_punti = sh_res.get_worksheet(0)
                        sheet_punti.clear()
                        sheet_punti.update(range_name="A1", values=[["N.", "Nickname", "Punti_VS", "Combattente_Sabato", "Eventi_Totali", "Donazioni_Tech", "Premi_Stella", "Penalita_Scudo", "Assenza_Evento", "Mancata_Risposta_R4", "Giorni_Inattivita"]])
                        st.success(T["sidebar_reset_success"])
                        st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

    st.markdown("---")
    if st.button(T["logout_btn"]):
        st.session_state.autenticato = False
        st.session_state.ruolo = None
        st.session_state.lang = None
        st.rerun()

elenco_tabs = [T["tab_squadre"], T["tab_crescita"], T["tab_dati"], T["tab_classifica"], T["tab_chat"], T["tab_regole"]]
if is_admin:
    elenco_tabs.append(T["tab_log"])

tabs = st.tabs(elenco_tabs)
tab_squadre, tab_crescita, tab_dati, tab_report, tab_chat, tab_regole = tabs[0], tabs[1], tabs[2], tabs[3], tabs[4], tabs[5]
tab_log = tabs[6] if is_admin else None

with tab_squadre:
    st.subheader(T["squadre_header"])
    if spreadsheet_obj:
        df_drive_attivo, sheet_obj_punti, _ = carica_dati_da_drive()
        df_squadre, sheet_squadre_obj = carica_squadre_da_drive(spreadsheet_obj)
        
        if df_squadre is not None and df_drive_attivo is not None:
            if "Stato_Approvazione" not in df_squadre.columns:
                df_squadre["Stato_Approvazione"] = "Approvato"

            df_in_attesa = df_squadre[df_squadre["Stato_Approvazione"].astype(str).str.contains("In Attesa")].copy()
            if not df_in_attesa.empty:
                st.warning(T["pending_requests_warn"].format(count=len(df_in_attesa)))
                if st.button(T["btn_approve_all"], type="primary"):
                    for idx_att in df_in_attesa.index:
                        df_squadre.loc[idx_att, "Stato_Approvazione"] = "Approvato"
                    salva_squadre_su_drive(sheet_squadre_obj, df_squadre)
                    st.success("🎉 Tutte le richieste approvate!")
                    st.rerun()

            mesi_anno = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"]
            mese_attuale_def = datetime.datetime.now().strftime("%Y-%m")
            mese_selezionato_sq = st.selectbox(T["month_curr_label"], mesi_anno, index=mesi_anno.index(mese_attuale_def) if mese_attuale_def in mesi_anno else 6, key="sel_mese_potenza")

            df_mese_curr = df_squadre[df_squadre["Mese_Anno"] == mese_selezionato_sq].copy()
            cols_to_edit = ["Nickname", "Tipo_Squadra_1", "Squadra_1", "Tipo_Squadra_2", "Squadra_2", "Tipo_Squadra_3", "Squadra_3", "Tipo_Squadra_4", "Squadra_4"]
            for c in cols_to_edit:
                if c not in df_mese_curr.columns:
                    df_mese_curr[c] = "" if "Tipo" in c else ""

            df_mese_curr.insert(0, T["col_n"], range(1, len(df_mese_curr) + 1))
            column_config_sq = {
                T["col_n"]: st.column_config.NumberColumn(T["col_n"], width="small", disabled=True),
                "Nickname": st.column_config.TextColumn(T["col_nickname"], width="medium", required=True),
                "Tipo_Squadra_1": st.column_config.SelectboxColumn("Tipo Sq1", options=OPZIONI_TIPO_SQUADRA, width="small"),
                "Squadra_1": st.column_config.TextColumn("Potenza Sq1", width="small"),
                "Tipo_Squadra_2": st.column_config.SelectboxColumn("Tipo Sq2", options=OPZIONI_TIPO_SQUADRA, width="small"),
                "Squadra_2": st.column_config.TextColumn("Potenza Sq2", width="small"),
                "Tipo_Squadra_3": st.column_config.SelectboxColumn("Tipo Sq3", options=OPZIONI_TIPO_SQUADRA, width="small"),
                "Squadra_3": st.column_config.TextColumn("Potenza Sq3", width="small"),
                "Tipo_Squadra_4": st.column_config.SelectboxColumn("Tipo Sq4", options=OPZIONI_TIPO_SQUADRA, width="small"),
                "Squadra_4": st.column_config.TextColumn("Potenza Sq4", width="small"),
            }

            df_squadre_edit = st.data_editor(df_mese_curr, column_config=column_config_sq, num_rows="dynamic", width="stretch", key="editor_squadre")
            if st.button(T["save_squadre_btn"], type="primary"):
                df_pulita_edit = df_squadre_edit.copy()
                if T["col_n"] in df_pulita_edit.columns:
                    df_pulita_edit = df_pulita_edit.drop(columns=[T["col_n"]])
                df_pulita_edit["Mese_Anno"] = mese_selezionato_sq
                df_pulita_edit["Stato_Approvazione"] = "Approvato"
                
                for sq_col in ["Squadra_1", "Squadra_2", "Squadra_3", "Squadra_4"]:
                    if sq_col in df_pulita_edit.columns:
                        df_pulita_edit[sq_col] = df_pulita_edit[sq_col].apply(normalizza_valore_potenza)

                df_squadre_agg = df_squadre[df_squadre["Mese_Anno"] != mese_selezionato_sq].copy() if not df_squadre.empty else pd.DataFrame()
                df_squadre_agg = pd.concat([df_squadre_agg, df_pulita_edit], ignore_index=True)
                if salva_squadre_su_drive(sheet_squadre_obj, df_squadre_agg):
                    st.success("🎉 Salvato con successo!")
                    st.rerun()

with tab_crescita:
    st.subheader(T["crescita_header"])
    if spreadsheet_obj:
        df_squadre, _ = carica_squadre_da_drive(spreadsheet_obj)
        if df_squadre is not None and not df_squadre.empty:
            mesi_anno = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"]
            mese_attuale_def = datetime.datetime.now().strftime("%Y-%m")
            col_cr1, col_cr2 = st.columns(2)
            with col_cr1:
                mese_selezionato_cr = st.selectbox(T["month_curr_label"], mesi_anno, index=mesi_anno.index(mese_attuale_def) if mese_attuale_def in mesi_anno else 6, key="sel_mese_cr")
            with col_cr2:
                idx_prev_cr = mesi_anno.index(mese_selezionato_cr) - 1 if mese_selezionato_cr in mesi_anno and mesi_anno.index(mese_selezionato_cr) > 0 else 0
                mese_confronto_cr = st.selectbox(T["month_prev_label"], mesi_anno, index=idx_prev_cr, key="sel_mese_cmp_cr")

            df_curr = df_squadre[df_squadre["Mese_Anno"] == mese_selezionato_cr].copy()
            df_prev = df_squadre[df_squadre["Mese_Anno"] == mese_confronto_cr].copy()
            if not df_curr.empty:
                risultati_crescita = []
                for _, row_c in df_curr.iterrows():
                    if str(row_c.get("Stato_Approvazione", "Approvato")).strip() != "Approvato":
                        continue
                    nick = str(row_c.get("Nickname", ""))
                    squadre_attuali = []
                    tot_c = 0.0
                    for i in range(1, 5):
                        t_tipo_raw = str(row_c.get(f"Tipo_Squadra_{i}", "")).strip()
                        t_tipo = traduci_tipo_squadra(t_tipo_raw, st.session_state.lang)
                        p_val = parse_compact_number(row_c.get(f"Squadra_{i}", 0))
                        tot_c += p_val
                        if t_tipo:
                            squadre_attuali.append({"tipo": t_tipo, "tipo_key": t_tipo_raw.lower(), "potenza": p_val})

                    mappa_prec = {}
                    tot_p = 0.0
                    clean_nick_cmp = nick.replace("🔴 ", "").strip().lower()
                    row_p = df_prev[df_prev["Nickname"].astype(str).str.replace("🔴 ", "").str.strip().str.lower() == clean_nick_cmp] if not df_prev.empty else pd.DataFrame()
                    if not row_p.empty:
                        r_p = row_p.iloc[0]
                        for i in range(1, 5):
                            tp_tipo_raw = str(r_p.get(f"Tipo_Squadra_{i}", "")).strip().lower()
                            pp_val = parse_compact_number(r_p.get(f"Squadra_{i}", 0))
                            tot_p += pp_val
                            if tp_tipo_raw:
                                mappa_prec[tp_tipo_raw] = pp_val

                    g_tot = ((tot_c - tot_p) / tot_p * 100.0) if tot_p > 0 else 0.0
                    riga_player = {T["col_nickname"]: nick}
                    for sq in squadre_attuali:
                        col_nome_sq = sq["tipo"]
                        col_nome_perc = f"% crescita {col_nome_sq}"
                        pot_curr = sq["potenza"]
                        t_key = sq["tipo_key"]
                        if t_key in mappa_prec and mappa_prec[t_key] > 0:
                            crescita = ((pot_curr - mappa_prec[t_key]) / mappa_prec[t_key]) * 100.0
                            riga_player[col_nome_sq] = format_compact_number(pot_curr)
                            riga_player[col_nome_perc] = f"{crescita:+.1f}%"
                        else:
                            riga_player[col_nome_sq] = format_compact_number(pot_curr)
                            riga_player[col_nome_perc] = "N/D"

                    riga_player[T["col_pot_tot"]] = format_compact_number(tot_c)
                    riga_player[T["col_growth_tot"]] = f"{g_tot:+.1f}%" if tot_p > 0 else "N/D"
                    riga_player["Valore_Totale_Num"] = tot_c
                    risultati_crescita.append(riga_player)

                if risultati_crescita:
                    df_risultati = pd.DataFrame(risultati_crescita).sort_values(by="Valore_Totale_Num", ascending=False)
                    df_visibile = df_risultati.drop(columns=["Valore_Totale_Num"])
                    df_visibile.insert(0, T["col_n"], range(1, len(df_visibile) + 1))
                    st.dataframe(df_visibile, width="stretch")

# ==============================================================================
# 3. TAB DATI GOOGLE DRIVE (FORM NATIVA ANTIBUG)
# ==============================================================================
with tab_dati:
    st.subheader("📊 Inserimento Punteggi (Modulo Sicuro)")
    df_drive, sheet_obj, spreadsheet_obj = carica_dati_da_drive()
    if df_drive is not None:
        st.success(T["success_drive"])
        st.markdown(T["db_legend_text"])
        st.markdown("---")

        with st.form("form_inserimento_sicuro"):
            nuovi_dati = []
            
            for idx, row in df_drive.iterrows():
                nick = str(row.get("Nickname", ""))
                st.markdown(f"#### 👤 {nick}")
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    vs_val_pulito = str(converti_in_numero_puro(row.get("Punti_VS", 0)))
                    if vs_val_pulito == "0": vs_val_pulito = ""
                    inp_vs = st.text_input(f"Punti VS ({nick})", value=vs_val_pulito, key=f"vs_form_{idx}")
                with c2:
                    tech_val_pulito = str(converti_in_numero_puro(row.get("Donazioni_Tech", 0)))
                    if tech_val_pulito == "0": tech_val_pulito = ""
                    inp_tech = st.text_input(f"Donazioni Tech ({nick})", value=tech_val_pulito, key=f"tech_form_{idx}")
                with c3:
                    st_val = int(converti_in_numero_puro(row.get("Premi_Stella", 0)))
                    if st_val > 5: st_val = 5
                    inp_stella = st.selectbox(f"Premi Stella ({nick})", options=[0, 1, 2, 3, 4, 5], index=st_val, key=f"stella_form_{idx}")
                with c4:
                    opt_ev = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
                    curr_ev = str(row.get("Eventi_Totali", "0"))
                    idx_ev = opt_ev.index(curr_ev) if curr_ev in opt_ev else 0
                    inp_eventi = st.selectbox(f"Eventi Totali ({nick})", options=opt_ev, index=idx_ev, key=f"ev_form_{idx}")

                c5, c6, c7, c8 = st.columns(4)
                with c5:
                    opt_yn = ["no", "si"]
                    curr_comb = str(row.get("Combattente_Sabato", "no")).lower()
                    idx_comb = opt_yn.index(curr_comb) if curr_comb in opt_yn else 0
                    inp_comb = st.selectbox(f"Combattente Sabato ({nick})", options=opt_yn, index=idx_comb, key=f"comb_form_{idx}")
                with c6:
                    curr_scudo = str(row.get("Penalita_Scudo", "no")).lower()
                    idx_scudo = opt_yn.index(curr_scudo) if curr_scudo in opt_yn else 0
                    inp_scudo = st.selectbox(f"Penalità Scudo ({nick})", options=opt_yn, index=idx_scudo, key=f"scudo_form_{idx}")
                with c7:
                    curr_ass = str(row.get("Assenza_Evento", "no")).lower()
                    idx_ass = opt_yn.index(curr_ass) if curr_ass in opt_yn else 0
                    inp_ass = st.selectbox(f"Assenza Evento ({nick})", options=opt_yn, index=idx_ass, key=f"ass_form_{idx}")
                with c8:
                    curr_r4 = str(row.get("Mancata_Risposta_R4", "no")).lower()
                    idx_r4 = opt_yn.index(curr_r4) if curr_r4 in opt_yn else 0
                    inp_r4 = st.selectbox(f"Mancata Risposta R4 ({nick})", options=opt_yn, index=idx_r4, key=f"r4_form_{idx}")

                c9, _ = st.columns(2)
                with c9:
                    opt_giorni = ["0", "1", "2", "3", "4", "5", "6", "7"]
                    curr_inatt = str(row.get("Giorni_Inattivita", "0"))
                    idx_inatt = opt_giorni.index(curr_inatt) if curr_inatt in opt_giorni else 0
                    inp_inatt = st.selectbox(f"Giorni Inattività ({nick})", options=opt_giorni, index=idx_inatt, key=f"inatt_form_{idx}")

                nuovi_dati.append({
                    "Nickname": nick,
                    "Punti_VS": converti_in_numero_puro(inp_vs),
                    "Combattente_Sabato": inp_comb,
                    "Eventi_Totali": inp_eventi,
                    "Donazioni_Tech": converti_in_numero_puro(inp_tech),
                    "Premi_Stella": inp_stella,
                    "Penalita_Scudo": inp_scudo,
                    "Assenza_Evento": inp_ass,
                    "Mancata_Risposta_R4": inp_r4,
                    "Giorni_Inattivita": inp_inatt
                })
                st.markdown("---")

            btn_invia_form = st.form_submit_button(T["save_drive_btn"], type="primary", width="stretch")
            if btn_invia_form:
                df_salvataggio = pd.DataFrame(nuovi_dati)
                if salva_dati_su_drive(sheet_obj, df_salvataggio):
                    st.success("🎉 Dati salvati con successo su Google Drive!")
                    st.rerun()

# ==============================================================================
# 4. TAB CLASSIFICA
# ==============================================================================
with tab_report:
    st.subheader(T["tab_classifica"])
    if df_drive is not None:
        if st.button(T["calc_btn"], type="primary", width="stretch"):
            df_calcolato = calcola_punteggi_alleanza(df_drive, st.session_state.config_settimana)
            map_cols = {"Nickname": T["col_nickname"], "Punti_VS": T["col_punti_vs"], "Punteggio_Totale": T["col_punteggio_tot"]}
            st.session_state.df_calcolato_raw = df_calcolato
            st.session_state.df_calcolato = df_calcolato.rename(columns=map_cols)
            st.success("Punteggi calcolati!")
        if "df_calcolato" in st.session_state:
            df_mostra = st.session_state.df_calcolato.copy()
            if "Punti_VS" in df_mostra.columns:
                df_mostra["Punti_VS"] = df_mostra["Punti_VS"].apply(formatta_con_puntini)
            if "Donazioni_Tech" in df_mostra.columns:
                df_mostra["Donazioni_Tech"] = df_mostra["Donazioni_Tech"].apply(formatta_con_puntini)
                
            col_n_str = T["col_n"]
            if col_n_str in df_mostra.columns:
                df_mostra = df_mostra.drop(columns=[col_n_str])
            df_mostra.insert(0, col_n_str, range(1, len(df_mostra) + 1))
            st.dataframe(df_mostra, width="stretch", height=450)
            
            pdf_data = genera_report_pdf(st.session_state.df_calcolato_raw, st.session_state.config_settimana["tipo_settimana"])
            st.download_button(label=T["download_pdf_btn"], data=pdf_data, file_name="Report.pdf", mime="application/pdf", type="primary", width="stretch")

with tab_chat:
    st.subheader(T["tab_chat"])
    prompt_utente = st.text_input(T["ai_prompt_label"])
    if st.button(T["ai_send_btn"], type="primary") and prompt_utente:
        if GEMINI_API_KEY:
            try:
                client = genai.Client(api_key=GEMINI_API_KEY)
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt_utente)
                st.info(response.text)
            except Exception as e:
                st.error(f"❌ Errore IA: {e}")
        else:
            st.error("⚠️ Chiave API Gemini non configurata nei Secrets.")

with tab_regole:
    st.subheader(T["tab_regole"])
    st.markdown(f"### {T['rule_goal_title']}")
    st.markdown(T['rule_goal_desc'])
    st.markdown("---")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.subheader(T['rule_vs_title'])
        st.markdown(T['rule_vs_desc'])
        st.markdown("---")
        st.subheader(T['rule_ev_title'])
        st.markdown(T['rule_ev_desc'])
    with col_r2:
        st.subheader(T['rule_tech_title'])
        st.markdown(T['rule_tech_desc'])
        st.markdown("---")
        st.subheader(T['rule_bonus_title'])
        st.markdown(T['rule_bonus_desc'])
        st.markdown("---")
        st.subheader(T['rule_pen_title'])
        st.markdown(T['rule_pen_desc'])

if is_admin and tab_log is not None:
    with tab_log:
        st.subheader(T["tab_log"])
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                log_content = f.read()
            st.text_area("Registro Attività", log_content, height=300)
            if st.button(T["btn_empty_log"], type="primary"):
                svuota_log()
                st.success("Registro log svuotato con successo!")
                st.rerun()
        else:
            st.info("Nessun log registrato finora.")