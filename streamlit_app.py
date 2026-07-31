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

# Libreria per la generazione dei Report PDF
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

# ID univoco del tuo Foglio Google nativo
ID_FOGLIO_DRIVE = "1igENI9rB2Lyqy8EUtnIWuWxwfRQZKyhCXpAnve3Wtrk"
FILE_CHIAVE_JSON = "chiave_drive.json"

# --- GESTIONE IMPOSTAZIONI PERSISTENTI ---
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

# --- TRADUZIONI MULTILINGUA GLOBALI COMPLETE ---
TEXTS = {
    "🇮🇹 🇮🇹 Italiano": {
        "welcome_title": "🇮🇹 Seleziona la Lingua",
        "welcome_btn": "Conferma e Continua",
        "title": "🛡️ Pannello di Controllo Alleanza",
        "login_title": "🔒 Accesso Gestionale Alleanza",
        "nick_label": "Nickname In-Game",
        "nick_placeholder": "Inserisci il tuo nick o il tuo nome",
        "pass_label": "Password di Accesso",
        "login_btn": "Accedi",
        "logout_btn": "Logout",
        "sidebar_settings": "⚙️ Impostazioni Settimana",
        "sidebar_mode_lbl": "Modalità",
        "sidebar_limit_save": "Limite di Risparmio",
        "sidebar_target_tech": "Target Donazioni Tech",
        "sidebar_obj_vs": "Obiettivo VS Spinta",
        "sidebar_events_lbl": "Eventi Programmati",
        "sidebar_btn_edit_params": "⚙️ Modifica Parametri Settimanali",
        "sidebar_btn_edit_squads": "⚔️ Inserisci / Modifica mie Squadre",
        "sidebar_reset_title": "🚨 Reset Totale Software",
        "sidebar_reset_desc": "Attenzione: questo comando azzererà completamente sia il Registro delle Squadre che il Database Condiviso dei Punteggi su Google Drive, lasciando intatte solo le intestazioni.",
        "sidebar_reset_chk": "Confermo reset totale",
        "sidebar_reset_btn": "🔴 AZZERA TUTTO (SQUADRE + DATABASE)",
        "sidebar_reset_success": "✅ Software azzerato con successo! Entrambi i database sono puliti.",
        "sidebar_reset_err_chk": "⚠️ Spunta la casella di conferma.",
        "wizard_title": "🧙‍♂️ Configurazione Iniziale Settimanale",
        "wizard_subtitle": "Imposta i parametri tattici per il calcolo dei punteggi di questa settimana.",
        "strat_choice": "Strategia VS Settimanale",
        "opt_spinta": "SPINTA COMPLETA",
        "opt_risparmio": "RISPARMIA / PROFILO BASSO",
        "target_vs_push": "Obiettivo VS Spinta (es. 100000000)",
        "limite_save_txt": "Limite di Risparmio (es. 45000000)",
        "target_tech": "Target Donazioni Tech (es. 10000)",
        "ev_planning_header": "📅 Pianificazione Eventi Settimanali:",
        "tot_ev_planned_lbl": "Totale Eventi di Gruppo Programmati",
        "confirm_config": "💾 Salva e Torna alla Dashboard",
        "tab_dati": "📊 Inserimento Punteggi",
        "tab_classifica": "🏆 Classifica",
        "tab_regole": "📚 Regolamento",
        "tab_squadre": "⚔️ Potenza Squadre",
        "tab_crescita": "📈 Crescita Squadre",
        "tab_chat": "🤖 Assistente IA",
        "tab_log": "📜 Registro Log",
        "save_drive_btn": "💾 SALVA TUTTE LE MODIFICHE SU GOOGLE DRIVE",
        "calc_btn": "🧮 CALCOLA CLASSIFICA SETTIMANALE",
        "download_pdf_btn": "📄 SCARICA REPORT SETTIMANALE IN PDF",
        "squadre_header": "⚔️ Gestione Potenza delle 4 Squadre",
        "crescita_header": "📈 Analisi Percentuale di Crescita Mensile",
        "save_squadre_btn": "💾 SALVA SQUADRE DEL MESE SU GOOGLE DRIVE",
        "export_xls_btn": "📊 SCARICA IN FORMATO EXCEL (.xlsx)",
        "export_pdf_btn": "📄 SCARICA IN FORMATO PDF (.pdf)",
        "success_drive": "✅ Connessione attiva al file su Google Drive!",
        "month_curr_label": "🗓️ Mese di Rilevazione Attuale",
        "month_prev_label": "🔍 Mese Precedente per Confronto",
        "month_edit_title": "📝 Inserimento / Modifica Potenza del Mese Selezionato",
        "month_analysis_title": "📈 Crescita Registrata:",
        "ai_prompt_label": "Domanda per l'assistente tattico su Last War:",
        "ai_send_btn": "Invia Domanda Tattica",
        "btn_empty_log": "🗑️ Svuota Registro Log",
        "rule_goal_title": "🎯 L'Obiettivo della Formula",
        "rule_goal_desc": "La formula per il calcolo del punteggio premia l'aderenza del giocatore alle direttive tattiche dell'alleanza.",
        "rule_vs_title": "1. ⚔️ Punteggio VS (Massimo 40 punti)",
        "rule_vs_desc": "* **FULL PUSH:** Chi raggiunge o supera il Target PUSH ottiene 40 punti.\n* **SAVE:** Chi rimane sotto il Limite SAVE ottiene 40 punti.",
        "rule_ev_title": "2. 📅 Presenza agli Eventi (Massimo 30 punti)",
        "rule_ev_desc": "Somma unificata delle presenze agli eventi di gruppo rispetto al totale programmato.",
        "rule_tech_title": "3. 🔬 Donazioni Tecnologiche (Massimo 20 punti)",
        "rule_tech_desc": "Chi raggiunge o supera il Target Donazioni Tech ottiene 20 punti.",
        "rule_bonus_title": "4. ⭐ Bonus Stella dell'Alleanza",
        "rule_bonus_desc": "Ogni Stella dell'Alleanza assegnata aggiunge +3 punti bonus diretti.",
        "rule_pen_title": "5. 🛑 Penalità e Detrazioni",
        "rule_pen_desc": "* Scudo Caduto / Violazione Regole: -30 punti.\n* Assenza Ingiustificata: -15 punti.\n* Mancata Risposta R4: -10 punti.\n* Giorni Inattività (>3gg): -5 punti per ogni giorno oltre i 3.",
        "m_portal_title": "⚔️ Portale Aggiornamento Potenza",
        "m_connected_as": "Connesso come:",
        "m_member_role": "(Membro)",
        "m_month_info": "🗓️ Stai inserendo la tua potenza relativa al mese:",
        "m_format_info": "💡 L'unità di misura è in **Milioni (M)**. Se lascerai vuoto, il sistema registrerà `0M`.",
        "m_pending_warn": "⌛ I tuoi dati sono in attesa di approvazione da parte di un Ufficiale R4/R5.",
        "m_approved_success": "✅ La tua potenza risulta approvata dagli ufficiali!",
        "m_not_submitted": "ℹ️ Non hai ancora inviato le squadre per questo mese o sono in fase di compilazione.",
        "m_sq1_label": "Squadra 1",
        "m_sq2_label": "Squadra 2",
        "m_sq3_label": "Squadra 3",
        "m_sq4_label": "Squadra 4",
        "m_input_squad_power": "Valore Potenza Squadra",
        "m_submit_btn": "💾 INVIA POTENZA",
        "m_save_success_approval": "Squadre inviate in approvazione - GRAZIE!",
        "m_save_success_direct": "Squadre salvate e aggiornate con successo - GRAZIE!",
        "pending_requests_warn": "🚨 **ATTENZIONE: Ci sono {count} richieste di potenza in attesa di approvazione!**",
        "btn_approve": "✅ Approva",
        "btn_approve_all": "✅ Approva Tutto",
        "btn_reject": "❌ Rifiuta",
        "opt_yes": "si",
        "opt_no": "no",
        "tipo_squadra_opzioni": ["", "Carri", "Missili", "Aerei", "Mista"],
        "db_legend_text": """
        📖 **LEGENDA COLONNE (Da sinistra a destra):**  
        * **N.** = N. Progressivo  
        * **Nickname** = Nome Giocatore  
        * **VS** = Punti VS inseriti (formattati con punti migliaia)  
        * **Comb.** = Combattente Sabato (si/no)  
        * **Tech** = Donazioni Tech inserite (formattate con punti migliaia)  
        * **Stelle** = Premi Stella  
        * **Scudo** = Penalità Scudo (si/no)  
        * **Ass.** = Assenza Ingiustificata (si/no)  
        * **No R4** = Mancata Risposta R4 (si/no)  
        * **Eventi** = Totale presenze eventi di gruppo  
        * **Inattiv.** = Giorni di inattività (>3gg = -5 pt/gg).
        """,
        "col_n": "N.",
        "col_nickname": "Nickname",
        "col_punti_vs": "VS",
        "col_combattente": "Comb.",
        "col_eventi": "Eventi",
        "col_donazioni": "Tech",
        "col_premi": "Stelle",
        "col_pen_scudo": "Scudo",
        "col_assenza": "Ass.",
        "col_mancata_risp": "No R4",
        "col_inattivita": "Inattiv.",
        "col_punteggio_tot": "Punteggio Totale",
        "col_pot_tot": "Potenza Totale",
        "col_growth_tot": "Crescita Totale %"
    },
    "🇬🇧 🇬🇧 English": {
        "welcome_title": "🇬🇧 Select Language",
        "welcome_btn": "Confirm and Continue",
        "title": "🛡️ Alliance Control Panel",
        "login_title": "🔒 Alliance Portal Login",
        "nick_label": "In-Game Nickname",
        "nick_placeholder": "Enter your nick or your name",
        "pass_label": "Access Password",
        "login_btn": "Login",
        "logout_btn": "Logout",
        "sidebar_settings": "⚙️ Weekly Settings",
        "sidebar_mode_lbl": "Mode",
        "sidebar_limit_save": "Save Limit",
        "sidebar_target_tech": "Tech Donations Target",
        "sidebar_obj_vs": "VS Push Target",
        "sidebar_events_lbl": "Planned Events",
        "sidebar_btn_edit_params": "⚙️ Edit Weekly Parameters",
        "sidebar_btn_edit_squads": "⚔️ Enter / Edit my Squads",
        "sidebar_reset_title": "🚨 Total Software Reset",
        "sidebar_reset_desc": "Warning: this command will completely reset both the Squads Registry and the Shared Scores Database on Google Drive, leaving only the headers intact.",
        "sidebar_reset_chk": "I confirm total reset",
        "sidebar_reset_btn": "🔴 RESET EVERYTHING (SQUADS + DATABASE)",
        "sidebar_reset_success": "✅ Software successfully reset! Both databases are clean.",
        "sidebar_reset_err_chk": "⚠️ Check the confirmation box.",
        "wizard_title": "🧙‍♂️ Initial Weekly Setup",
        "wizard_subtitle": "Set tactical parameters for this week's score calculation.",
        "strat_choice": "Weekly VS Strategy",
        "opt_spinta": "FULL PUSH",
        "opt_risparmio": "SAVE / LOW PROFILE",
        "target_vs_push": "VS Push Target",
        "limite_save_txt": "Save Limit",
        "target_tech": "Target Tech Donations",
        "ev_planning_header": "📅 Weekly Event Planning:",
        "tot_ev_planned_lbl": "Total Planned Group Events",
        "confirm_config": "💾 Save & Return to Dashboard",
        "tab_dati": "📊 Scores",
        "tab_classifica": "🏆 Leaderboard",
        "tab_regole": "📚 Rules",
        "tab_squadre": "⚔️ Squads Power",
        "tab_crescita": "📈 Squads Growth",
        "tab_chat": "🤖 AI Assistant",
        "tab_log": "📜 Activity Log",
        "save_drive_btn": "💾 SAVE ALL CHANGES TO GOOGLE DRIVE",
        "calc_btn": "🧮 CALCULATE WEEKLY LEADERBOARD",
        "download_pdf_btn": "📄 DOWNLOAD WEEKLY REPORT IN PDF",
        "squadre_header": "⚔️ Squads Power Management",
        "crescita_header": "📈 Monthly Growth Percentage Analysis",
        "save_squadre_btn": "💾 SAVE MONTHLY SQUADS TO GOOGLE DRIVE",
        "export_xls_btn": "📊 DOWNLOAD EXCEL FORMAT (.xlsx)",
        "export_pdf_btn": "📄 DOWNLOAD PDF FORMAT (.pdf)",
        "success_drive": "✅ Active connection to Google Drive file!",
        "month_curr_label": "🗓️ Current Evaluation Month",
        "month_prev_label": "🔍 Previous Month for Comparison",
        "month_edit_title": "📝 Enter / Edit Power for Selected Month",
        "month_analysis_title": "📈 Recorded Growth:",
        "ai_prompt_label": "Question for the tactical assistant about Last War:",
        "ai_send_btn": "Send Tactical Question",
        "btn_empty_log": "🗑️ Clear Log Register",
        "rule_goal_title": "🎯 Formula Objective",
        "rule_goal_desc": "The score formula rewards player compliance with alliance tactical directives.",
        "rule_vs_title": "1. ⚔️ VS Score (Max 40 points)",
        "rule_vs_desc": "* **FULL PUSH:** Hitting PUSH Target awards 40 points.\n* **SAVE:** Staying below SAVE Limit awards 40 points.",
        "rule_ev_title": "2. 📅 Event Attendance (Max 30 points)",
        "rule_ev_desc": "Unified sum of group event attendance vs planned total.",
        "rule_tech_title": "3. 🔬 Tech Donations (Max 20 points)",
        "rule_tech_desc": "Hitting Tech Target awards 20 points.",
        "rule_bonus_title": "4. ⭐ Alliance Star Bonus",
        "rule_bonus_desc": "Each Star awarded adds +3 direct bonus points.",
        "rule_pen_title": "5. 🛑 Penalties & Deductions",
        "rule_pen_desc": "* Shield Dropped: -30 points.\n* Unexcused Absence: -15 points.\n* No Response: -10 points.\n* Inactivity (>3 days): -5 points per day beyond 3.",
        "m_portal_title": "⚔️ Power Update Portal",
        "m_connected_as": "Connected as:",
        "m_member_role": "(Member)",
        "m_month_info": "🗓️ You are entering your power for the month:",
        "m_format_info": "💡 Unit of measurement is in **Millions (M)**. If left blank, it will default to `0M`.",
        "m_pending_warn": "⌛ Your submitted data is pending approval.",
        "m_approved_success": "✅ Your power is approved!",
        "m_not_submitted": "ℹ️ You have not submitted squads for this month yet.",
        "m_sq1_label": "Squad 1",
        "m_sq2_label": "Squad 2",
        "m_sq3_label": "Squad 3",
        "m_sq4_label": "Squad 4",
        "m_input_squad_power": "Squad Power Value",
        "m_submit_btn": "💾 SUBMIT POWER",
        "m_save_success_approval": "Squads submitted for approval - THANK YOU!",
        "m_save_success_direct": "Squads saved and updated successfully - THANK YOU!",
        "pending_requests_warn": "🚨 **WARNING: There are {count} power requests pending your approval!**",
        "btn_approve": "✅ Approve",
        "btn_approve_all": "✅ Approve All",
        "btn_reject": "❌ Reject",
        "opt_yes": "yes",
        "opt_no": "no",
        "tipo_squadra_opzioni": ["", "Tanks", "Missiles", "Aircraft", "Mixed"],
        "db_legend_text": """
        📖 **COLUMNS LEGEND (Left to Right Order):**  
        * **N.** = Progressive No.  
        * **Nickname** = Player Name  
        * **VS** = VS Points  
        * **Fighter** = Saturday Fighter (yes/no)  
        * **Tech** = Tech Donations  
        * **Stars** = Star Rewards  
        * **Shield** = Shield Penalty (yes/no)  
        * **Absence** = Unexcused Absence (yes/no)  
        * **No R4** = No R4 Response (yes/no)  
        * **Events** = Total Group Events Attendance  
        * **Inactive** = Days offline (>3d = -5 pts/d).
        """,
        "col_n": "N.",
        "col_nickname": "Nickname",
        "col_punti_vs": "VS",
        "col_combattente": "Fighter",
        "col_eventi": "Events",
        "col_donazioni": "Tech",
        "col_premi": "Stars",
        "col_pen_scudo": "Shield",
        "col_assenza": "Absence",
        "col_mancata_risp": "No R4",
        "col_inattivita": "Inactive",
        "col_punteggio_tot": "Total Score",
        "col_pot_tot": "Total Power",
        "col_growth_tot": "Total Growth %"
    },
    "🇩🇪 🇩🇪 Deutsch": {
        "welcome_title": "🇩🇪 Sprache auswählen",
        "welcome_btn": "Bestätigen und Fortfahren",
        "title": "🛡️ Allianz-Kontrollzentrum",
        "login_title": "🔒 Allianz-Portal Anmeldung",
        "nick_label": "In-Game-Nickname",
        "nick_placeholder": "Geben Sie Ihren Nick oder Namen ein",
        "pass_label": "Zugangspasswort",
        "login_btn": "Anmelden",
        "logout_btn": "Abmelden",
        "sidebar_settings": "⚙️ Wocheneinstellungen",
        "sidebar_mode_lbl": "Modus",
        "sidebar_limit_save": "Sparlimit",
        "sidebar_target_tech": "Tech-Spenden-Ziel",
        "sidebar_obj_vs": "VS-Push-Ziel",
        "sidebar_events_lbl": "Geplante Events",
        "sidebar_btn_edit_params": "⚙️ Wocheneinstellungen bearbeiten",
        "sidebar_btn_edit_squads": "⚔️ Meine Truppen eingeben / bearbeiten",
        "sidebar_reset_title": "🚨 Komplettes Software-Reset",
        "sidebar_reset_desc": "Achtung: Dieser Befehl setzt sowohl das Truppenregister als auch die gemeinsame Punktedatenbank auf Google Drive vollständig zurück, sodass nur die Kopfzeilen erhalten bleiben.",
        "sidebar_reset_chk": "Ich bestätige das komplette Reset",
        "sidebar_reset_btn": "🔴 ALLES ZURÜCKSETZEN (TRUPPEN + DATENBANK)",
        "sidebar_reset_success": "✅ Software erfolgreich zurückgesetzt! Beide Datenbanken sind sauber.",
        "sidebar_reset_err_chk": "⚠️ Aktivieren Sie das Bestätigungskästchen.",
        "wizard_title": "🧙‍♂️ Wöchentliche Erstkonfiguration",
        "wizard_subtitle": "Legen Sie die taktischen Parameter für diese Woche fest.",
        "strat_choice": "Wöchentliche VS-Strategie",
        "opt_spinta": "FULL PUSH",
        "opt_risparmio": "SAVE / LOW PROFILE",
        "target_vs_push": "VS-Push-Ziel",
        "limite_save_txt": "Sparlimit",
        "target_tech": "Tech-Spenden-Ziel",
        "ev_planning_header": "📅 Wöchentliche Event-Planung:",
        "tot_ev_planned_lbl": "Geplante Gruppenevents Gesamt",
        "confirm_config": "💾 Speichern & Zurück zum Dashboard",
        "tab_dati": "📊 Punkte",
        "tab_classifica": "🏆 Rangliste",
        "tab_regole": "📚 Regeln",
        "tab_squadre": "⚔️ Truppenstärke",
        "tab_crescita": "📈 Truppenwachstum",
        "tab_chat": "🤖 KI-Assistent",
        "tab_log": "📜 Protokoll",
        "save_drive_btn": "💾 ALLE ÄNDERUNGEN AUF GOOGLE DRIVE SPEICHERN",
        "calc_btn": "🧮 WOCHENRANGLISTE BERECHNEN",
        "download_pdf_btn": "📄 WOCHENBERICHT ALS PDF HERUNTERLADEN",
        "squadre_header": "⚔️ Verwaltung der Truppenstärke",
        "crescita_header": "📈 Monatliche Wachstumsanalyse (%)",
        "save_squadre_btn": "💾 MONATSTRUPPEN AUF GOOGLE DRIVE SPEICHERN",
        "export_xls_btn": "📊 IM EXCEL-FORMAT HERUNTERLADEN (.xlsx)",
        "export_pdf_btn": "📄 IM PDF-FORMAT HERUNTERLADEN (.pdf)",
        "success_drive": "✅ Aktive Verbindung zur Google Drive-Datei!",
        "month_curr_label": "🗓️ Aktueller Bewertungsmonat",
        "month_prev_label": "🔍 Vormonat zum Vergleich",
        "month_edit_title": "📝 Stärke für den ausgewählten Monat eingeben / bearbeiten",
        "month_analysis_title": "📈 Verzeichnetes Wachstum:",
        "ai_prompt_label": "Frage an den Taktikassistenten du Last War:",
        "ai_send_btn": "Taktische Frage Senden",
        "btn_empty_log": "🗑️ Log-Register leeren",
        "rule_goal_title": "🎯 Formelziel",
        "rule_goal_desc": "Die Punkteformel belohnt die Einhaltung taktischer Vorgaben.",
        "rule_vs_title": "1. ⚔️ VS-Punkte (Max. 40 Punkte)",
        "rule_vs_desc": "* **FULL PUSH:** 40 Punkte.\n* **SAVE:** 40 Punkte.",
        "rule_ev_title": "2. 📅 Event-Teilnahme (Max. 30 Punkte)",
        "rule_ev_desc": "Vereinigte Summe der Gruppenevent-Teilnahmen.",
        "rule_tech_title": "3. 🔬 Tech-Spenden (Max. 20 Punkte)",
        "rule_tech_desc": "Das Erreichen des Tech-Ziels gibt die vollen 20 Punkte.",
        "rule_bonus_title": "4. ⭐ Allianz-Stern-Bonus",
        "rule_bonus_desc": "Jeder verliehene Stern bringt +3 Punkte.",
        "rule_pen_title": "5. 🛑 Strafen & Abzüge",
        "rule_pen_desc": "* Schild gefallen: -30 Punkte.\n* Unentschuldigtes Fehlen: -15 Punkte.\n* Keine Antwort: -10 Punkte.\n* Inaktivität (>3 Tage): -5 Punkte pro Tag über 3.",
        "m_portal_title": "⚔️ Portal zur Truppenstärke-Aktualisierung",
        "m_connected_as": "Angemeldet as:",
        "m_member_role": "(Mitglied)",
        "m_month_info": "🗓️ Sie geben Ihre Truppenstärke für folgenden Monat ein:",
        "m_format_info": "💡 Einheit in Rohzahlen eingeben.",
        "m_pending_warn": "⌛ Daten warten auf Genehmigung.",
        "m_approved_success": "✅ Ihre Truppenstärke ist genehmigt!",
        "m_not_submitted": "ℹ️ Sie haben noch keine Truppen für diesen Monat eingereicht.",
        "m_sq1_label": "Truppe 1",
        "m_sq2_label": "Truppe 2",
        "m_sq3_label": "Truppe 3",
        "m_sq4_label": "Truppe 4",
        "m_input_squad_power": "Truppenstärke Wert",
        "m_submit_btn": "💾 TRUPPENSTÄRKE SENDEN",
        "m_save_success_approval": "Truppen zur Genehmigung eingereicht - DANKE!",
        "m_save_success_direct": "Truppen erfolgreich gespeichert und aktualisiert - DANKE!",
        "pending_requests_warn": "🚨 **ACHTUNG: Es gibt {count} Truppenstärke-Anträge, die auf Ihre Genehmigung warten!**",
        "btn_approve": "✅ Genehmigen",
        "btn_approve_all": "✅ Alle genehmigen",
        "btn_reject": "❌ Ablehnen",
        "opt_yes": "ja",
        "opt_no": "nein",
        "tipo_squadra_opzioni": ["", "Panzer", "Raketen", "Flieger", "Gemischt"],
        "db_legend_text": """
        📖 **SPALTENLEGENDE (Von links nach rechts):**  
        * **N.** = Fortlaufende Nr.  
        * **Nickname** = Spielername  
        * **VS** = VS-Punkte  
        * **Kämpfer** = Samstagskämpfer (ja/nein)  
        * **Tech** = Tech-Spenden  
        * **Sterne** = Sternen-Belohnungen  
        * **Schild** = Schild-Strafe (ja/nein)  
        * **Abwes.** = Unentschuldigte Abwesenheit (ja/nein)  
        * **Keine R4** = Keine R4-Antwort (ja/nein)  
        * **Events** = Gesamtzahl Gruppenevents  
        * **Inaktiv** = Tage offline (>3T = -5 Pkt/T).
        """,
        "col_n": "N.",
        "col_nickname": "Nickname",
        "col_punti_vs": "VS",
        "col_combattente": "Kämpfer",
        "col_eventi": "Events",
        "col_donazioni": "Tech",
        "col_premi": "Sterne",
        "col_pen_scudo": "Schild",
        "col_assenza": "Abwes.",
        "col_mancata_risp": "Keine R4",
        "col_inattivita": "Inaktiv",
        "col_punteggio_tot": "Gesamtpunkte",
        "col_pot_tot": "Gesamtstärke",
        "col_growth_tot": "Gesamtwachstum %"
    }
}

