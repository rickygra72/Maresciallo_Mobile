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
        "tot_eventi_programmati": 5,
        "deserto_inizio": str(datetime.datetime.now().date()),
        "deserto_fine": str((datetime.datetime.now() + datetime.timedelta(days=7)).date()),
        "canyon_inizio": str(datetime.datetime.now().date()),
        "canyon_fine": str((datetime.datetime.now() + datetime.timedelta(days=7)).date())
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
        "tab_crescita": "📈 Crescita Squadre", "tab_deserto": "🏜️ Battaglia Deserto", "tab_canyon": "🏔️ Battaglia Canyon",
        "tab_chat": "🤖 Assistente IA", "tab_log": "📜 Registro Log",
        "save_drive_btn": "💾 SALVA TUTTI I CAMBIAMENTI SU GOOGLE DRIVE", "calc_btn": "🧮 CALCOLA CLASSIFICA SETTIMANALE",
        "download_pdf_btn": "📄 SCARICA REPORT SETTIMANALE IN PDF", "squadre_header": "⚔️ Gestione Potenza delle 4 Squadre",
        "crescita_header": "📈 Analisi Percentuale di Crescita Mensile", "save_squadre_btn": "💾 SALVA SQUADRE DEL MESE",
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
        "m_input_squad_power": "Potenza", "m_submit_btn": "💾 INVIA", "m_save_success_approval": "Inviato per approvazione!",
        "m_save_success_direct": "Squadre salvate con successo!", "pending_requests_warn": "🚨 **Ci sono {count} richieste in attesa!**",
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
        "tab_crescita": "📈 Growth", "tab_deserto": "🏜️ Desert Battle", "tab_canyon": "🏔️ Canyon Battle",
        "tab_chat": "🤖 AI", "tab_log": "📜 Log", "save_drive_btn": "💾 SAVE", "calc_btn": "🧮 CALCULATE",
        "download_pdf_btn": "📄 PDF", "squadre_header": "Squads", "crescita_header": "Growth", "success_drive": "Connected",
        "month_curr_label": "Month", "month_prev_label": "Prev", "month_edit_title": "Edit", "month_analysis_title": "Growth",
        "ai_prompt_label": "Ask", "ai_send_btn": "Send", "btn_empty_log": "Clear", "rule_goal_title": "Goal", "rule_goal_desc": "Desc",
        "rule_vs_title": "1. VS", "rule_vs_desc": "Desc", "rule_ev_title": "2. Events", "rule_ev_desc": "Desc",
        "rule_tech_title": "3. Tech", "rule_tech_desc": "Desc", "rule_bonus_title": "4. Star", "rule_bonus_desc": "Desc",
        "rule_pen_title": "5. Penalty", "rule_pen_desc": "Desc", "m_portal_title": "Portal", "m_connected_as": "Connected:",
        "m_member_role": "(Member)", "m_month_info": "Month:", "m_format_info": "Format", "m_pending_warn": "Pending",
        "m_approved_success": "Approved", "m_not_submitted": "Not submitted", "m_sq1_label": "Sq 1", "m_sq2_label": "Sq 2",
        "m_sq3_label": "Sq 3", "m_sq4_label": "Sq 4", "m_input_squad_power": "Power", "m_submit_btn": "SUBMIT",
        "m_save_success_approval": "Sent for approval!", "m_save_success_direct": "Saved!", "pending_requests_warn": "Pending {count}",
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
        "tab_crescita": "📈 Wachstum", "tab_deserto": "🏜️ Wüstenschlacht", "tab_canyon": "🏔️ Canyonschlacht",
        "tab_chat": "🤖 KI", "tab_log": "📜 Log", "save_drive_btn": "💾 SPEICHERN", "calc_btn": "🧮 BERECHNEN",
        "download_pdf_btn": "📄 PDF", "squadre_header": "Truppen", "crescita_header": "Wachstum", "success_drive": "Verbunden",
        "month_curr_label": "Monat", "month_prev_label": "Vormonat", "month_edit_title": "Bearbeiten", "month_analysis_title": "Wachstum",
        "ai_prompt_label": "Frage", "ai_send_btn": "Senden", "btn_empty_log": "Leeren", "rule_goal_title": "Ziel", "rule_goal_desc": "Desc",
        "rule_vs_title": "1. VS", "rule_vs_desc": "Desc", "rule_ev_title": "2. Events", "rule_ev_desc": "Desc",
        "rule_tech_title": "3. Tech", "rule_tech_desc": "Desc", "rule_bonus_title": "4. Sterne", "rule_bonus_desc": "Desc",
        "rule_pen_title": "5. Strafen", "rule_pen_desc": "Desc", "m_portal_title": "Portal", "m_connected_as": "Verbunden als:",
        "m_member_role": "(Mitglied)", "m_month_info": "Monat:", "m_format_info": "Format", "m_pending_warn": "Wartet",
        "m_approved_success": "Genehmigt", "m_not_submitted": "Nicht eingereicht", "m_sq1_label": "Truppe 1", "m_sq2_label": "Truppe 2",
        "m_sq3_label": "Truppe 3", "m_sq4_label": "Truppe 4", "m_input_squad_power": "Stärke", "m_submit_btn": "SENDEN",
        "m_save_success_approval": "Zur Genehmigung gesendet!", "m_save_success_direct": "Gespeichert!", "pending_requests_warn": "Wartet {count}",
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
                
                for col_num in ["Punti_VS", "Donazioni_Tech", "Premi_Stella"]:
                    if col_num in df.columns:
                        df[col_num] = df[col_num].apply(converti_in_numero_puro)

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
    headers_base = ["Mese_Anno", "Nickname", "Tipo_Squadra_1", "Squadra_1", "Tipo_Squadra_2", "Squadra_2", "Tipo_Squadra_3", "Squadra_3", "Tipo_Squadra_4", "Squadra_4", "Stato_Approvazione"]
    try:
        sheet_squadre = sh.worksheet("Registro_Squadre")
        rows = sheet_squadre.get_all_values()
    except Exception:
        try:
            sheet_squadre = sh.add_worksheet(title="Registro_Squadre", rows=100, cols=15)
            sheet_squadre.update(range_name="A1", values=[headers_base])
            return pd.DataFrame(columns=headers_base), sheet_squadre
        except Exception:
            return pd.DataFrame(columns=headers_base), None

    if not rows or len(rows) == 0:
        sheet_squadre.update(range_name="A1", values=[headers_base])
        return pd.DataFrame(columns=headers_base), sheet_squadre

    headers = [str(h).strip() for h in rows[0]]
    data = rows[1:]
    
    if "Nickname" not in headers:
        sheet_squadre.clear()
        sheet_squadre.update(range_name="A1", values=[headers_base])
        return pd.DataFrame(columns=headers_base), sheet_squadre

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

