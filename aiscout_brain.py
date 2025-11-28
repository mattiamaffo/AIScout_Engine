"""
AIScout Brain - Modulo Cloud
Fornisce funzioni per ricerca similarità, generazione report e Routing intelligente.
Configurato per Groq (LLM), FastEmbed (Embeddings), Qdrant Cloud.
"""

import os
import sys
import uuid
import time
import joblib # type: ignore
import pandas as pd # type: ignore
import dspy # type: ignore
from dotenv import load_dotenv # type: ignore
from tavily import TavilyClient # type: ignore
from qdrant_client import QdrantClient, models # type: ignore
from fastembed import TextEmbedding # type: ignore

# Carica variabili d'ambiente
load_dotenv()

# --- CONFIGURAZIONE CLOUD ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

COLLECTION_NAME = "scouting_reports"
GROQ_MODEL = "llama-3.3-70b-versatile" 
VECTOR_SIZE = 384 

# --- SINGLETON PATTERN PER INIZIALIZZAZIONE ---
_INITIALIZED = False
_sim_engine = None
_df_main = None
_tavily = None
_qdrant = None
_embedding_model = None
_scout_bot = None
_router_bot = None  # <--- NUOVO

def _initialize():
    """Inizializza tutti i componenti (lazy loading)."""
    global _INITIALIZED, _sim_engine, _df_main, _tavily, _qdrant, _embedding_model, _scout_bot, _router_bot, _identikit_bot
    
    if _INITIALIZED:
        return
    
    print("[INIT] Caricamento AIScout Brain...", file=sys.stderr)
    
    # 1. Carica dati e motore similarità
    try:
        import data
        from SimEngine import SimilarityEngine
        
        if data.DATABASE_DF.empty:
            data.load_data()
            
        _df_main = data.DATABASE_DF
        artifacts_path = data.ARTIFACTS_DIR
        
        _sim_engine = SimilarityEngine(artifacts_dir=artifacts_path)
        _sim_engine._ensure_artifacts_loaded()
        print("[INIT] ✓ SimEngine caricato", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] SimEngine: {e}", file=sys.stderr)
        raise
    
    # 2. Configura DSPy con Groq
    try:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY non trovata nel .env")
        
        lm = dspy.LM(model=f'groq/{GROQ_MODEL}', api_key=GROQ_API_KEY, temperature=0.0) # Temp 0 per il router è meglio
        dspy.configure(lm=lm)
        
        # --- CLASSI DSPy ---
        class ScoutingSignature(dspy.Signature):
            """Senior Football Scout analysis. RESPOND STRICTLY IN ITALIAN."""
            player_name = dspy.InputField()
            raw_notes = dspy.InputField()
            player_profile = dspy.OutputField(desc="In Italian")
            tactical_analysis = dspy.OutputField(desc="In Italian")
            key_strengths = dspy.OutputField(desc="In Italian")
            weaknesses = dspy.OutputField(desc="In Italian")
            final_verdict = dspy.OutputField(desc="In Italian")
        
        class ScoutBot(dspy.Module):
            def __init__(self):
                super().__init__()
                self.prog = dspy.ChainOfThought(ScoutingSignature)
            def forward(self, name, notes):
                return self.prog(player_name=name, raw_notes=notes)

        class IdentikitTranslatorSignature(dspy.Signature):
            """
            You are a Football Data Analyst. Translate the user's natural language description into statistical metrics (p90), PLAYING STYLE, and FILTERS.
            
            CRITICAL RULES FOR STATS (CONVERSION):
            - The database uses PER 90 MINUTES metrics (x90).
            - If user says ABSOLUTE numbers (e.g. "10 goals", "8 assists"), CONVERT them to p90 assuming ~20-25 full games (approx 2000 mins).
            - Example: "10 goals" -> 10/20 = 0.5 (Set value to 0.5).
            - Example: "5 assists" -> 5/20 = 0.25 (Set value to 0.25).
            - If user uses Adjectives:
            - "Good/Buono" -> 60th percentile (e.g. Gls=0.25, TklW=1.5)
            - "High/Alto/Tanti" -> 85th percentile (e.g. Gls=0.45, TklW=2.5)
            - "Elite/Top" -> 95th percentile (e.g. Gls=0.70)

            CRITICAL RULES FOR STYLE (STRICT MAP):
            Map the user's description to one of these specific styles ONLY if explicitly requested:
            - FW: 'Bomber', 'Seconda Punta', 'Ala d\'Attacco', 'Attaccante di Manovra', 'Attaccante d\'Area'
            - MF: 'Regista', 'Mediano', 'Centrocampista Box-to-Box', 'Trequartista', 'Centrocampista di Equilibrio', 'Centrocampista di Quantità'
            - DF: 'Stopper', 'Difensore Centrale Impostatore', 'Terzino Difensivo', 'Esterno a Tutta Fascia'
            - GK: 'Portiere Moderno', 'Portiere Tradizionale'
            If the request is generic (e.g. "Un attaccante"), output 'None'.

            CRITICAL RULES FOR FILTERS:
            - Extract Age constraints (e.g. "Under 23" -> max_age=23).
            - Extract League (Comp) and Nation if explicitly mentioned (e.g. "In Serie A", "Brasilian").
            """
            user_description = dspy.InputField(desc="User's request (e.g. 'Attaccante da 10 gol in Serie A under 21')")
            
            role_code = dspy.OutputField(desc="Must be one of: FW, MF, DF, GK")
            target_style = dspy.OutputField(desc="Specific style name from the list above OR 'None'")
            
            # Nuovi campi per i filtri
            min_age = dspy.OutputField(desc="Minimum age (integer) or 'None'")
            max_age = dspy.OutputField(desc="Maximum age (integer) or 'None'")
            league_filter = dspy.OutputField(desc="Specific league name (e.g. 'Serie A') or 'None'")
            nation_filter = dspy.OutputField(desc="Specific nationality (e.g. 'Brazil', 'ITA') or 'None'")
            
            # Feature statistiche
            feature_1_name = dspy.OutputField(desc="Name of 1st metric (e.g. Gls, Ast, TklW, Int, PrgP, xG)")
            feature_1_value = dspy.OutputField(desc="Float value for feature 1 (converted to p90)")
            feature_2_name = dspy.OutputField(desc="Name of 2nd metric (or 'None')")
            feature_2_value = dspy.OutputField(desc="Float value for feature 2")
            feature_3_name = dspy.OutputField(desc="Name of 3rd metric (or 'None')")
            feature_3_value = dspy.OutputField(desc="Float value for feature 3")

        class IdentikitBot(dspy.Module):
            def __init__(self):
                super().__init__()
                self.prog = dspy.ChainOfThought(IdentikitTranslatorSignature)
            def forward(self, description):
                return self.prog(user_description=description)
        
        # --- ROUTER INTELLIGENTE (Fix: Gestione Filtri) ---
        class RouterSignature(dspy.Signature):
            """
            You are an AI Orchestrator for a Football Scouting App.
            Classify the user query into a specific TOOL and extract the PLAYER NAME.
            
            CRITICAL RULES FOR CLASSIFICATION:
            1. If the user mentions a specific existing player to compare (e.g. "Similar to Zirkzee"), use 'SEARCH_SIMILAR'.
            2. If the user wants an analysis of a specific player (e.g. "Report on Zirkzee"), use 'GET_REPORT'.
            3. If the user asks for a LIST of players based on criteria (Role, Nation, League, Age, Stats), use 'CREATE_IDENTIKIT'.
            - Example: "French players in Serie A" -> CREATE_IDENTIKIT
            - Example: "Young strikers" -> CREATE_IDENTIKIT
            - Example: "Find me a defender" -> CREATE_IDENTIKIT
            4. FOR NATION: Always convert the country name to its 3-LETTER ISO/FIFA CODE uppercase.
                - User: "Francia" -> Output: "FRA"
                - User: "Germany" -> Output: "GER"
                - User: "Olanda"  -> Output: "NED"
                - User: "Spagna"  -> Output: "ESP"
            5. Use 'CHAT' ONLY for greetings ("Hi", "Ciao") or general questions about the AI itself. Do NOT use CHAT for player searches.
            """
            user_query = dspy.InputField()
            
            tool_selected = dspy.OutputField(desc="Must be exactly one of: 'SEARCH_SIMILAR', 'GET_REPORT', 'CREATE_IDENTIKIT', 'CHAT'")
            player_name = dspy.OutputField(desc="The name of the target player extracted from query (for SEARCH/REPORT). Leave empty for IDENTIKIT/CHAT.")
            nation_filter = dspy.OutputField(desc="The 3-letter uppercase Country Code (e.g. FRA, BRA, ITA).")
            chat_reply = dspy.OutputField(desc="If tool is CHAT, write a friendly reply here IN ITALIAN. Otherwise leave empty.")

        class RouterBot(dspy.Module):
            def __init__(self):
                super().__init__()
                self.prog = dspy.ChainOfThought(RouterSignature)
            def forward(self, query):
                return self.prog(user_query=query)

        _scout_bot = ScoutBot()
        _router_bot = RouterBot() # Inizializziamo il router
        _identikit_bot = IdentikitBot()
        print("[INIT] ✓ DSPy & Router configurati (Groq)", file=sys.stderr)

    except Exception as e:
        print(f"[ERROR] DSPy/Groq: {e}", file=sys.stderr)
        raise
    
    # 3. Client Esterni
    try:
        _tavily = TavilyClient(api_key=TAVILY_API_KEY)
        _qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        
        if not _qdrant.collection_exists(COLLECTION_NAME):
            _qdrant.create_collection(collection_name=COLLECTION_NAME, vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE))
        
        _qdrant.create_payload_index(collection_name=COLLECTION_NAME, field_name="player_name", field_schema=models.PayloadSchemaType.KEYWORD)
        print("[INIT] ✓ Tavily & Qdrant configurati", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] External Clients: {e}", file=sys.stderr)
        raise
    
    # 4. FastEmbed
    try:
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        print("[INIT] ✓ FastEmbed caricato", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] FastEmbed: {e}", file=sys.stderr)
        raise
    
    _INITIALIZED = True
    print("[INIT] ✓ AIScout Brain pronto\n", file=sys.stderr)