# --- FUNZIONE TRADUZIONE TIPI SQUADRA ---
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

# --- FUNZIONI DI NORMALIZZAZIONE INPUT (Estrae solo i numeri interi puri) ---
def normalizza_valore_vs(val_str):
    if val_str is None or str(val_str).strip() == "" or str(val_str).strip() == "0":
        return "0"
    digs = ''.join(filter(str.isdigit, str(val_str).upper().replace('M', '').replace('K', '').replace('.', '')))
    if not digs:
        return "0"
    return str(int(digs))

def normalizza_valore_tech(val_str):
    if val_str is None or str(val_str).strip() == "" or str(val_str).strip() == "0":
        return "0"
    digs = ''.join(filter(str.isdigit, str(val_str).upper().replace('M', '').replace('K', '').replace('.', '')))
    if not digs:
        return "0"
    return str(int(digs))

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
    if val_str is None or pd.isna(val_str) or str(val_str).strip() == "":
        return default_val
    if isinstance(val_str, (int, float)):
        if np.isnan(val_str) or np.isinf(val_str):
            return default_val
        return float(val_str)
    digs = ''.join(filter(str.isdigit, str(val_str).upper().replace('M', '').replace('K', '').replace('.', '')))
    if not digs:
        return default_val
    try:
        return float(digs)
    except ValueError:
        return default_val