def carica_iscrizioni_esatte_da_drive(sh, nome_foglio):
    headers_base = ["Settimana", "Nickname", "Scelta", "Preferenza_Orario", "Timestamp"]
    try:
        sheet_iscrizioni = sh.worksheet(nome_foglio)
        rows = sheet_iscrizioni.get_all_values()
    except Exception:
        try:
            sheet_iscrizioni = sh.add_worksheet(title=nome_foglio, rows=100, cols=10)
            sheet_iscrizioni.update(range_name="A1", values=[headers_base])
            return pd.DataFrame(columns=headers_base), sheet_iscrizioni
        except Exception:
            return pd.DataFrame(columns=headers_base), None

    if not rows or len(rows) == 0:
        sheet_iscrizioni.update(range_name="A1", values=[headers_base])
        return pd.DataFrame(columns=headers_base), sheet_iscrizioni

    headers = [str(h).strip() for h in rows[0]]
    data = rows[1:]
    
    if "Nickname" not in headers:
        sheet_iscrizioni.clear()
        sheet_iscrizioni.update(range_name="A1", values=[headers_base])
        return pd.DataFrame(columns=headers_base), sheet_iscrizioni

    df = pd.DataFrame(data, columns=headers[:len(data[0])] if data and len(data) > 0 else headers)
    for col in headers_base:
        if col not in df.columns:
            df[col] = ""
    df = pulisci_dataframe(df)
    return df, sheet_iscrizioni

def salva_iscrizioni_esatte_su_drive(sheet_iscrizioni, df):
    try:
        sheet_iscrizioni.clear()
        df_clean = pulisci_dataframe(df)
        valori = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
        sheet_iscrizioni.update(range_name="A1", values=valori)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio Registro: {e}")
    return False

def verifica_squadre_validate_membro(spreadsheet_obj, nickname):
    mese_attuale = datetime.datetime.now().strftime("%Y-%m")
    try:
        df_sq, _ = carica_squadre_da_drive(spreadsheet_obj)
        if df_sq is not None and not df_sq.empty:
            df_sq["Nick_Clean"] = df_sq["Nickname"].astype(str).str.replace("🔴 ", "").str.strip().str.lower()
            user_row = df_sq[(df_sq["Mese_Anno"] == mese_attuale) & (df_sq["Nick_Clean"] == nickname.strip().lower())]
            if not user_row.empty:
                stato = str(user_row.iloc[0].get("Stato_Approvazione", "")).strip()
                if stato == "Approvato":
                    return True
    except Exception:
        pass
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

