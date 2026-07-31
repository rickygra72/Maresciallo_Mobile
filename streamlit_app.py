def calcola_punteggi_alleanza(df, config_dict):
    df = df.copy()
    tipo_settimana = config_dict.get("tipo_settimana", "SPINTA COMPLETA")
    target_push = parse_compact_number(config_dict.get("target_push_str", "100M"), 100_000_000.0)
    limite_save = parse_compact_number(config_dict.get("limite_save_str", "45M"), 45_000_000.0)
    target_tech = parse_compact_number(config_dict.get("target_tech_str", "10k"), 10_000.0)
    
    tot_ev_planned = config_dict.get("tot_eventi_programmati", 5)
    if tot_ev_planned <= 0:
        tot_ev_planned = 1

    colonne_default = {
        "Punti_VS": "0M", "Combattente_Sabato": "no", "Eventi_Totali": "0", 
        "Donazioni_Tech": "10k", "Premi_Stella": 0, "Penalita_Scudo": "no", 
        "Assenza_Evento": "no", "Mancata_Risposta_R4": "no", "Giorni_Inattivita": "0"
    }
    for col, def_val in colonne_default.items():
        if col not in df.columns:
            df[col] = def_val

    punteggi_totali = []
    for _, row in df.iterrows():
        # Parsing sicuro dei valori utente
        p_vs = parse_compact_number(str(row.get("Punti_VS", "0")))
        combattente = str(row.get("Combattente_Sabato", "no")).lower() in ["true", "1", "si", "yes", "ja", "sì"]
        
        try:
            tot_eventi_presenze = float(str(row.get("Eventi_Totali", "0")).strip() or 0)
        except ValueError:
            tot_eventi_presenze = 0.0
            
        donazioni = parse_compact_number(str(row.get("Donazioni_Tech", "0")))
        premi_stella = int(parse_compact_number(str(row.get("Premi_Stella", "0"))))
        
        penalita_scudo = str(row.get("Penalita_Scudo", "no")).lower() in ["true", "1", "si", "yes", "ja", "sì"]
        assenza_evento = str(row.get("Assenza_Evento", "no")).lower() in ["true", "1", "si", "yes", "ja", "sì"]
        mancata_risposta = str(row.get("Mancata_Risposta_R4", "no")).lower() in ["true", "1", "si", "yes", "ja", "sì"]
        
        try:
            giorni_inattivita = int(parse_compact_number(str(row.get("Giorni_Inattivita", "0"))))
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