def format_compact_number(val):
    if val is None or np.isnan(val) or np.isinf(val):
        return "0.00M"
    if val >= 1_000_000:
        return f"{val / 1_000_000:.2f}M".replace('.00M', 'M')
    elif val >= 1_000:
        return f"{val / 1_000:.1f}k".replace('.0k', 'k')
    return f"{val:.2f}M"

# --- GOOGLE DRIVE CONNECTION (SOLO FILE JSON LOCALE/GITHUB) ---
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

@st.cache_data(ttl=15, show_spinner=False)
def carica_dati_da_drive_cached():
    try:
        client = connetti_google_drive()
        if client:
            sh = client.open_by_key(ID_FOGLIO_DRIVE)
            sheet = sh.get_worksheet(0)
            rows = sheet.get_all_values()
            return rows, sheet, sh
    except Exception as e:
        st.error(f"❌ Errore apertura Foglio Google (ID: {ID_FOGLIO_DRIVE}): {e}")
        return None, None, None
    return None, None, None

def carica_dati_da_drive():
    rows, sheet, sh = carica_dati_da_drive_cached()
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
            vecchie_col = ["Maresciallo", "Desert_Storm", "Canyon", "Eventi_Guerra", "Eventi_Vari"]
            somma_vecchie = 0
            for vc in vecchie_col:
                if vc in df.columns:
                    somma_vecchie += pd.to_numeric(df[vc], errors='coerce').fillna(0)
            df["Eventi_Totali"] = somma_vecchie.astype(str) if any(vc in df.columns for vc in vecchie_col) else "0"

        colonne_richieste = ["Eventi_Totali", "Donazioni_Tech", "Premi_Stella", "Penalita_Scudo", "Assenza_Evento", "Mancata_Risposta_R4", "Giorni_Inattivita"]
        for c in colonne_richieste:
            if c not in df.columns:
                df[c] = "0" if c in ["Eventi_Totali", "Giorni_Inattivita", "Premi_Stella"] else ("no" if c != "Donazioni_Tech" else "10000")
                
        vecchie_da_rimuovere = [vc for vc in ["Maresciallo", "Desert_Storm", "Canyon", "Eventi_Guerra", "Eventi_Vari"] if vc in df.columns]
        if vecchie_da_rimuovere:
            df = df.drop(columns=vecchie_da_rimuovere)

        # Formattazione con separatore a puntino per le migliaia (es. 86.234.091)
        for col_f in ["Punti_VS", "Donazioni_Tech"]:
            if col_f in df.columns:
                df[col_f] = df[col_f].apply(lambda x: f"{int(parse_compact_number(x)):,}".replace(",", ".") if parse_compact_number(x) > 0 else "0")

        return df, sheet, sh
    else:
        client = connetti_google_drive()
        sh = client.open_by_key(ID_FOGLIO_DRIVE) if client else None
        sheet = sh.get_worksheet(0) if sh else None
        return pd.DataFrame(columns=["N.", "Nickname", "Punti_VS", "Eventi_Totali"]), sheet, sh