def genera_pdf_iscrizioni(df_iscrizioni, titolo_evento, settimana):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#1A365D"), spaceAfter=10, alignment=1)
    subtitle_style = ParagraphStyle('DocSubTitle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#4A5568"), spaceAfter=15, alignment=1)
    
    story.append(Paragraph(f"⚔️ REPORT COMPLETO ISCRIZIONI {titolo_evento} - Settimana: {settimana}", title_style))
    story.append(Paragraph(f"Generato il: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    story.append(Spacer(1, 5))
    
    cols = list(df_iscrizioni.columns)
    table_data = [cols]
    for _, row in df_iscrizioni.iterrows():
        table_data.append([str(row.get(c, '')) for c in cols])
        
    col_width = max(40, min(120, int(750 / max(1, len(cols)))))
    t = Table(table_data, colWidths=[col_width]*len(cols))
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
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
        if st.button("Conferma / Confirm / Bestätigen", type="primary", use_container_width=True):
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

# --- BARRA SUPERIORE CON PULSANTE HOME E LOGOUT ---
col_h1, col_h2, col_h3 = st.columns([6, 1, 1])
with col_h2:
    if st.button("🏠 HOME", use_container_width=True, key="btn_top_home"):
        st.rerun()
with col_h3:
    if st.button(T["logout_btn"], use_container_width=True, key="btn_top_logout"):
        st.session_state.autenticato = False
        st.session_state.ruolo = None
        st.session_state.lang = None
        if "ruolo_originale" in st.session_state:
            del st.session_state["ruolo_originale"]
        st.rerun()

spreadsheet_obj = connetti_google_drive().open_by_key(ID_FOGLIO_DRIVE) if connetti_google_drive() else None
is_r4_user = (st.session_state.get("ruolo") == "R4" or st.session_state.get("ruolo_originale") == "R4")
is_admin = (st.session_state.get("nome_utente", "").lower().strip() == "rickygra72")

# --- COSTRUZIONE DEI TAB IN BASE AL RUOLO ---
if is_r4_user:
    elenco_tabs = [T["tab_squadre"], T["tab_crescita"], T["tab_dati"], T["tab_classifica"], T["tab_deserto"], T["tab_canyon"], T["tab_chat"], T["tab_regole"]]
    if is_admin:
        elenco_tabs.append(T["tab_log"])
    tabs = st.tabs(elenco_tabs)
    tab_squadre, tab_crescita, tab_dati, tab_report, tab_deserto, tab_canyon, tab_chat, tab_regole = tabs[0], tabs[1], tabs[2], tabs[3], tabs[4], tabs[5], tabs[6], tabs[7]
    tab_log = tabs[8] if is_admin else None
else:
    elenco_tabs = [T["tab_squadre"], T["tab_deserto"], T["tab_canyon"]]
    tabs = st.tabs(elenco_tabs)
    tab_squadre, tab_deserto, tab_canyon = tabs[0], tabs[1], tabs[2]
    tab_crescita = tab_report = tab_chat = tab_log = tab_dati = tab_regole = None

# --- TAB SQUADRE ---
with tab_squadre:
    st.subheader(T["squadre_header"])
    if spreadsheet_obj:
        df_drive_attivo, sheet_obj_punti, _ = carica_dati_da_drive()
        df_squadre, sheet_squadre_obj = carica_squadre_da_drive(spreadsheet_obj)
        
        if df_squadre is not None and df_drive_attivo is not None:
            if "Stato_Approvazione" not in df_squadre.columns:
                df_squadre["Stato_Approvazione"] = "Approvato"

            df_in_attesa = df_squadre[df_squadre["Stato_Approvazione"].astype(str).str.contains("In Attesa")].copy()
            if not df_in_attesa.empty and is_r4_user:
                st.warning(T["pending_requests_warn"].format(count=len(df_in_attesa)))
                if st.button(T["btn_approve_all"], type="primary", key="btn_app_all_squadre"):
                    for idx_att in df_in_attesa.index:
                        df_squadre.loc[idx_att, "Stato_Approvazione"] = "Approvato"
                    salva_squadre_su_drive(sheet_squadre_obj, df_squadre)
                    st.success("🎉 Tutte le richieste approvate!")
                    st.rerun()

            mese_attuale_def = datetime.datetime.now().strftime("%Y-%m")
            nick_user = st.session_state.nome_utente.strip()
            
            if not is_r4_user:
                st.info(f"🗓️ Mese corrente: **{mese_attuale_def}** — Inserisci o aggiorna le tue 4 squadre.")
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
                else:
                    t1_val = t2_val = t3_val = t4_val = None
                    s1_val = s2_val = s3_val = s4_val = "0M"
                    
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

                    btn_salva_membro = st.form_submit_button(T['m_submit_btn'], type="primary", use_container_width=True)
                    
                if btn_salva_membro:
                    if duplicati_presenti and not conferma_anomalia:
                        st.error("🚫 Invio bloccato: spunta la casella di conferma.")
                        st.stop()

                    stato_richiesta = "In Attesa"
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
                        st.success(T["m_save_success_approval"])
            else:
                mesi_anno = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"]
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

                df_squadre_edit = st.data_editor(df_mese_curr, column_config=column_config_sq, num_rows="dynamic", use_container_width=True, key="editor_squadre")
                if st.button(T["save_squadre_btn"], type="primary", key="btn_save_squadre_r4_tab"):
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
                        st.success(T["m_save_success_direct"])
                        st.rerun()

# --- TAB CRESCITA (SOLO R4) ---
if is_r4_user and tab_crescita is not None:
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
                        st.dataframe(df_visibile, use_container_width=True)

# --- TAB DATI (SOLO R4) ---
if is_r4_user and tab_dati is not None:
    with tab_dati:
        st.subheader("📊 Inserimento Punteggi (Prospetto Unificato con Menu a Tendina e Legenda)")
        df_drive, sheet_obj, spreadsheet_obj = carica_dati_da_drive()
        if df_drive is not None:
            st.success(T["success_drive"])
            
            with st.expander("📖 LEGENDA DI CONFRONTO E GUIDA COLONNE", expanded=True):
                st.markdown("""
                | Nome Colonna / Campo | Significato / Regola di Inserimento | Valori Accettati |
                | :--- | :--- | :--- |
                | **N.** | Numero progressivo riga | Automatico |
                | **Nickname** | Nome del giocatore in-game | Testo |
                | **VS** | Punti VS settimanali (senza M o K) | Numeri interi puri (es. `47430991`) |
                | **Comb.** | Combattente di Sabato | Menu a tendina: `no` / `si` |
                | **Tech** | Donazioni Tecnologiche | Numeri interi puri (es. `9500`) |
                | **Stelle** | Premi Stella assegnati | Menu a tendina: da `0` a `7` |
                | **Scudo** | Penalità Scudo caduto | Menu a tendina: `no` / `si` |
                | **Ass.** | Assenza Ingiustificata agli Eventi | Menu a tendina: `no` / `si` |
                | **No R4** | Mancata Risposta / Inadempienza Iscrizioni Eventi | Menu a tendina: `no` / `si` |
                | **Eventi** | Presenze totali eventi di gruppo | Menu a tendina: da `0` a `10` |
                """)
            st.markdown("---")

            with st.form("form_inserimento_unificato"):
                nuovi_dati = []
                
                hc1, hc2, hc3, hc4, hc5, hc6, hc7, hc8, hc9, hc10 = st.columns([0.6, 2, 2, 1, 2, 1, 1, 1, 1, 1])
                hc1.markdown(f"**{T['col_n']}**")
                hc2.markdown(f"**{T['col_nickname']}**")
                hc3.markdown(f"**{T['col_punti_vs']}**")
                hc4.markdown(f"**{T['col_combattente']}**")
                hc5.markdown(f"**{T['col_donazioni']}**")
                hc6.markdown(f"**{T['col_premi']}**")
                hc7.markdown(f"**{T['col_pen_scudo']}**")
                hc8.markdown(f"**{T['col_assenza']}**")
                hc9.markdown(f"**{T['col_mancata_risp']}**")
                hc10.markdown(f"**{T['col_eventi']}**")
                st.markdown("---")

                opzioni_eventi = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
                opzioni_yn = ["no", "si"]
                opzioni_stelle = [0, 1, 2, 3, 4, 5, 6, 7]

                for idx, row in df_drive.iterrows():
                    nick = str(row.get("Nickname", ""))
                    rc1, rc2, rc3, rc4, rc5, rc6, rc7, rc8, rc9, rc10 = st.columns([0.6, 2, 2, 1, 2, 1, 1, 1, 1, 1])
                    
                    rc1.markdown(f"**{idx+1}**")
                    rc2.markdown(f"**{nick}**")
                    
                    val_vs_pulito = str(converti_in_numero_puro(row.get("Punti_VS", 0)))
                    if val_vs_pulito == "0": val_vs_pulito = ""
                    inp_vs = rc3.text_input(f"VS_{idx}", value=formatta_con_puntini(val_vs_pulito) if val_vs_pulito else "", label_visibility="collapsed", key=f"vs_form_{idx}")
                    
                    curr_comb = str(row.get("Combattente_Sabato", "no")).lower()
                    idx_comb = opzioni_yn.index(curr_comb) if curr_comb in opzioni_yn else 0
                    inp_comb = rc4.selectbox(f"Comb_{idx}", options=opzioni_yn, index=idx_comb, label_visibility="collapsed", key=f"comb_form_{idx}")
                    
                    val_tech_pulito = str(converti_in_numero_puro(row.get("Donazioni_Tech", 0)))
                    if val_tech_pulito == "0": val_tech_pulito = ""
                    inp_tech = rc5.text_input(f"Tech_{idx}", value=formatta_con_puntini(val_tech_pulito) if val_tech_pulito else "", label_visibility="collapsed", key=f"tech_form_{idx}")
                    
                    st_val = int(converti_in_numero_puro(row.get("Premi_Stella", 0)))
                    if st_val > 7: st_val = 7
                    idx_st = opzioni_stelle.index(st_val) if st_val in opzioni_stelle else 0
                    inp_stella = rc6.selectbox(f"Stella_{idx}", options=opzioni_stelle, index=idx_st, label_visibility="collapsed", key=f"stella_form_{idx}")
                    
                    curr_scudo = str(row.get("Penalita_Scudo", "no")).lower()
                    idx_scudo = opzioni_yn.index(curr_scudo) if curr_scudo in opzioni_yn else 0
                    inp_scudo = rc7.selectbox(f"Scudo_{idx}", options=opzioni_yn, index=idx_scudo, label_visibility="collapsed", key=f"scudo_form_{idx}")
                    
                    curr_ass = str(row.get("Assenza_Evento", "no")).lower()
                    idx_ass = opzioni_yn.index(curr_ass) if curr_ass in opzioni_yn else 0
                    inp_ass = rc8.selectbox(f"Ass_{idx}", options=opzioni_yn, index=idx_ass, label_visibility="collapsed", key=f"ass_form_{idx}")
                    
                    curr_r4 = str(row.get("Mancata_Risposta_R4", "no")).lower()
                    idx_r4 = opzioni_yn.index(curr_r4) if curr_r4 in opzioni_yn else 0
                    inp_r4 = rc9.selectbox(f"R4_{idx}", options=opzioni_yn, index=idx_r4, label_visibility="collapsed", key=f"r4_form_{idx}")
                    
                    curr_ev = str(row.get("Eventi_Totali", "0"))
                    idx_ev = opzioni_eventi.index(curr_ev) if curr_ev in opzioni_eventi else 0
                    inp_eventi = rc10.selectbox(f"Ev_{idx}", options=opzioni_eventi, index=idx_ev, label_visibility="collapsed", key=f"ev_form_{idx}")

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
                        "Giorni_Inattivita": str(row.get("Giorni_Inattivita", 0))
                    })

                st.markdown("---")
                btn_invia_form = st.form_submit_button(T["save_drive_btn"], type="primary", use_container_width=True)
                if btn_invia_form:
                    df_salvataggio = pd.DataFrame(nuovi_dati)
                    if salva_dati_su_drive(sheet_obj, df_salvataggio):
                        st.success("🎉 Dati salvati con successo su Google Drive!")
                        st.rerun()

# --- TAB CLASSIFICA (SOLO R4) ---
if is_r4_user and tab_report is not None:
    with tab_report:
        st.subheader(T["tab_classifica"])
        df_drive, _, _ = carica_dati_da_drive()
        if df_drive is not None:
            if st.button(T["calc_btn"], type="primary", use_container_width=True, key="btn_calc_classifica"):
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
                
                st.dataframe(df_mostra, use_container_width=True, height=450)
                
                pdf_data = genera_report_pdf(st.session_state.df_calcolato_raw, st.session_state.config_settimana["tipo_settimana"])
                st.download_button(label=T["download_pdf_btn"], data=pdf_data, file_name="Report.pdf", mime="application/pdf", type="primary", use_container_width=True, key="dl_pdf_classifica")

# --- TAB DESERTO ---
with tab_deserto:
    st.subheader("🏜️ Campo di Battaglia del DESERTO - Iscrizioni")
    if spreadsheet_obj:
        cfg_d = st.session_state.config_settimana
        
        if is_r4_user:
            with st.expander("⚙️ [R4/R5] Imposta Finestra Temporale Iscrizioni Deserto"):
                try:
                    def_d_i = datetime.datetime.strptime(cfg_d.get("deserto_inizio", "2026-01-01 00:00"), "%Y-%m-%d %H:%M")
                except Exception:
                    def_d_i = datetime.datetime.now()
                try:
                    def_d_f = datetime.datetime.strptime(cfg_d.get("deserto_fine", "2026-12-31 23:59"), "%Y-%m-%d %H:%M")
                except Exception:
                    def_d_f = datetime.datetime.now() + datetime.timedelta(days=3)

                di_d = st.date_input("Inizio Data (GG/MM/AAAA)", value=def_d_i.date(), format="DD/MM/YYYY", key="tab_di_d")
                di_t = st.time_input("Inizio Ora", value=def_d_i.time(), key="tab_di_t")
                df_d = st.date_input("Fine Data (GG/MM/AAAA)", value=def_d_f.date(), format="DD/MM/YYYY", key="tab_df_d")
                df_t = st.time_input("Fine Ora", value=def_d_f.time(), key="tab_df_t")

                if st.button("💾 Salva Date Deserto", key="btn_save_tab_deserto"):
                    cfg_d["deserto_inizio"] = f"{di_d} {di_t.strftime('%H:%M')}"
                    cfg_d["deserto_fine"] = f"{df_d} {df_t.strftime('%H:%M')}"
                    st.session_state.config_settimana = cfg_d
                    save_config(cfg_d)
                    st.success("✅ Date Deserto aggiornate con successo!")

        try:
            dt_inizio_d = datetime.datetime.strptime(cfg_d.get("deserto_inizio", "2026-01-01 00:00"), "%Y-%m-%d %H:%M")
            dt_fine_d = datetime.datetime.strptime(cfg_d.get("deserto_fine", "2026-12-31 23:59"), "%Y-%m-%d %H:%M")
        except Exception:
            dt_inizio_d, dt_fine_d = datetime.datetime.min, datetime.datetime.max

        now_utc = datetime.datetime.now()
        deserto_aperto = dt_inizio_d <= now_utc <= dt_fine_d
        settimana_corrente = datetime.datetime.now().strftime("%Y-W%U")

        st.info(f"⏳ Finestra Iscrizioni Deserto: dal **{dt_inizio_d.strftime('%d/%m/%Y %H:%M')}** al **{dt_fine_d.strftime('%d/%m/%Y %H:%M')}**")
        if not deserto_aperto:
            st.error("🔴 **Iscrizioni Deserto CHIUSE.** Fuori tempo massimo di registrazione.")

        df_isc_d, sheet_isc_d_obj = carica_iscrizioni_esatte_da_drive(spreadsheet_obj, "Registro_Deserto")
        df_isc_d_curr = df_isc_d[df_isc_d["Settimana"] == settimana_corrente] if not df_isc_d.empty and "Settimana" in df_isc_d.columns else pd.DataFrame()
        
        deserto_partecipanti = len(df_isc_d_curr[df_isc_d_curr["Scelta"] == "Partecipo"]) if not df_isc_d_curr.empty and "Scelta" in df_isc_d_curr.columns else 0
        posti_deserto_titolari = max(0, 20 - deserto_partecipanti)

        nick_user = st.session_state.nome_utente.strip()
        user_isc_d = df_isc_d_curr[df_isc_d_curr["Nickname"].astype(str).str.strip().str.lower() == nick_user.lower()] if not df_isc_d_curr.empty and "Nickname" in df_isc_d_curr.columns else pd.DataFrame()
        prev_d_scelta = user_isc_d.iloc[0].get("Scelta", "Partecipo") if not user_isc_d.empty else "Partecipo"
        prev_d_pref = user_isc_d.iloc[0].get("Preferenza_Orario", "Squadra A (Ven 13:00)") if not user_isc_d.empty else "Squadra A (Ven 13:00)"

        opzioni_scelta = ["Partecipo", "Non sono sicuro (Riserva)", "Non partecipo"]
        opzioni_preferenza_deserto = ["Squadra A (Ven 13:00)", "Squadra B (Ven 22:00)"]

        st.markdown(f"Posti Titolari Deserto Disponibili: **{posti_deserto_titolari} / 20**")

        with st.form("form_tab_deserto"):
            in_d_scelta = st.selectbox("Scelta Deserto", opzioni_scelta, index=opzioni_scelta.index(prev_d_scelta) if prev_d_scelta in opzioni_scelta else 0)
            in_d_pref = st.selectbox("Squadra / Orario Deserto", opzioni_preferenza_deserto, index=opzioni_preferenza_deserto.index(prev_d_pref) if prev_d_pref in opzioni_preferenza_deserto else 0)
            btn_invia_d = st.form_submit_button("💾 INVIA ISCRIZIONE DESERTO", type="primary", use_container_width=True)

        if btn_invia_d:
            if not deserto_aperto:
                st.error("🚫 Spiacenti, iscrizioni Deserto fuori tempo massimo.")
                st.stop()

            # --- CHECK SICUREZZA: SQUADRE VALIDATE ---
            if not is_r4_user and not verifica_squadre_validate_membro(spreadsheet_obj, nick_user):
                st.error("⚠️ Non puoi iscriverti agli eventi finché le tue squadre non saranno inserite e convalidate da un ufficiale R4. Per eventuali urgenze contattare R4.")
                st.stop()

            timestamp_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            df_isc_d["Nick_Cmp"] = df_isc_d["Nickname"].astype(str).str.strip().str.lower()
            maschera_d = (df_isc_d["Settimana"] == settimana_corrente) & (df_isc_d["Nick_Cmp"] == nick_user.lower())
            if "Nick_Cmp" in df_isc_d.columns:
                df_isc_d = df_isc_d.drop(columns=["Nick_Cmp"])

            if df_isc_d[maschera_d].shape[0] > 0:
                df_isc_d.loc[maschera_d, "Scelta"] = in_d_scelta
                df_isc_d.loc[maschera_d, "Preferenza_Orario"] = in_d_pref
                df_isc_d.loc[maschera_d, "Timestamp"] = timestamp_str
                df_isc_d_agg = df_isc_d
            else:
                nuova_d = pd.DataFrame([{
                    "Settimana": settimana_corrente, "Nickname": nick_user,
                    "Scelta": in_d_scelta, "Preferenza_Orario": in_d_pref, "Timestamp": timestamp_str
                }])
                df_isc_d_agg = pd.concat([df_isc_d, nuova_d], ignore_index=True)
            
            if salva_iscrizioni_esatte_su_drive(sheet_isc_d_obj, df_isc_d_agg):
                df_drive_punti, sheet_punti_obj, _ = carica_dati_da_drive()
                if not df_drive_punti.empty:
                    for idx_p, row_p in df_drive_punti.iterrows():
                        if str(row_p["Nickname"]).replace("🔴 ", "").strip().lower() == nick_user.lower():
                            df_drive_punti.loc[idx_p, "Mancata_Risposta_R4"] = "no"
                    salva_dati_su_drive(sheet_punti_obj, df_drive_punti)
                st.success("ISCRIZIONE DESERTO SALVATA CORRETTAMENTE")
                st.rerun()

        # VISIBILE SOLO AGLI R4/R5: Prospetto completo, elenco iscritti e download report
        if is_r4_user:
            st.markdown("---")
            st.subheader("📋 Prospetto Generale e Report Deserto (Tutti i Membri - Riservato R4/R5)")
            df_drive_punti, sheet_punti_obj, _ = carica_dati_da_drive()
            if not df_drive_punti.empty:
                tutti_membri = [str(n).replace("🔴 ", "").strip() for n in df_drive_punti["Nickname"].tolist()]
                iscritti_df = df_isc_d[df_isc_d["Settimana"] == settimana_corrente].copy() if not df_isc_d.empty and "Settimana" in df_isc_d.columns else pd.DataFrame()
                iscritti_dict = {str(row["Nickname"]).strip().lower(): row for _, row in iscritti_df.iterrows()} if not iscritti_df.empty else {}
                
                report_completo = []
                inadempienti = []
                
                for m in tutti_membri:
                    m_low = m.lower()
                    if m_low in iscritti_dict:
                        r = iscritti_dict[m_low]
                        pref = str(r.get("Preferenza_Orario", "Squadra A (Ven 13:00)"))
                        scelta = str(r.get("Scelta", "Partecipo"))
                        ts = str(r.get("Timestamp", "-"))
                        
                        if "Squadra A" in pref:
                            ordine_sort = 1
                        elif "Squadra B" in pref:
                            ordine_sort = 2
                        else:
                            ordine_sort = 3
                            
                        report_completo.append({
                            "Nickname": m, "Stato_Iscrizione": scelta, "Squadra_Orario": pref,
                            "Timestamp": ts, "_ordine": ordine_sort
                        })
                    else:
                        inadempienti.append(m)
                        report_completo.append({
                            "Nickname": m, "Stato_Iscrizione": "Malus / Non ha partecipato", "Squadra_Orario": "Nessuna",
                            "Timestamp": "-", "_ordine": 4
                        })
                
                for idx_p, row_p in df_drive_punti.iterrows():
                    clean_n = str(row_p["Nickname"]).replace("🔴 ", "").strip()
                    if clean_n in inadempienti:
                        df_drive_punti.loc[idx_p, "Mancata_Risposta_R4"] = "si"
                    else:
                        df_drive_punti.loc[idx_p, "Mancata_Risposta_R4"] = "no"
                salva_dati_su_drive(sheet_punti_obj, df_drive_punti)

                df_report = pd.DataFrame(report_completo).sort_values(by=["_ordine", "Nickname"]).drop(columns=["_ordine"])
                df_report.insert(0, "N.", range(1, len(df_report) + 1))
                
                if not iscritti_df.empty:
                    riga_da_cancellare = st.selectbox("Seleziona iscrizione da cancellare", options=["-- Seleziona --"] + [f"{row['Nickname']} ({row['Squadra_Orario']})" for _, row in iscritti_df.iterrows()], key="sel_canc_deserto_tab")
                    if riga_da_cancellare != "-- Seleziona --":
                        nick_selezionato = riga_da_cancellare.split(" (")[0]
                        if st.button("🗑️ Cancella Iscrizione Selezionata", key="btn_del_deserto_tab"):
                            df_isc_d = df_isc_d[~((df_isc_d["Settimana"] == settimana_corrente) & (df_isc_d["Nickname"].str.strip().str.lower() == nick_selezionato.lower()))]
                            salva_iscrizioni_esatte_su_drive(sheet_isc_d_obj, df_isc_d)
                            st.success(f"Iscrizione di {nick_selezionato} cancellata con successo!")
                            st.rerun()

                st.dataframe(df_report, use_container_width=True)
                
                col_ex1, col_ex2 = st.columns(2)
                with col_ex1:
                    output_excel = io.BytesIO()
                    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                        df_report.to_excel(writer, sheet_name='Deserto', index=False)
                    output_excel.seek(0)
                    st.download_button(label="📊 SCARICA IN FORMATO EXCEL (.xlsx)", data=output_excel, file_name=f"Iscrizioni_Deserto_{settimana_corrente}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_excel_deserto_tab")
                with col_ex2:
                    pdf_isc_data = genera_pdf_iscrizioni(df_report, "DESERTO", settimana_corrente)
                    st.download_button(label="📄 SCARICA IN FORMATO PDF (.pdf)", data=pdf_isc_data, file_name=f"Iscrizioni_Deserto_{settimana_corrente}.pdf", mime="application/pdf", use_container_width=True, key="dl_pdf_deserto_tab")

# --- TAB CANYON ---
with tab_canyon:
    st.subheader("🏔️ Campo di Battaglia del CANYON - Iscrizioni")
    if spreadsheet_obj:
        cfg_c = st.session_state.config_settimana
        
        if is_r4_user:
            with st.expander("⚙️ [R4/R5] Imposta Finestra Temporale Iscrizioni Canyon"):
                try:
                    def_c_i = datetime.datetime.strptime(cfg_c.get("canyon_inizio", "2026-01-01 00:00"), "%Y-%m-%d %H:%M")
                except Exception:
                    def_c_i = datetime.datetime.now()
                try:
                    def_c_f = datetime.datetime.strptime(cfg_c.get("canyon_fine", "2026-12-31 23:59"), "%Y-%m-%d %H:%M")
                except Exception:
                    def_c_f = datetime.datetime.now() + datetime.timedelta(days=3)

                ci_d = st.date_input("Inizio Data (GG/MM/AAAA)", value=def_c_i.date(), format="DD/MM/YYYY", key="tab_ci_d")
                ci_t = st.time_input("Inizio Ora", value=def_c_i.time(), key="tab_ci_t")
                cf_d = st.date_input("Fine Data (GG/MM/AAAA)", value=def_c_f.date(), format="DD/MM/YYYY", key="tab_cf_d")
                cf_t = st.time_input("Fine Ora", value=def_c_f.time(), key="tab_cf_t")

                if st.button("💾 Salva Date Canyon", key="btn_save_tab_canyon"):
                    cfg_c["canyon_inizio"] = f"{ci_d} {ci_t.strftime('%H:%M')}"
                    cfg_c["canyon_fine"] = f"{cf_d} {cf_t.strftime('%H:%M')}"
                    st.session_state.config_settimana = cfg_c
                    save_config(cfg_c)
                    st.success("✅ Date Canyon aggiornate con successo!")

        try:
            dt_inizio_c = datetime.datetime.strptime(cfg_c.get("canyon_inizio", "2026-01-01 00:00"), "%Y-%m-%d %H:%M")
            dt_fine_c = datetime.datetime.strptime(cfg_c.get("canyon_fine", "2026-12-31 23:59"), "%Y-%m-%d %H:%M")
        except Exception:
            dt_inizio_c, dt_fine_c = datetime.datetime.min, datetime.datetime.max

        now_utc = datetime.datetime.now()
        canyon_aperto = dt_inizio_c <= now_utc <= dt_fine_c
        settimana_corrente = datetime.datetime.now().strftime("%Y-W%U")

        st.info(f"⏳ Finestra Iscrizioni Canyon: dal **{dt_inizio_c.strftime('%d/%m/%Y %H:%M')}** al **{dt_fine_c.strftime('%d/%m/%Y %H:%M')}**")
        if not canyon_aperto:
            st.error("🔴 **Iscrizioni Canyon CHIUSE.** Fuori tempo massimo di registrazione.")

        df_isc_c, sheet_isc_c_obj = carica_iscrizioni_esatte_da_drive(spreadsheet_obj, "Registro_Canyon")
        df_isc_c_curr = df_isc_c[df_isc_c["Settimana"] == settimana_corrente] if not df_isc_c.empty and "Settimana" in df_isc_c.columns else pd.DataFrame()
        
        canyon_partecipanti = len(df_isc_c_curr[df_isc_c_curr["Scelta"] == "Partecipo"]) if not df_isc_c_curr.empty and "Scelta" in df_isc_c_curr.columns else 0
        posti_canyon_titolari = max(0, 20 - canyon_partecipanti)

        user_isc_c = df_isc_c_curr[df_isc_c_curr["Nickname"].astype(str).str.strip().str.lower() == nick_user.lower()] if not df_isc_c_curr.empty and "Nickname" in df_isc_c_curr.columns else pd.DataFrame()
        prev_c_scelta = user_isc_c.iloc[0].get("Scelta", "Partecipo") if not user_isc_c.empty else "Partecipo"

        st.markdown(f"Posti Titolari Canyon Disponibili: **{posti_canyon_titolari} / 20**")

        with st.form("form_tab_canyon"):
            in_c_scelta = st.selectbox("Scelta Canyon (Giovedì 16:00)", opzioni_scelta, index=opzioni_scelta.index(prev_c_scelta) if prev_c_scelta in opzioni_scelta else 0)
            btn_invia_c = st.form_submit_button("💾 INVIA ISCRIZIONE CANYON", type="primary", use_container_width=True)

        if btn_invia_c:
            if not canyon_aperto:
                st.error("🚫 Spiacenti, iscrizioni Canyon fuori tempo massimo.")
                st.stop()

            # --- CHECK SICUREZZA: SQUADRE VALIDATE ---
            if not is_r4_user and not verifica_squadre_validate_membro(spreadsheet_obj, nick_user):
                st.error("⚠️ Non puoi iscriverti agli eventi finché le tue squadre non saranno inserite e convalidate da un ufficiale R4. Per eventuali urgenze contattare R4.")
                st.stop()

            timestamp_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            df_isc_c["Nick_Cmp"] = df_isc_c["Nickname"].astype(str).str.strip().str.lower()
            maschera_c = (df_isc_c["Settimana"] == settimana_corrente) & (df_isc_c["Nick_Cmp"] == nick_user.lower())
            if "Nick_Cmp" in df_isc_c.columns:
                df_isc_c = df_isc_c.drop(columns=["Nick_Cmp"])

            if df_isc_c[maschera_c].shape[0] > 0:
                df_isc_c.loc[maschera_c, "Scelta"] = in_c_scelta
                df_isc_c.loc[maschera_c, "Preferenza_Orario"] = "Giovedi 16:00"
                df_isc_c.loc[maschera_c, "Timestamp"] = timestamp_str
                df_isc_c_agg = df_isc_c
            else:
                nuova_c = pd.DataFrame([{
                    "Settimana": settimana_corrente, "Nickname": nick_user,
                    "Scelta": in_c_scelta, "Preferenza_Orario": "Giovedi 16:00", "Timestamp": timestamp_str
                }])
                df_isc_c_agg = pd.concat([df_isc_c, nuova_c], ignore_index=True)
            
            if salva_iscrizioni_esatte_su_drive(sheet_isc_c_obj, df_isc_c_agg):
                st.success("ISCRIZIONE CANYON SALVATA CORRETTAMENTE")
                st.rerun()

        # VISIBILE SOLO AGLI R4/R5: Prospetto completo, elenco iscritti e download report
        if is_r4_user:
            st.markdown("---")
            st.subheader("📋 Prospetto Generale e Report Canyon (Tutti i Membri - Riservato R4/R5)")
            df_drive_punti, _, _ = carica_dati_da_drive()
            if not df_drive_punti.empty:
                tutti_membri = [str(n).replace("🔴 ", "").strip() for n in df_drive_punti["Nickname"].tolist()]
                iscritti_df = df_isc_c[df_isc_c["Settimana"] == settimana_corrente].copy() if not df_isc_c.empty and "Settimana" in df_isc_c.columns else pd.DataFrame()
                iscritti_dict = {str(row["Nickname"]).strip().lower(): row for _, row in iscritti_df.iterrows()} if not iscritti_df.empty else {}
                
                report_completo_c = []
                
                for m in tutti_membri:
                    m_low = m.lower()
                    if m_low in iscritti_dict:
                        r = iscritti_dict[m_low]
                        scelta = str(r.get("Scelta", "Partecipo"))
                        ts = str(r.get("Timestamp", "-"))
                        
                        report_completo_c.append({
                            "Nickname": m, "Stato_Iscrizione": scelta, "Squadra_Orario": "Giovedì 16:00",
                            "Timestamp": ts, "_ordine": 1 if scelta == "Partecipo" else 2
                        })
                    else:
                        report_completo_c.append({
                            "Nickname": m, "Stato_Iscrizione": "Malus / Non ha partecipato", "Squadra_Orario": "Nessuna",
                            "Timestamp": "-", "_ordine": 3
                        })

                df_report_c = pd.DataFrame(report_completo_c).sort_values(by=["_ordine", "Nickname"]).drop(columns=["_ordine"])
                df_report_c.insert(0, "N.", range(1, len(df_report_c) + 1))
                
                if not iscritti_df.empty:
                    riga_da_cancellare_c = st.selectbox("Seleziona iscrizione da cancellare", options=["-- Seleziona --"] + [f"{row['Nickname']}" for _, row in iscritti_df.iterrows()], key="sel_canc_canyon_tab")
                    if riga_da_cancellare_c != "-- Seleziona --":
                        if st.button("🗑️ Cancella Iscrizione Selezionata", key="btn_del_canyon_tab"):
                            df_isc_c = df_isc_c[~((df_isc_c["Settimana"] == settimana_corrente) & (df_isc_c["Nickname"].str.strip().str.lower() == riga_da_cancellare_c.lower()))]
                            salva_iscrizioni_esatte_su_drive(sheet_isc_c_obj, df_isc_c)
                            st.success(f"Iscrizione di {riga_da_cancellare_c} cancellata con successo!")
                            st.rerun()

                st.dataframe(df_report_c, use_container_width=True)
                
                col_ex1, col_ex2 = st.columns(2)
                with col_ex1:
                    output_excel = io.BytesIO()
                    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                        df_report_c.to_excel(writer, sheet_name='Canyon', index=False)
                    output_excel.seek(0)
                    st.download_button(label="📊 SCARICA IN FORMATO EXCEL (.xlsx)", data=output_excel, file_name=f"Iscrizioni_Canyon_{settimana_corrente}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_excel_canyon_tab")
                with col_ex2:
                    pdf_isc_data = genera_pdf_iscrizioni(df_report_c, "CANYON", settimana_corrente)
                    st.download_button(label="📄 SCARICA IN FORMATO PDF (.pdf)", data=pdf_isc_data, file_name=f"Iscrizioni_Canyon_{settimana_corrente}.pdf", mime="application/pdf", use_container_width=True, key="dl_pdf_canyon_tab")

# --- TAB CHAT AI (SOLO R4) ---
if is_r4_user and tab_chat is not None:
    with tab_chat:
        st.subheader(T["tab_chat"])
        prompt_utente = st.text_input(T["ai_prompt_label"], key="input_ai_prompt")
        if st.button(T["ai_send_btn"], type="primary", key="btn_send_ai") and prompt_utente:
            if GEMINI_API_KEY:
                try:
                    client = genai.Client(api_key=GEMINI_API_KEY)
                    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt_utente)
                    st.info(response.text)
                except Exception as e:
                    st.error(f"❌ Errore IA: {e}")
            else:
                st.error("⚠️ Chiave API Gemini non configurata nei Secrets.")

# --- TAB REGOLE (SOLO R4) ---
if is_r4_user and tab_regole is not None:
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

# --- TAB LOG (SOLO ADMIN) ---
if is_admin and tab_log is not None:
    with tab_log:
        st.subheader(T["tab_log"])
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                log_content = f.read()
            st.text_area("Registro Attività", log_content, height=300, key="textarea_log_attivita")
            if st.button(T["btn_empty_log"], type="primary", key="btn_empty_log_file"):
                svuota_log()
                st.success("Registro log svuotato con successo!")
                st.rerun()
        else:
            st.info("Nessun log registrato finora.")