def initialize():
    """Wrapper pubblico per l'inizializzazione."""
    _initialize()

# --- FUNZIONI CORE ---

def cerca_simili_statistici(nome_giocatore: str) -> str:
    _initialize()
    try:
        print(f"[DEBUG] Cerco simili a: {nome_giocatore}...") # DEBUG
        
        df_res, player_style = _sim_engine.find_similar_players(nome_giocatore, k=5)
        
        # DEBUG: Stampiamo cosa ha restituito il motore
        print(f"[DEBUG] Righe trovate: {len(df_res)}")
        if not df_res.empty:
            print(f"[DEBUG] Colonne disponibili: {df_res.columns.tolist()}")
            print(f"[DEBUG] Primo risultato:\n{df_res.iloc[0]}")

        if df_res.empty:
            return f"Nessun giocatore simile trovato per '{nome_giocatore}'."
        
        cols_to_show = ['Player', 'Team', 'Comp', 'Age', 'Similarita (Distanza)']
        # Aggiungiamo 'Valore_Mercato' se c'è, che è utile
        if 'Valore_Mercato' in df_res.columns:
            cols_to_show.append('Valore_Mercato')

        cols_existing = [c for c in cols_to_show if c in df_res.columns]
        
        result = f"**Stile di Gioco:** {player_style}\n\n" if player_style else ""
        result += df_res[cols_existing].to_markdown(index=False)
        
        return result
        
    except Exception as e:
        print(f"[ERROR] cerca_simili_statistici: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc() # Stampa l'errore completo
        return f"Errore nella ricerca: {str(e)}"

def ottieni_report_tattico(nome_giocatore: str) -> str:
    _initialize()
    print(f"[LOG] Report richiesto per: {nome_giocatore}", file=sys.stderr)
    
    # 1. Cache
    try:
        hits = _qdrant.scroll(collection_name=COLLECTION_NAME, scroll_filter=models.Filter(must=[models.FieldCondition(key="player_name", match=models.MatchValue(value=nome_giocatore))]), limit=1)[0]
        if hits:
            return f"FONTE: MEMORIA INTERNA\n\n{hits[0].payload['full_text']}"
    except Exception:
        pass
    
    # 2. Disambiguazione
    search_context = ""
    try:
        player_row = _df_main[_df_main['Player'].str.lower() == nome_giocatore.lower()].head(1)
        if not player_row.empty:
            search_context = f"{player_row.iloc[0]['Team']} {player_row.iloc[0]['Pos']}"
    except Exception:
        pass
    
    # 3. Web
    try:
        response = _tavily.search(query=f"{nome_giocatore} {search_context} tactical analysis scouting report style of play", max_results=5, include_raw_content=True)
        raw_notes = "\n".join([r['content'] for r in response['results']])
        sources = "\n".join([f"- {r['url']}" for r in response['results']])
    except Exception as e:
        return f"Errore ricerca web: {str(e)}"
    
    # 4. GenAI
    try:
        notes_with_context = f"CONTEXT: Player is {nome_giocatore}, plays for {search_context}.\nLANGUAGE: ITALIAN (Must write the report in Italian).\n\nRAW NOTES:\n{raw_notes}"
        pred = _scout_bot(name=nome_giocatore, notes=notes_with_context)
        final_report = f"# REPORT: {nome_giocatore} ({search_context})\n\n## PROFILO\n{pred.player_profile}\n\n## TATTICA\n{pred.tactical_analysis}\n\n## PRO\n{pred.key_strengths}\n\n## CONTRO\n{pred.weaknesses}\n\n## VERDETTO\n{pred.final_verdict}\n\n---\nFONTI:\n{sources}"
    except Exception as e:
        return f"Errore generazione report: {str(e)}"
    
    # 5. Save
    try:
        embedding_vector = list(_embedding_model.embed([final_report]))[0].tolist()
        _qdrant.upsert(collection_name=COLLECTION_NAME, points=[models.PointStruct(id=str(uuid.uuid4()), vector=embedding_vector, payload={"player_name": nome_giocatore, "full_text": final_report, "sources": sources})])
    except Exception:
        pass
    
    return f"FONTE: WEB + AI (Disambiguato)\n\n{final_report}"

def crea_identikit_ai(descrizione_utente: str) -> str:
    _initialize()
    print(f"[LOG] Generazione Identikit da: '{descrizione_utente}'", file=sys.stderr)
    
    try:
        # 1. TRADUZIONE AI
        translation = _identikit_bot(description=descrizione_utente)
        
        role = translation.role_code
        style_requested = translation.target_style
        
        # Estrazione Filtri Extra
        filters = {}
        try:
            if translation.min_age and translation.min_age != 'None':
                filters['age_min'] = int(translation.min_age)
            if translation.max_age and translation.max_age != 'None':
                filters['age_max'] = int(translation.max_age)
            if translation.league_filter and translation.league_filter != 'None':
                filters['league'] = translation.league_filter
            if translation.nation_filter and translation.nation_filter != 'None':
                filters['nation'] = translation.nation_filter
        except Exception as e:
            print(f"[WARN] Errore parsing filtri extra: {e}", file=sys.stderr)

        # Estrazione Features Statistiche
        features = {}
        for i in range(1, 4):
            name = getattr(translation, f"feature_{i}_name")
            val = getattr(translation, f"feature_{i}_value")
            if name and name != 'None' and val:
                try:
                    f_val = float(val)
                    if f_val > 0: features[name] = f_val
                except: pass
        
        print(f"[LOG] Target: Ruolo={role}, Stile={style_requested}, Features={features}, Filtri={filters}", file=sys.stderr)
        
        # --- BIVIO LOGICO ---
        # Caso 1: Ricerca per Similarità (ci sono features o stile specifico)
        if features or (style_requested and style_requested != 'None'):
            print("[LOG] Modalità: SIMILARITÀ MATEMATICA", file=sys.stderr)
            
            cluster_id = None
            if style_requested and style_requested != 'None':
                cluster_id = _sim_engine._get_cluster_id_from_name(role, style_requested)

            K_SEARCH_INITIAL = 100 # Cerchiamo ampio per poi filtrare
            
            # Se il ruolo è nullo ma ci sono features, cerchiamo in tutti i ruoli
            if (not role or role == 'None'):
                 print("[LOG] Ricerca su TUTTI i ruoli...", file=sys.stderr)
                 df_res, style, _ = _sim_engine.find_similar_by_identikit_all_roles(features, k=K_SEARCH_INITIAL)
                 msg_intro = "**Identikit Generato:** Tutti i Ruoli"
            elif cluster_id is not None:
                df_res, style, _ = _sim_engine.find_similar_by_identikit(role, features, k=K_SEARCH_INITIAL, requested_cluster_id=cluster_id)
                msg_intro = f"**Identikit Generato:** {style_requested} ({role})"
            else:
                df_res, style, _ = _sim_engine.find_similar_by_identikit_all_clusters(role, features, k=K_SEARCH_INITIAL)
                msg_intro = f"**Identikit Generato:** {role} (Tutti gli stili)"

        # Caso 2: Ricerca Filtro Diretto (Solo Nazione/Lega/Età, nessuna feature tecnica)
        else:
            print("[LOG] Modalità: FILTRO DIRETTO (Query al Database)", file=sys.stderr)
            if not filters and (not role or role == 'None'):
                 return "Richiesta troppo vaga. Specifica almeno un ruolo, una lega, una nazione o una statistica."
            
            # Partiamo dal dataframe completo
            df_res = _df_main.copy()
            msg_intro = "**Risultati Ricerca:**"
            
            # Filtro Ruolo preventivo
            if role and role != 'None':
                df_res = df_res[df_res['Pos'].str.contains(role, na=False)]

        # --- APPLICAZIONE FILTRI COMUNI (Post-Processing) ---
        # Questa parte ora pulisce sia i risultati del SimEngine che quelli del Filtro Diretto
        
        # Normalizzazione colonne mancanti (per sicurezza)
        for col in ['Age', 'Comp', 'Nation']:
            if col not in df_res.columns and 'ID_Univoco' in df_res.columns:
                 # Merge di recupero veloce
                 df_res = df_res.merge(_df_main[['ID_Univoco', col]], on='ID_Univoco', how='left', suffixes=('', '_y'))
                 if f'{col}_y' in df_res.columns:
                     df_res[col] = df_res[f'{col}_y']
                     df_res.drop(columns=[f'{col}_y'], inplace=True)

        original_count = len(df_res)
        
        # Filtri Anagrafici/Geografici
        if 'age_min' in filters:
            df_res = df_res[pd.to_numeric(df_res['Age'], errors='coerce') >= filters['age_min']]
        if 'age_max' in filters:
            df_res = df_res[pd.to_numeric(df_res['Age'], errors='coerce') <= filters['age_max']]
        if 'league' in filters:
            df_res = df_res[df_res['Comp'].astype(str).str.contains(filters['league'], case=False, na=False)]
        if 'nation' in filters:
            # L'AI ci dà "FRA", "BRA", "ITA"
            target_code = filters['nation'].strip().upper()
            
            print(f"[LOG] Filtro Nazione (AI): Cerco codice '{target_code}'", file=sys.stderr)

            # Logica "Smart Search" sul Database
            # Il database ha formato "fr FRA", "it ITA", "br BRA"
            
            mask = pd.Series([False] * len(df_res), index=df_res.index)
            
            # 1. Cerca nella colonna NationCode (se l'hai creata in data.py ed è pulita)
            if 'NationCode' in df_res.columns:
                mask |= df_res['NationCode'].astype(str).str.upper() == target_code
            
            # 2. Cerca nel campo completo 'Nation' (Fallback robusto)
            # Cerca "FRA" dentro "fr FRA" -> True
            # Cerca "FRA" dentro "France" -> False (ma l'AI ci ha dato FRA, quindi ok)
            if 'Nation' in df_res.columns:
                # Usiamo word boundaries (\b) per evitare che "IN" matchi "ARGENTINA"
                # Ma per i codici 3 lettere, contains semplice è spesso sufficiente e più veloce
                mask |= df_res['Nation'].astype(str).str.upper().str.contains(target_code, na=False)
            
            df_res = df_res[mask]

        print(f"[LOG] Risultati dopo filtri: {original_count} -> {len(df_res)}", file=sys.stderr)

        if df_res.empty:
            return f"Nessun giocatore trovato con questi criteri. Prova ad allargare la ricerca."

        # 4. FORMATTAZIONE FINALE
        # Ordiniamo per Valore di Mercato se disponibile, altrimenti casuale o per similarità
        if 'Similarita (Distanza)' in df_res.columns:
             df_final = df_res.sort_values(by='Similarita (Distanza)').head(10)
        elif 'Valore_Mercato' in df_res.columns:
             # Se è un filtro diretto, mostriamo i più preziosi
             # Assumendo Valore_Mercato sia pulito, altrimenti head(10) standard
             df_final = df_res.head(10)
        else:
             df_final = df_res.head(10)
        
        cols_to_show = ['Player', 'Team', 'Comp', 'Age']
        if 'Similarita (Distanza)' in df_final.columns: cols_to_show.append('Similarita (Distanza)')
        if 'Valore_Mercato' in df_final.columns: cols_to_show.append('Valore_Mercato')
        
        cols_existing = [c for c in cols_to_show if c in df_final.columns]
        
        filter_desc = ", ".join([f"{k}={v}" for k,v in filters.items()])
        result = f"{msg_intro}\n*Filtri applicati: {filter_desc}*\n\n"
        result += df_final[cols_existing].to_markdown(index=False)
        
        return result

    except Exception as e:
        print(f"[ERROR] crea_identikit_ai: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return f"Errore creazione identikit: {str(e)}"

# --- FUNZIONE MASTER PER LA WEB APP ---
def process_request(user_text: str) -> dict:
    """
    Punto di ingresso per la chat.
    Restituisce un dizionario: {'type': 'chat'|'table'|'report'|'error', 'content': str}
    """
    _initialize()
    
    print(f"[ROUTER] Input Utente: '{user_text}'", file=sys.stderr)
    
    try:
        # 1. Il Router decide cosa fare
        decision = _router_bot(query=user_text)
        tool = decision.tool_selected
        player = decision.player_name
        
        print(f"[ROUTER] Decisione: Tool={tool}, Player={player}", file=sys.stderr)
        
        if tool == 'SEARCH_SIMILAR':
            if not player or player.lower() == 'none':
                return {"type": "chat", "content": "Per cercare giocatori simili, devi dirmi il nome di un giocatore di riferimento."}
            content = cerca_simili_statistici(player)
            return {"type": "table", "content": content}
            
        elif tool == 'GET_REPORT':
            if not player or player.lower() == 'none':
                return {"type": "chat", "content": "Di quale giocatore vuoi il report? Specifica il nome."}
            content = ottieni_report_tattico(player)
            return {"type": "report", "content": content}
        elif tool == 'CREATE_IDENTIKIT':
            content = crea_identikit_ai(user_text)
            return {"type": "table", "content": content}
        else: # CHAT
            return {"type": "chat", "content": decision.chat_reply or "Sono un assistente tattico, chiedimi di analizzare un giocatore o trovarne di simili!"}
            
    except Exception as e:
        print(f"[ROUTER ERROR] {e}", file=sys.stderr)
        return {"type": "error", "content": f"Errore nel ragionamento: {e}"}

# --- TEST LOCALE ---
if __name__ == "__main__":
    print("\n=== TEST ROUTER ===")
    
    # Test 1: Domanda Statistica
    q1 = "Chi è simile a Calafiori?"
    print(f"\nQ: {q1}")
    res1 = process_request(q1)
    print(f"A ({res1['type']}): {str(res1['content'])[:100]}...") # Tronco per brevità
    
    # Test 2: Domanda Tattica
    q2 = "Analizza lo stile di gioco di Zirkzee"
    print(f"\nQ: {q2}")
    res2 = process_request(q2)
    print(f"A ({res2['type']}): {str(res2['content'])[:100]}...")
    
    # Test 3: Chat
    q3 = "Ciao, chi sei?"
    print(f"\nQ: {q3}")
    res3 = process_request(q3)
    print(f"A ({res3['type']}): {res3['content']}")