def salva_dati_su_drive(sheet, df):
    try:
        client_fresco = connetti_google_drive()
        if client_fresco:
            sh_fresco = client_fresco.open_by_key(ID_FOGLIO_DRIVE)
            sheet_fresco = sh_fresco.get_worksheet(0)
            
            df_pulito = df.copy()
            if "Nickname" in df_pulito.columns:
                df_pulito["Nickname"] = df_pulito["Nickname"].astype(str).str.replace("🔴 ", "").str.strip()

            # Rimozione totale di qualsiasi puntino, M o K prima del salvataggio su Drive
            for col_f in ["Punti_VS", "Donazioni_Tech"]:
                if col_f in df_pulito.columns:
                    df_pulito[col_f] = df_pulito[col_f].apply(lambda x: ''.join(filter(str.isdigit, str(x).upper().replace('M', '').replace('K', '').replace('.', ''))) or "0")

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

@st.cache_data(ttl=15, show_spinner=False)
def carica_squadre_da_drive_cached(sh_key):
    try:
        client = connetti_google_drive()
        if client:
            sh = client.open_by_key(sh_key)
            try:
                sheet_squadre = sh.worksheet("Registro_Squadre")
            except gspread.exceptions.WorksheetNotFound:
                sheet_squadre = sh.add_worksheet(title="Registro_Squadre", rows="1000", cols="15")
                headers_base = ["Mese_Anno", "Nickname", "Tipo_Squadra_1", "Squadra_1", "Tipo_Squadra_2", "Squadra_2", "Tipo_Squadra_3", "Squadra_3", "Tipo_Squadra_4", "Squadra_4", "Stato_Approvazione"]
                sheet_squadre.append_row(headers_base)
            rows = sheet_squadre.get_all_values()
            return rows, sheet_squadre
    except Exception:
        return None, None
    return None, None

def carica_squadre_da_drive(sh):
    rows, sheet_squadre = carica_squadre_da_drive_cached(ID_FOGLIO_DRIVE)
    if sheet_squadre is None:
        try:
            sheet_squadre = sh.worksheet("Registro_Squadre")
            rows = sheet_squadre.get_all_values()
        except Exception:
            return pd.DataFrame(), None

    headers_base = ["Mese_Anno", "Nickname", "Tipo_Squadra_1", "Squadra_1", "Tipo_Squadra_2", "Squadra_2", "Tipo_Squadra_3", "Squadra_3", "Tipo_Squadra_4", "Squadra_4", "Stato_Approvazione"]
    
    if not rows or len(rows) == 0 or (len(rows) == 1 and not any(rows[0])) or "Mese_Anno" not in [str(h).strip() for h in rows[0]]:
        sheet_squadre.clear()
        sheet_squadre.update(range_name="A1", values=[headers_base])
        return pd.DataFrame(columns=headers_base), sheet_squadre

    headers = [str(h).strip() for h in rows[0]]
    data = rows[1:]
    df = pd.DataFrame(data, columns=headers[:len(data[0])] if data and len(data) > 0 else headers)
    
    for col in headers_base:
        if col not in df.columns:
            if col == "Stato_Approvazione":
                df[col] = "Approvato"
            elif col == "Mese_Anno":
                df[col] = datetime.datetime.now().strftime("%Y-%m")
            else:
                df[col] = ""
            
    df = pulisci_dataframe(df)
    
    if "Nickname" in df.columns:
        active_r4 = st.session_state.get("ruolo") == "R4" or st.session_state.get("ruolo_originale") == "R4"
        current_user = st.session_state.get("nome_utente", "").strip().lower()
        df["Nickname"] = df["Nickname"].apply(lambda x: f"🔴 {x}" if (active_r4 and str(x).replace("🔴 ", "").strip().lower() == current_user) else str(x).replace("🔴 ", ""))

    return df, sheet_squadre

def salva_squadre_su_drive(sheet_squadre, df):
    try:
        client_fresco = connetti_google_drive()
        if client_fresco:
            sh_fresco = client_fresco.open_by_key(ID_FOGLIO_DRIVE)
            sheet_squadre = sh_fresco.worksheet("Registro_Squadre")
            
            df_pulito = df.copy()
            if "Nickname" in df_pulito.columns:
                df_pulito["Nickname"] = df_pulito["Nickname"].astype(str).str.replace("🔴 ", "").str.strip()

            sheet_squadre.clear()
            df_clean = pulisci_dataframe(df_pulito)
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
        "Punti_VS": "0", "Combattente_Sabato": "no", "Eventi_Totali": "0", 
        "Donazioni_Tech": "0", "Premi_Stella": 0, "Penalita_Scudo": "no", 
        "Assenza_Evento": "no", "Mancata_Risposta_R4": "no", "Giorni_Inattivita": "0"
    }
    for col, def_val in colonne_default.items():
        if col not in df.columns:
            df[col] = def_val

    punteggi_totali = []
    for _, row in df.iterrows():
        p_vs = parse_compact_number(str(row.get("Punti_VS", "0")))
        combattente = str(row.get("Combattente_Sabato", "no")).lower() in ["true", "1", "si", "yes", "ja", "sì"]
        
        try:
            tot_eventi_presenze = float(str(row.get("Eventi_Totali", "0")).strip() or 0)
        except ValueError:
            tot_eventi_presenze = 0.0
            
        donazioni = parse_compact_number(str(row.get("Donazioni_Tech", "0")))
        
        try:
            premi_stella = int(float(str(row.get("Premi_Stella", "0")).strip() or 0))
        except ValueError:
            premi_stella = 0
            
        penalita_scudo = str(row.get("Penalita_Scudo", "no")).lower() in ["true", "1", "si", "yes", "ja", "sì"]
        assenza_evento = str(row.get("Assenza_Evento", "no")).lower() in ["true", "1", "si", "yes", "ja", "sì"]
        mancata_risposta = str(row.get("Mancata_Risposta_R4", "no")).lower() in ["true", "1", "si", "yes", "ja", "sì"]
        
        try:
            giorni_inattivita = int(float(str(row.get("Giorni_Inattivita", "0")).strip() or 0))
        except ValueError:
            giorni_inattivita = 0

        # 1. Punteggio VS (Max 40 punti)
        if tipo_settimana in ["SPINTA COMPLETA", "FULL PUSH"]:
            s_vs = min(40.0, (p_vs / target_push) * 40.0) if target_push > 0 else 0.0
        else:
            if p_vs <= limite_save or combattente:
                s_vs = 40.0
            else:
                soglia_sforamento = limite_save * 0.5
                s_vs = max(0.0, 40.0 - ((p_vs - limite_save) / soglia_sforamento) * 20.0)

        # 2. Punteggio Eventi (Max 30 punti)
        s_eventi = min(30.0, (tot_eventi_presenze / tot_ev_planned) * 30.0)
        
        # 3. Punteggio Tech (Max 20 punti)
        s_tech = min(20.0, (donazioni / target_tech) * 20.0) if target_tech > 0 else 0.0
        
        # 4. Bonus Stella (+3 punti ciascuna)
        b_stella = premi_stella * 3.0
        
        # 5. Penalità
        malus_inattivita = max(0, (giorni_inattivita - 3) * 5.0) if giorni_inattivita > 3 else 0.0
        penalita = (30.0 if penalita_scudo else 0.0) + (15.0 if assenza_evento else 0.0) + (10.0 if mancata_risposta else 0.0) + malus_inattivita
        
        # Totale finale blindato
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
            str(pos),
            str(pos),
            clean_nick,
            str(row.get('Punti_VS', '0')),
            str(row.get('Donazioni_Tech', '0')),
            str(row.get('Premi_Stella', 0)),
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

# --- INIZIALIZZAZIONE STATO APPLICAZIONE ---
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
if "ruolo" not in st.session_state:
    st.session_state.ruolo = None
if "lang" not in st.session_state:
    st.session_state.lang = None
if "config_settimana" not in st.session_state:
    st.session_state.config_settimana = load_config()

st.set_page_config(page_title="Gestionale Last War Alleanza", layout="wide", page_icon="🛡️")

# --- STYLE CSS & RESTYLING GRAFICO A GRANDE IMPATTO ---
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
    .stDataEditor {
        border: 2px solid #2B6CB0 !important;
        border-radius: 8px !important;
        box-shadow: 0px 4px 12px rgba(43, 108, 176, 0.15) !important;
        background-color: #FAFCFF !important;
    }
    div[data-testid="stTable"] table { font-size: 15px !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🌐 SELETTORE LINGUA INIZIALE A TUTTO SCHERMO
# ==============================================================================
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

# --- LOGIN A DOPPIO LIVELLO ---
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

# --- INIZIALIZZAZIONE OGGETTO SPREADSHEET GLOBALE ---
spreadsheet_obj = connetti_google_drive().open_by_key(ID_FOGLIO_DRIVE) if connetti_google_drive() else None

# ==============================================================================
# 🚪 PORTALE MEMBRI
# ==============================================================================
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
            
        if not is_r4_origin:
            if has_submitted:
                if "In Attesa" in str(stato_att):
                    st.warning(T['m_pending_warn'])
                elif stato_att == "Approvato":
                    st.success(T['m_approved_success'])
            else:
                st.info(T['m_not_submitted'])

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
                st.error("🚫 Invio bloccato: spunta la casella di conferma per inoltrare comunque la richiesta con i tipi duplicati.")
                st.stop()

            if is_r4_origin:
                stato_richiesta = "Approvato"
            else:
                stato_richiesta = "In Attesa (⚠️ Duplicati)" if duplicati_presenti else "In Attesa"

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
                    "Tipo_Squadra_1": in_t1, "Squadra_1": norm_s1,
                    "Tipo_Squadra_2": in_t2, "Squadra_2": norm_s2,
                    "Tipo_Squadra_3": in_t3, "Squadra_3": norm_s3,
                    "Tipo_Squadra_4": in_t4, "Squadra_4": norm_s4,
                    "Stato_Approvazione": stato_richiesta
                }])
                df_squadre_agg = pd.concat([df_squadre, nuova_riga], ignore_index=True)
            
            if salva_squadre_su_drive(sheet_squadre_obj, df_squadre_agg):
                if is_r4_origin:
                    df_drive_attivo, sheet_obj_punti, _ = carica_dati_da_drive()
                    if df_drive_attivo is not None:
                        col_nick_dr = "Nickname" if "Nickname" in df_drive_attivo.columns else df_drive_attivo.columns[0]
                        set_esistenti_punti = set(df_drive_attivo[col_nick_dr].astype(str).str.replace("🔴 ", "").str.strip().str.lower())
                        if nick_user.lower() not in set_esistenti_punti:
                            riga_vs_nuova = pd.DataFrame([{
                                col_nick_dr: nick_user, "Punti_VS": "0", "Combattente_Sabato": "no",
                                "Eventi_Totali": "0", "Donazioni_Tech": "0", "Premi_Stella": "0", 
                                "Penalita_Scudo": "no", "Assenza_Evento": "no", "Mancata_Risposta_R4": "no", 
                                "Giorni_Inattivita": "0"
                            }])
                            df_drive_attivo = pd.concat([df_drive_attivo, riga_vs_nuova], ignore_index=True)
                            salva_dati_su_drive(sheet_obj_punti, df_drive_attivo)

                registra_log(nick_user, "Aggiornate squadre dal portale")
                msg_successo = T["m_save_success_direct"] if is_r4_origin else T["m_save_success_approval"]
                st.markdown(f"<p style='color: #2e7d32; font-weight: bold; font-size: 18px; margin-top: 15px; padding: 10px; background-color: #e8f5e9; border-radius: 5px; text-align: center;'>{msg_successo}</p>", unsafe_allow_html=True)
                st.stop()
    st.stop()

# ==============================================================================
# 🛡️ PANNELLO UFFICIALI R4/R5
# ==============================================================================
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
                "target_push_str": normalizza_valore_vs(w_target_vs),
                "limite_save_str": normalizza_valore_vs(w_limite_vs), 
                "target_tech_str": normalizza_valore_tech(w_target_tech),
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
        st.markdown(f"""
        **{T['sidebar_mode_lbl']}:** {cfg_attiva['tipo_settimana']}  
        **{T['sidebar_obj_vs']}:** {cfg_attiva['target_push_str']}  
        **{T['sidebar_target_tech']}:** {cfg_attiva['target_tech_str']}  
        **{T['sidebar_events_lbl']}:** 📅 {tot_ev_correnti}
        """)
    else:
        st.markdown(f"""
        **{T['sidebar_mode_lbl']}:** {cfg_attiva['tipo_settimana']}  
        **{T['sidebar_limit_save']}:** {cfg_attiva['limite_save_str']}  
        **{T['sidebar_target_tech']}:** {cfg_attiva['target_tech_str']}  
        **{T['sidebar_events_lbl']}:** 📅 {tot_ev_correnti}
        """)

    if st.button(T["sidebar_btn_edit_params"]):
        st.session_state.forza_wizard_modifica = True
        st.rerun()

    st.markdown("---")
    if st.button(T["sidebar_btn_edit_squads"]):
        st.session_state.ruolo_originale = "R4"
        st.session_state.ruolo = "Membro"
        st.rerun()

    # --- PULSANTE ROSSO DI EMERGENZA: AZZERAMENTO TOTALE ---
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
                            headers_squadre = ["Mese_Anno", "Nickname", "Tipo_Squadra_1", "Squadra_1", "Tipo_Squadra_2", "Squadra_2", "Tipo_Squadra_3", "Squadra_3", "Tipo_Squadra_4", "Squadra_4", "Stato_Approvazione"]
                            sheet_sq.update(range_name="A1", values=[headers_squadre])
                        except Exception:
                            pass

                        sheet_punti = sh_res.get_worksheet(0)
                        sheet_punti.clear()
                        headers_punti = ["N.", "Nickname", "Punti_VS", "Combattente_Sabato", "Eventi_Totali", "Donazioni_Tech", "Premi_Stella", "Penalita_Scudo", "Assenza_Evento", "Mancata_Risposta_R4", "Giorni_Inattivita"]
                        sheet_punti.update(range_name="A1", values=[headers_punti])

                        st.cache_data.clear()
                        st.success(T["sidebar_reset_success"])
                        st.rerun()
                except Exception as e:
                    st.error(f"Errore durante il reset totale: {e}")
            else:
                st.error(T["sidebar_reset_err_chk"])

    st.markdown("---")
    if st.button(T["logout_btn"]):
        st.session_state.autenticato = False
        st.session_state.ruolo = None
        st.session_state.lang = None
        if "ruolo_originale" in st.session_state:
            del st.session_state["ruolo_originale"]
        st.rerun()

# --- MENU SEPARATO E RIORDINATO ---
elenco_tabs = [T["tab_squadre"], T["tab_crescita"], T["tab_dati"], T["tab_classifica"], T["tab_chat"], T["tab_regole"]]
if is_admin:
    elenco_tabs.append(T["tab_log"])

tabs = st.tabs(elenco_tabs)
tab_squadre, tab_crescita, tab_dati, tab_report, tab_chat, tab_regole = tabs[0], tabs[1], tabs[2], tabs[3], tabs[4], tabs[5]
tab_log = tabs[6] if is_admin else None

# ==============================================================================
# 1. TAB POTENZA SQUADRE
# ==============================================================================
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
                        nick_app = str(df_squadre.loc[idx_att, "Nickname"]).replace("🔴 ", "").strip()
                        if nick_app and nick_app.lower() != "nan":
                            col_nick_dr = "Nickname" if "Nickname" in df_drive_attivo.columns else df_drive_attivo.columns[0]
                            set_esistenti_punti = set(df_drive_attivo[col_nick_dr].astype(str).str.replace("🔴 ", "").str.strip().str.lower())
                            if nick_app.lower() not in set_esistenti_punti:
                                riga_vs_nuova = pd.DataFrame([{
                                    col_nick_dr: nick_app, "Punti_VS": "0", "Combattente_Sabato": "no",
                                    "Eventi_Totali": "0", "Donazioni_Tech": "0", "Premi_Stella": "0", 
                                    "Penalita_Scudo": "no", "Assenza_Evento": "no", "Mancata_Risposta_R4": "no", 
                                    "Giorni_Inattivita": "0"
                                }])
                                df_drive_attivo = pd.concat([df_drive_attivo, riga_vs_nuova], ignore_index=True)

                    salva_squadre_su_drive(sheet_squadre_obj, df_squadre)
                    salva_dati_su_drive(sheet_obj_punti, df_drive_attivo)
                    registra_log(st.session_state.nome_utente, "Approvate tutte le richieste in blocco")
                    st.success("🎉 Tutte le richieste approvate e sincronizzate!")
                    st.rerun()

                st.markdown("---")
                for idx_att, riga_att in df_in_attesa.iterrows():
                    c_nick, c_ok, c_no = st.columns([3, 1, 1])
                    nick_membro = str(riga_att.get('Nickname', '')).strip()
                    
                    t1_r = traduci_tipo_squadra(riga_att.get('Tipo_Squadra_1', ''), st.session_state.lang)
                    v1_r = riga_att.get('Squadra_1', '')
                    t2_r = traduci_tipo_squadra(riga_att.get('Tipo_Squadra_2', ''), st.session_state.lang)
                    v2_r = riga_att.get('Squadra_2', '')
                    t3_r = traduci_tipo_squadra(riga_att.get('Tipo_Squadra_3', ''), st.session_state.lang)
                    v3_r = riga_att.get('Squadra_3', '')
                    t4_r = traduci_tipo_squadra(riga_att.get('Tipo_Squadra_4', ''), st.session_state.lang)
                    v4_r = riga_att.get('Squadra_4', '')
                    
                    stato_riga = str(riga_att.get('Stato_Approvazione', ''))
                    avviso_dup = " ⚠️ **[ANOMALIA: Tipi di squadra duplicati!]**" if "Duplicati" in stato_riga else ""

                    with c_nick:
                        st.markdown(f"👤 **{nick_membro}** ({riga_att.get('Mese_Anno')}){avviso_dup}  \n"
                                    f"⚔️ **1°** [{t1_r}]: `{v1_r}` | **2°** [{t2_r}]: `{v2_r}` | "
                                    f"**3°** [{t3_r}]: `{v3_r}` | **4°** [{t4_r}]: `{v4_r}`")
                    with c_ok:
                        if st.button(T["btn_approve"], key=f"app_{idx_att}"):
                            df_squadre.loc[idx_att, "Stato_Approvazione"] = "Approvato"
                            salva_squadre_su_drive(sheet_squadre_obj, df_squadre)
                            
                            clean_nick_membro = nick_membro.replace("🔴 ", "").strip()
                            if clean_nick_membro and clean_nick_membro.lower() != "nan":
                                col_nick_dr = "Nickname" if "Nickname" in df_drive_attivo.columns else df_drive_attivo.columns[0]
                                set_esistenti_punti = set(df_drive_attivo[col_nick_dr].astype(str).str.replace("🔴 ", "").str.strip().str.lower())
                                if clean_nick_membro.lower() not in set_esistenti_punti:
                                    riga_vs_nuova = pd.DataFrame([{
                                        col_nick_dr: clean_nick_membro, "Punti_VS": "0", "Combattente_Sabato": "no",
                                        "Eventi_Totali": "0", "Donazioni_Tech": "0", "Premi_Stella": "0", 
                                        "Penalita_Scudo": "no", "Assenza_Evento": "no", "Mancata_Risposta_R4": "no", 
                                        "Giorni_Inattivita": "0"
                                    }])
                                    df_drive_attivo = pd.concat([df_drive_attivo, riga_vs_nuova], ignore_index=True)
                                    salva_dati_su_drive(sheet_obj_punti, df_drive_attivo)

                            registra_log(st.session_state.nome_utente, f"Approvato utente {clean_nick_membro}")
                            st.rerun()
                    with c_no:
                        if st.button(T["btn_reject"], key=f"rej_{idx_att}"):
                            df_squadre = df_squadre.drop(idx_att)
                            salva_squadre_su_drive(sheet_squadre_obj, df_squadre)
                            st.rerun()
                st.markdown("---")

            mesi_anno = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"]
            mese_attuale_def = datetime.datetime.now().strftime("%Y-%m")
            
            mese_selezionato_sq = st.selectbox(T["month_curr_label"], mesi_anno, index=mesi_anno.index(mese_attuale_def) if mese_attuale_def in mesi_anno else 6, key="sel_mese_potenza")

            col_nick_punti = "Nickname" if "Nickname" in df_drive_attivo.columns else df_drive_attivo.columns[0]
            set_nick_punti = set(df_drive_attivo[col_nick_punti].dropna().astype(str).str.replace("🔴 ", "").str.strip().str.lower())
            set_nick_punti.discard("")
            set_nick_punti.discard("0")
            set_nick_punti.discard("nan")

            df_mese_curr_app = df_squadre[(df_squadre["Mese_Anno"] == mese_selezionato_sq) & (df_squadre["Stato_Approvazione"] == "Approvato")].copy()
            set_nick_squadre = set(df_mese_curr_app["Nickname"].dropna().astype(str).str.replace("🔴 ", "").str.strip().str.lower())
            set_nick_squadre.discard("")
            set_nick_squadre.discard("0")
            set_nick_squadre.discard("nan")

            mancanti_nelle_squadre = set_nick_punti - set_nick_squadre
            mancanti_nei_punti = set_nick_squadre - set_nick_punti

            if mancanti_nelle_squadre or mancanti_nei_punti:
                st.warning(f"⚠️ **ALERT: DISALLINEAMENTO PLAYER RILEVATO TRA DATABASE E SQUADRE**")
                if mancanti_nelle_squadre:
                    st.error(f"🔴 Player presenti in 'Inserimento Punteggi' ma **MANCANTI** nel mese {mese_selezionato_sq} delle Squadre: `{', '.join([p.capitalize() for p in mancanti_nelle_squadre])}`")
                if mancanti_nei_punti:
                    st.error(f"🔴 Player presenti nel mese {mese_selezionato_sq} delle Squadre ma **MANCANTI** in 'Inserimento Punteggi': `{', '.join([p.capitalize() for p in mancanti_nei_punti])}`")
                st.markdown("---")

            st.markdown(f"#### {T['month_edit_title']}")

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

            df_squadre_edit = st.data_editor(
                df_mese_curr,
                column_config=column_config_sq,
                num_rows="dynamic",
                width="stretch",
                key="editor_squadre"
            )
            
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
                    for _, row_ed in df_pulita_edit.iterrows():
                        nick_ed = str(row_ed.get("Nickname", "")).replace("🔴 ", "").strip()
                        if nick_ed and nick_ed != "0" and nick_ed.lower() != "nan":
                            col_nick_dr = "Nickname" if "Nickname" in df_drive_attivo.columns else df_drive_attivo.columns[0]
                            set_esistenti_punti = set(df_drive_attivo[col_nick_dr].astype(str).str.replace("🔴 ", "").str.strip().str.lower())
                            if nick_ed.lower() not in set_esistenti_punti:
                                riga_vs_nuova = pd.DataFrame([{
                                    col_nick_dr: nick_ed, "Punti_VS": "0", "Combattente_Sabato": "no",
                                    "Eventi_Totali": "0", "Donazioni_Tech": "0", "Premi_Stella": "0", 
                                    "Penalita_Scudo": "no", "Assenza_Evento": "no", "Mancata_Risposta_R4": "no", 
                                    "Giorni_Inattivita": "0"
                                }])
                                df_drive_attivo = pd.concat([df_drive_attivo, riga_vs_nuova], ignore_index=True)
                                salva_dati_su_drive(sheet_obj_punti, df_drive_attivo)

                    st.success(f"🎉 Dati salvati e approvati istantaneamente per il mese {mese_selezionato_sq}!")
                    st.rerun()

            st.markdown("---")
            st.markdown("#### 📋 Tabella Ufficiale Potenza Squadre del Mese")
            
            df_potenza_vis = df_squadre[(df_squadre["Mese_Anno"] == mese_selezionato_sq) & (df_squadre["Stato_Approvazione"] == "Approvato")].copy()
            if not df_potenza_vis.empty:
                cols_potenza_clean = ["Nickname", "Tipo_Squadra_1", "Squadra_1", "Tipo_Squadra_2", "Squadra_2", "Tipo_Squadra_3", "Squadra_3", "Tipo_Squadra_4", "Squadra_4"]
                df_potenza_vis = df_potenza_vis[[c for c in cols_potenza_clean if c in df_potenza_vis.columns]]
                
                for i in range(1, 5):
                    col_t_s = f"Tipo_Squadra__{i}" if f"Tipo_Squadra__{i}" in df_potenza_vis.columns else f"Tipo_Squadra_{i}"
                    if col_t_s in df_potenza_vis.columns:
                        df_potenza_vis[col_t_s] = df_potenza_vis[col_t_s].apply(lambda x: traduci_tipo_squadra(x, st.session_state.lang))

                df_potenza_vis.insert(0, T["col_n"], range(1, len(df_potenza_vis) + 1))
                st.dataframe(df_potenza_vis, width="stretch")

                col_exp_pot_xls, col_exp_pot_pdf = st.columns(2)
                with col_exp_pot_xls:
                    buffer_pot_excel = io.BytesIO()
                    with pd.ExcelWriter(buffer_pot_excel, engine='openpyxl') as writer:
                        df_potenza_vis.to_excel(writer, index=False, sheet_name="Potenza_Squadre")
                    buffer_pot_excel.seek(0)
                    st.download_button(
                        label=T["export_xls_btn"], data=buffer_pot_excel,
                        file_name=f"Potenza_Squadre_{mese_selezionato_sq}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        width="stretch"
                    )
                with col_exp_pot_pdf:
                    pdf_potenza_data = genera_pdf_squadre(df_potenza_vis, mese_selezionato_sq)
                    st.download_button(
                        label=T["export_pdf_btn"], data=pdf_potenza_data,
                        file_name=f"Potenza_Squadre_{mese_selezionato_sq}.pdf",
                        mime="application/pdf",
                        width="stretch"
                    )

# ==============================================================================
# 2. TAB CRESCITA SQUADRE
# ==============================================================================
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

            st.markdown(f"### {T['month_analysis_title']} {mese_selezionato_cr} / {mese_confronto_cr}")
            
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
                        col_nome_perc = f"% growth {col_nome_sq}" if "English" in st.session_state.lang else (f"% Wachstum {col_nome_sq}" if "Deutsch" in st.session_state.lang else f"% crescita {col_nome_sq}")
                        
                        pot_curr = sq["potenza"]
                        t_key = sq["tipo_key"]
                        
                        if t_key in mappa_prec and mappa_prec[t_key] > 0:
                            pot_prec = mappa_prec[t_key]
                            crescita = ((pot_curr - pot_prec) / pot_prec) * 100.0
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
                    df_risultati = pd.DataFrame(risultati_crescita)
                    df_risultati = df_risultati.sort_values(by="Valore_Totale_Num", ascending=False) if "Valore_Totale_Num" in df_risultati.columns else df_risultati
                    df_visibile = df_risultati.drop(columns=["Valore_Totale_Num"]) if "Valore_Totale_Num" in df_risultati.columns else df_risultati
                    df_visibile.insert(0, T["col_n"], range(1, len(df_visibile) + 1))
                    
                    st.dataframe(df_visibile, width="stretch")
                    
                    st.markdown("---")
                    col_exp_xls, col_exp_pdf = st.columns(2)
                    with col_exp_xls:
                        buffer_excel = io.BytesIO()
                        with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
                            df_visibile.to_excel(writer, index=False, sheet_name="Crescita_Squadre")
                        buffer_excel.seek(0)
                        st.download_button(
                            label=T["export_xls_btn"], data=buffer_excel,
                            file_name=f"Crescita_Squadre_{mese_selezionato_cr}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary",
                            width="stretch"
                        )
                    with col_exp_pdf:
                        pdf_squadre_data = genera_pdf_squadre(df_visibile, mese_selezionato_cr, mese_confronto_cr)
                        st.download_button(
                            label=T["export_pdf_btn"], data=pdf_squadre_data,
                            file_name=f"Crescita_Squadre_{mese_selezionato_cr}.pdf",
                            mime="application/pdf",
                            width="stretch"
                        )

# 3. TAB DATI GOOGLE DRIVE
with tab_dati:
    st.subheader("☁️ Database Condiviso Google Drive")
    df_drive, sheet_obj, spreadsheet_obj = carica_dati_da_drive()
    if df_drive is not None:
        st.success(T["success_drive"])
        
        st.markdown(T["db_legend_text"])

        # --- SISTEMA DI SICUREZZA R4: Controllo cifre anomale ---
        anomalie_rilevate = []
        for idx, row in df_drive.iterrows():
            nick_chk = str(row.get("Nickname", ""))
            vs_chk = str(row.get("Punti_VS", "")).replace(".", "").strip()
            tech_chk = str(row.get("Donazioni_Tech", "")).replace(".", "").strip()
            
            if vs_chk and vs_chk != "0" and len(vs_chk) < 7:
                anomalie_rilevate.append(f"⚠️ **{nick_chk}**: Il valore VS (`{row.get('Punti_VS')}`) sembra troppo corto (attese 7-9 cifre).")
            if tech_chk and tech_chk != "0" and len(tech_chk) < 4:
                anomalie_rilevate.append(f"⚠️ **{nick_chk}**: Le donazioni Tech (`{row.get('Donazioni_Tech')}`) sembrano troppo corte (attese 4-5 cifre).")

        if anomalie_rilevate:
            with st.expander("🚨 **AVVISI DI SICUREZZA R4: Valori potenzialmente errati rilevati!**", expanded=True):
                st.markdown("Sono stati inseriti numeri che non rispettano la lunghezza standard. Verificali prima di calcolare la classifica:")
                for avv in anomalie_rilevate:
                    st.markdown(f"- {avv}")
                st.info("💡 Se i dati sono corretti, puoi procedere altrimenti modificali direttamente nella tabella sottostante.")

        opzioni_eventi = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
        opzioni_yes_no = [T["opt_no"], T["opt_yes"]]
        opzioni_giorni = ["0", "1", "2", "3", "4", "5", "6", "7"]
        
        column_configuration = {
            T["col_n"]: st.column_config.NumberColumn(T["col_n"], width="small", disabled=True),
            "Nickname": st.column_config.TextColumn(T["col_nickname"], width="medium", required=True),
            "Punti_VS": st.column_config.TextColumn(T["col_punti_vs"], width="small"),
            "Combattente_Sabato": st.column_config.SelectboxColumn(T["col_combattente"], options=opzioni_yes_no, width="small"),
            "Donazioni_Tech": st.column_config.TextColumn(T["col_donazioni"], width="small"),
            "Premi_Stella": st.column_config.TextColumn(T["col_premi"], width="small"),
            "Penalita_Scudo": st.column_config.SelectboxColumn(T["col_pen_scudo"], options=opzioni_yes_no, width="small"),
            "Assenza_Evento": st.column_config.SelectboxColumn(T["col_assenza"], options=opzioni_yes_no, width="small"),
            "Mancata_Risposta_R4": st.column_config.SelectboxColumn(T["col_mancata_risp"], options=opzioni_yes_no, width="small"),
            "Eventi_Totali": st.column_config.SelectboxColumn(T["col_eventi"], options=opzioni_eventi, width="small"),
            "Giorni_Inattivita": st.column_config.SelectboxColumn(T["col_inattivita"], options=opzioni_giorni, width="small"),
        }
        
        df_modificato = st.data_editor(df_drive, column_config=column_configuration, num_rows="dynamic", width="stretch", key="editor_drive_custom")
        
        if st.button(T["save_drive_btn"], type="primary"):
            if "Punti_VS" in df_modificato.columns:
                df_modificato["Punti_VS"] = df_modificato["Punti_VS"].apply(normalizza_valore_vs)
            if "Donazioni_Tech" in df_modificato.columns:
                df_modificato["Donazioni_Tech"] = df_modificato["Donazioni_Tech"].apply(normalizza_valore_tech)
                
            if salva_dati_su_drive(sheet_obj, df_modificato):
                st.success("🎉 Salvato su Google Drive!")
                st.rerun()

# 4. TAB CLASSIFICA
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
            col_n_str = T["col_n"]
            if col_n_str in df_mostra.columns:
                df_mostra = df_mostra.drop(columns=[col_n_str])
            df_mostra.insert(0, col_n_str, range(1, len(df_mostra) + 1))
            st.dataframe(df_mostra, width="stretch", height=450)
            
            pdf_data = genera_report_pdf(st.session_state.df_calcolato_raw, st.session_state.config_settimana["tipo_settimana"])
            st.download_button(label=T["download_pdf_btn"], data=pdf_data, file_name="Report.pdf", mime="application/pdf", type="primary", width="stretch")

# 5. TAB CHAT IA
with tab_chat:
    st.subheader(T["tab_chat"])
    prompt_utente = st.text_input(T["ai_prompt_label"])
    if st.button(T["ai_send_btn"], type="primary") and prompt_utente:
        if GEMINI_API_KEY:
            try:
                client = genai.Client(api_key=GEMINI_API_KEY)
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=prompt_utente
                )
                st.info(response.text)
            except Exception as e:
                st.error(f"❌ Errore IA: {e}")
        else:
            st.error("⚠️ Chiave API Gemini non configurata nei Secrets.")

# 6. TAB REGOLAMENTO & FORMULE
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

# 7. TAB LOG
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