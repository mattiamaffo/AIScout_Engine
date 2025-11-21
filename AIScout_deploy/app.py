import dash # type: ignore
import dash_bootstrap_components as dbc # type: ignore
from dash.exceptions import PreventUpdate # type: ignore
from dash import dcc, html # type: ignore
from dash.dependencies import Input, Output, State, ALL # type: ignore
import math
import pandas as pd # type: ignore
from SimEngine import SimilarityEngine
import plotly.graph_objects as go # type: ignore
import sys
import os
import threading
from pathlib import Path

# --- Configurazione Percorsi ---
BASE_DIR = Path(__file__).resolve().parent
FULL_DATASET_PATH = BASE_DIR / 'data' / 'dataset_master_final.parquet'

# --- Importazioni dai file refattorizzati ---
from layout import (
    create_main_layout, 
    search_player_layout, 
    identikit_layout, 
    database_layout
)
import data
from data import (
    _filter_database, 
    with_blank, 
    ROWS_PER_PAGE
)
import config

# 1. --- Inizializzazione App ---
external_stylesheets = [
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',
    dbc.themes.BOOTSTRAP 
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
server = app.server

# Variabile globale per la finestra pywebview
# window = None

# --- Avvio Caricamento Dati in Background (Lazy Loading) ---
# Questo thread popola data.DATABASE_DF e data.PLAYER_SEARCH_OPTIONS mentre la UI si carica
threading.Thread(target=data.load_data, daemon=True).start()

print("--- Inizializzazione Globale SimilarityEngine ---")
try:
    ARTIFACTS_DIR = BASE_DIR / 'artifacts'
    engine = SimilarityEngine(artifacts_dir=str(ARTIFACTS_DIR))
    print("--- Motore di Similarità Caricato ---")
    # Rendi le statistiche disponibili globalmente per l'app
    FEATURE_STATS = engine.feature_stats if hasattr(engine, 'feature_stats') else {}
except Exception as e:
    print(f"--- ERRORE CRITICO: Impossibile caricare il SimEngine. {e} ---")
    engine = None # L'app funzionerà, ma la ricerca fallirà
    FEATURE_STATS = {}

# --- Avvio Caricamento Modelli AI in Background ---
# Questo thread pre-carica gli artefatti pesanti (PCA, k-NN) per rendere la ricerca istantanea
def load_engine_models():
    print("DEBUG: Thread load_engine_models avviato.")
    if engine:
        print("DEBUG: Engine trovato, avvio load_artifacts...")
        # Passiamo la funzione di callback per aggiornare la barra di progresso
        engine.load_artifacts(progress_callback=data.set_progress)
        print("DEBUG: load_artifacts completato.")
    else:
        print("DEBUG: Engine è None, impossibile caricare artefatti.")

threading.Thread(target=load_engine_models, daemon=True).start()


# ====== FUNZIONI DI VALIDAZIONE E GESTIONE ERRORI ======

def validate_age(age_value):
    """
    Valida l'input dell'età.
    Returns: (is_valid, validated_value, error_message)
    """
    if age_value is None or age_value == 0 or age_value == '':
        return True, None, None
    
    try:
        age = int(age_value) if isinstance(age_value, str) else age_value
        if age < 16 or age > 45:
            return False, None, "L'età deve essere compresa tra 16 e 45 anni."
        return True, age, None
    except (ValueError, TypeError):
        return False, None, "L'età deve essere un numero valido."


def validate_feature_value(feature_name, value):
    """
    Valida il valore di una feature statistica.
    Returns: (is_valid, validated_value, error_message)
    """
    if value is None or value == 0:
        return True, 0, None
    
    try:
        val = float(value)
        if val < 0:
            return False, None, f"{feature_name} non può essere negativo."
        if val > 100:  # Reasonable max for percentages/stats
            return False, None, f"{feature_name} ha un valore troppo alto (max 100)."
        return True, val, None
    except (ValueError, TypeError):
        return False, None, f"{feature_name} deve essere un numero valido."


# 2. --- Impostazione Layout ---
# Creiamo un wrapper per gestire il Loading Screen
main_layout_content = create_main_layout()

# Layout di Caricamento
loading_layout = html.Div(
    id='loading-screen',
    style={
        'position': 'fixed',
        'top': 0,
        'left': 0,
        'width': '100%',
        'height': '100%',
        'backgroundColor': '#1e1e1e', # Colore di sfondo scuro coerente con l'app
        'zIndex': 9999,
        'display': 'flex',
        'flexDirection': 'column',
        'justifyContent': 'center',
        'alignItems': 'center'
    },
    children=[
        html.Img(src='/assets/FullLogo_Transparent.png', style={'width': '250px', 'marginBottom': '30px'}),
        
        # Progress Bar Container
        html.Div(style={'width': '50%', 'maxWidth': '600px'}, children=[
            dbc.Progress(id="loading-progress-bar", value=0, striped=True, animated=True, color="info", style={"height": "20px"}),
        ]),
        
        html.H5(id="loading-text", children="Inizializzazione...", style={'color': '#cccccc', 'marginTop': '20px', 'fontFamily': 'sans-serif'}),
        html.P("Il primo avvio potrebbe richiedere alcuni secondi.", style={'color': '#888888', 'fontSize': '14px'})
    ]
)

# Layout Principale (inizialmente nascosto)
app.layout = html.Div([
    loading_layout,
    html.Div(
        id='main-content-wrapper',
        style={'display': 'none'}, # Nascosto all'avvio
        children=main_layout_content
    )
])

# --- Callback 1: Cambiare Scheda (Tab) ---
@app.callback(
    Output('tab-content-search', 'style'),
    Output('tab-content-identikit', 'style'),
    Output('tab-content-database', 'style'),
    Output('tab-search', 'className'),
    Output('tab-identikit', 'className'),
    Output('tab-database', 'className'),
    Output('main-container', 'className'),
    Output('output-display', 'children', allow_duplicate=True),
    Input('tab-search', 'n_clicks'),
    Input('tab-identikit', 'n_clicks'),
    Input('tab-database', 'n_clicks'),
    State('output-display', 'children'),
    prevent_initial_call='initial_duplicate'
)
def display_page_content(search_clicks, identikit_clicks, database_clicks, current_output):
    # Get the triggered ID
    triggered_id = dash.ctx.triggered_id 
    
    if triggered_id == 'tab-identikit':
        # Show Identikit, hide others
        return (
            {'display': 'none'},  # search
            {'display': 'block'}, # identikit
            {'display': 'none'},  # database
            'icon-nav-item', 
            'icon-nav-item active', 
            'icon-nav-item', 
            'layout-identikit', 
            None
        )
    
    elif triggered_id == 'tab-database':
        # Show Database, hide others
        return (
            {'display': 'none'},  # search
            {'display': 'none'},  # identikit
            {'display': 'block'}, # database
            'icon-nav-item', 
            'icon-nav-item', 
            'icon-nav-item active', 
            'layout-database', 
            None
        )
    
    elif triggered_id == 'tab-search':
        # Show Search, hide others
        return (
            {'display': 'block'}, # search
            {'display': 'none'},  # identikit
            {'display': 'none'},  # database
            'icon-nav-item active', 
            'icon-nav-item', 
            'icon-nav-item', 
            'layout-home', 
            current_output
        )
    
    # Default (initial load): show search tab
    default_message = "Seleziona un giocatore e premi 'Trova Simili' per iniziare."
    return (
        {'display': 'block'}, # search
        {'display': 'none'},  # identikit
        {'display': 'none'},  # database
        'icon-nav-item active', 
        'icon-nav-item', 
        'icon-nav-item', 
        'layout-home', 
        default_message
    )


# --- Callback A: Popola opzioni Nation quando si apre la scheda (aggiorna on tab visibility)
@app.callback(
    Output('identikit-nation', 'options'),
    Input('tab-content-identikit', 'style')
)
def populate_nation_options(identikit_style):
    # Carica opzioni uniche dal DATABASE_DF
    try:
        if data.DATABASE_DF.empty:
            return with_blank([])
        
        # Formatta e normalizza le nazioni - estrae solo il codice a 3 lettere maiuscolo
        nations_raw = data.DATABASE_DF['Nation'].dropna().unique()
        nations_formatted = set()
        for n in nations_raw:
            n_str = str(n).strip()
            # Estrai la parte con 3 lettere maiuscole (es: "eng ENG" -> "ENG", "fr FRA" -> "FRA")
            parts = n_str.split()
            for part in parts:
                if len(part) == 3 and part.isupper():
                    nations_formatted.add(part)
                    break
        
        nations = sorted(list(nations_formatted))
        nation_opts = with_blank([{'label': n, 'value': n} for n in nations])
        return nation_opts
    except Exception:
        return with_blank([])


# --- Callback B: Popola le opzioni dei cluster in base al ruolo scelto (Identikit)
@app.callback(
    Output('identikit-cluster', 'options'),
    Input('identikit-pos', 'value')
)
def update_identikit_clusters(selected_pos):
    # Tratta stringa vuota come None per mostrare placeholder
    if not selected_pos or selected_pos == '':
        return with_blank([])
    roles_for_pos = config.CLUSTER_NAMES_MAP.get(selected_pos, {})
    options = [{'label': role_name, 'value': role_name} for role_name in sorted(roles_for_pos.values())]
    return with_blank(options)


# --- Callback C: Render dinamico dei feature inputs per il ruolo selezionato ---
@app.callback(
    Output('identikit-role-features', 'children'),
    Input('identikit-pos', 'value')
)
def render_role_features(selected_pos):
    # Tratta stringa vuota come None
    if not selected_pos or selected_pos == '':
        return html.Div(
            "Seleziona prima una posizione (es. MF) per mostrare le caratteristiche.",
            className='identikit-features-placeholder'
        )
    features = config.ROLE_FEATURES.get(selected_pos, [])
    if not features:
        return html.Div(
            "Nessuna caratteristica configurata per questa posizione.",
            className='identikit-features-placeholder'
        )

    # Recupera le statistiche per questo ruolo
    role_stats = FEATURE_STATS.get(selected_pos, {})

    # Crea un layout a griglia moderna per le features con tooltip
    feature_cards = []
    for feat in features:
        # Genera tooltip con le statistiche
        tooltip_text = ""
        feat_stats = role_stats.get(feat, {})
        if feat_stats:
            p25 = feat_stats.get('p25', 0)
            p75 = feat_stats.get('p75', 0)
            max_val = feat_stats.get('max', 0)
            mean_val = feat_stats.get('mean', 0)
            tooltip_text = f"Tipico: {p25:.1f} - {p75:.1f} | Media: {mean_val:.1f} | Max: {max_val:.1f}"
        else:
            tooltip_text = "Statistiche non disponibili"
        
        # Determina il max per l'input
        input_max = feat_stats.get('max', 999) if feat_stats else 999
        
        card = html.Div(className='feature-card', children=[
            html.Label(feat, className='feature-label', title=tooltip_text),
            dcc.Input(
                id={'type': 'identikit-feature', 'index': feat},
                type='number',
                value=0,
                min=0,
                max=input_max,
                step=0.1 if input_max < 10 else 1,
                placeholder=f'Max: {input_max:.0f}',
                className='feature-input'
            )
        ])
        feature_cards.append(card)
    
    return html.Div(className='features-grid', children=feature_cards)


# --- Callback D: Reset Identikit Form ---
@app.callback(
    Output('identikit-pos', 'value'),
    Output('identikit-cluster', 'value'),
    Output('identikit-age', 'value'),
    Output('identikit-nation', 'value'),
    Output('identikit-league', 'value'),
    Output({'type': 'identikit-feature', 'index': ALL}, 'value'),
    Input('identikit-reset-button', 'n_clicks'),
    State({'type': 'identikit-feature', 'index': ALL}, 'id'),
    prevent_initial_call=True
)
def reset_identikit_form(reset_clicks, feature_ids):
    """
    Reset tutti i campi dell'Identikit ai valori di default.
    Con gestione errori robusta.
    """
    try:
        if not reset_clicks:
            raise PreventUpdate
        
        # Valida che feature_ids sia una lista
        if not isinstance(feature_ids, list):
            print(f"Warning: feature_ids non è una lista: {type(feature_ids)}")
            feature_ids = []
        
        # Reset valori features a 0
        feature_values = [0] * len(feature_ids)
        
        return None, None, None, None, None, feature_values
    
    except PreventUpdate:
        raise
    except Exception as e:
        print(f"Errore in reset_identikit_form: {e}")
        # In caso di errore, restituisci comunque valori di default
        return None, None, None, None, None, [0] * len(feature_ids if isinstance(feature_ids, list) else [])


# --- Callback 2a: Gestione Apertura/Chiusura Popup Risultati ---
@app.callback(
    Output('results-modal', 'is_open'),
    Output('search-trigger-store', 'data'),
    Output('output-display', 'children', allow_duplicate=True),
    Output('modal-results-content', 'children'), # Output per pulire il contenuto
    Input('search-button', 'n_clicks'),
    Input('identikit-find-button', 'n_clicks'),
    Input('modal-close-button', 'n_clicks'),
    State('search-bar', 'value'),
    State('k-slider', 'value'),
    State('results-modal', 'is_open'),
    prevent_initial_call=True
)
def toggle_results_modal(search_clicks, identikit_clicks, close_clicks, selected_id_univoco, k_value, is_open):
    """
    Gestisce l'apertura e la chiusura del modal.
    Passa anche i dati di ricerca al dcc.Store.
    Con validazione input e gestione errori robusta.
    """
    try:
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # --- Caso 1: L'utente preme "Trova Simili" (Search Player) ---
        if triggered_id == 'search-button':
            if not selected_id_univoco:
                # Se non ha selezionato un giocatore, mostra errore e non aprire
                msg = "Per favore, seleziona un giocatore dalla barra di ricerca prima di premere 'Trova Simili'."
                return False, dash.no_update, msg, dash.no_update
            
            # Valida k_value
            try:
                k_val = int(k_value) if k_value else 10
                if k_val < 1 or k_val > 100:
                    msg = "Il numero di giocatori simili deve essere tra 1 e 100."
                    return False, dash.no_update, msg, dash.no_update
            except (ValueError, TypeError):
                msg = "Valore non valido per il numero di giocatori simili."
                return False, dash.no_update, msg, dash.no_update
            
            # Se ha selezionato, apri il modal e salva i dati per la ricerca
            search_data = {'id_univoco': str(selected_id_univoco), 'k': k_val}
            # Pulisce il messaggio di errore/default e il contenuto precedente del modal
            return True, search_data, None, None
        
        # --- Caso 2: L'utente preme "Cerca" (Identikit) ---
        if triggered_id == 'identikit-find-button':
            # Apri il modal - la ricerca verrà eseguita dal callback run_similarity_calculation
            return True, dash.no_update, None, None

        # --- Caso 3: L'utente preme "Chiudi" sul modal ---
        if triggered_id == 'modal-close-button':
            # Chiudi il modal, cancella i dati di ricerca e il contenuto
            return False, None, dash.no_update, None

        raise PreventUpdate
    
    except PreventUpdate:
        raise
    except Exception as e:
        print(f"Errore in toggle_results_modal: {e}")
        import traceback
        traceback.print_exc()
        error_msg = "Si è verificato un errore nell'apertura del modal. Riprova."
        return False, dash.no_update, error_msg, dash.no_update


# --- Callback 2b: Calcolo Similarità -> Salvataggio nello Store ---
@app.callback(
    Output('results-store', 'data'),
    Input('search-trigger-store', 'data'),
    Input('identikit-find-button', 'n_clicks'),
    State('identikit-pos', 'value'),
    State('identikit-cluster', 'value'),
    State('identikit-age', 'value'),
    State('identikit-nation', 'value'),
    State('identikit-league', 'value'),
    State('search-filter-nation', 'value'),
    State('search-filter-comp', 'value'),
    State({'type': 'identikit-feature', 'index': ALL}, 'value'),
    State({'type': 'identikit-feature', 'index': ALL}, 'id'),
    State('k-slider', 'value'),
    prevent_initial_call=True,
)
def run_similarity_calculation(search_data, identikit_n_clicks, pos_value, cluster_value, age_value, nation_value, league_value, filter_nation_search, filter_comp_search, feature_values, feature_ids, k_value):
    """
    Unified callback handling both search-by-player (via `search-trigger-store`) and
    Identikit submissions (via `identikit-find-button`). Distinguishes the trigger
    using `dash.ctx.triggered_id`.
    Con validazione completa degli input e gestione errori robusta.
    """
    try:
        triggered = dash.ctx.triggered_id

        if engine is None:
            return {'error': "Errore: Il Motore di Similarità non è stato caricato. Riavvia l'applicazione."}
        
        # ===== VALIDAZIONE INPUT COMUNE =====
        
        # Valida k_value
        try:
            k_base = int(k_value) if k_value else 10
            if k_base < 1 or k_base > 100:
                return {'error': "Il numero di giocatori deve essere tra 1 e 100."}
        except (ValueError, TypeError):
            return {'error': "Valore non valido per il numero di giocatori."}
        
        # Valida età se fornita (per Identikit)
        if triggered == 'identikit-find-button' and age_value:
            is_valid, validated_age, error_msg = validate_age(age_value)
            if not is_valid:
                return {'error': error_msg}
            age_value = validated_age
        
        # Valida feature values (per Identikit)
        if triggered == 'identikit-find-button' and feature_values:
            if not isinstance(feature_values, list):
                return {'error': "Errore interno: valori delle caratteristiche non validi."}
            
            validated_features = []
            for idx, val in enumerate(feature_values):
                if idx < len(feature_ids):
                    feat_name = feature_ids[idx].get('index', f'Feature_{idx}')
                    is_valid, validated_val, error_msg = validate_feature_value(feat_name, val)
                    if not is_valid:
                        return {'error': error_msg}
                    validated_features.append(validated_val)
                else:
                    validated_features.append(0)
            
            feature_values = validated_features

        # --- Caso: ricerca standard (tramite store settato dalla UI di ricerca) ---
        if triggered == 'search-trigger-store':
            if not search_data:
                raise PreventUpdate

            player_id = str(search_data.get('id_univoco'))
            # prefer k from search_data if present, else from hidden k-slider state (k_value)
            try:
                k_base = int(search_data.get('k', int(k_value or 10)))
            except Exception:
                k_base = int(k_value or 10)

            player_row = data.DATABASE_DF[data.DATABASE_DF['ID_Univoco'] == player_id]
            if player_row.empty:
                return {'error': f"Giocatore con ID {player_id} non trovato."}
            player_data = player_row.iloc[0].to_dict()

            # Richiedi molti più risultati per compensare filtri (fino a 50)
            # In questo modo dopo il filtraggio avremo abbastanza giocatori per raggiungere k
            k_search = min(50, k_base * 5) if (filter_nation_search and 'filter' in filter_nation_search) or (filter_comp_search and 'filter' in filter_comp_search) else k_base

            results_df, source_player_style, target_coords = engine.find_similar_players_by_id(player_id, k=k_search)

            if not isinstance(results_df, pd.DataFrame) or results_df.empty or source_player_style is None:
                return {'error': f"Nessun giocatore simile trovato per '{player_data['Player']}'."}

            if target_coords:
                player_data.update(target_coords)

            results_df['ID_Univoco'] = results_df['ID_Univoco'].astype(str)
            
            # Merge con DATABASE_DF per aggiungere DisplayAge, e assicurarci di avere Nation/Comp
            # Se Comp esiste già in results_df, rinominala temporaneamente per evitare conflitti
            db_cols = ['ID_Univoco', 'DisplayAge']
            if 'Nation' not in results_df.columns:
                db_cols.append('Nation')
            if 'Comp' not in results_df.columns:
                db_cols.append('Comp')
            
            db_info = data.DATABASE_DF[db_cols]
            merged_df = pd.merge(results_df, db_info, on='ID_Univoco', how='left', suffixes=('', '_db'))

            # APPLICAZIONE FILTRI POST-RICERCA per Search Player
            # Filtra per Nation se richiesto
            if filter_nation_search and 'filter' in filter_nation_search:
                target_nation = str(player_data.get('Nation', '')).strip()
                if target_nation:
                    # Estrai codice a 3 lettere maiuscolo dalla nazione del target
                    target_nation_code = None
                    for part in target_nation.split():
                        if len(part) == 3 and part.isupper():
                            target_nation_code = part
                            break
                    if target_nation_code:
                        merged_df = merged_df[merged_df['Nation'].astype(str).str.contains(target_nation_code, case=False, na=False)]
            
            # Filtra per Comp se richiesto
            if filter_comp_search and 'filter' in filter_comp_search:
                target_comp = str(player_data.get('Comp', '')).strip()
                if target_comp:
                    merged_df = merged_df[merged_df['Comp'].astype(str).str.contains(target_comp, case=False, na=False)]
            
            # Limita ai k risultati richiesti dopo il filtraggio
            merged_df = merged_df.head(k_base)

            if merged_df.empty:
                return {'error': "Nessun giocatore trovato dopo l'applicazione dei filtri. Prova a disabilitare i filtri geografici."}

            return {
                'target_player': player_data,
                'target_style': source_player_style,
                'similar_players': merged_df.to_dict('records'
                )
            }

        # --- Caso: Identikit submission ---
        if triggered == 'identikit-find-button':
            # Build feature dict from provided states
            feature_dict = {}
            if age_value is not None and age_value != 0:
                feature_dict['Age'] = age_value
            if nation_value and nation_value != '':
                feature_dict['Nation'] = nation_value
            if cluster_value and cluster_value != '':
                feature_dict['Requested_StyleName'] = cluster_value

            # Populate role-specific features (solo quelle con valore > 0)
            for idx, fid in enumerate(feature_ids):
                feat_name = fid.get('index')
                feat_value = feature_values[idx]
                if feat_value is not None and feat_value > 0:
                    feature_dict[feat_name] = feat_value

            # k is taken from hidden k-slider state passed as k_value
            k_base = int(k_value or 10)
            
            # Determina quali filtri sono attivi
            has_geo_filters = (nation_value and nation_value != '') or (league_value and league_value != '')
            has_stat_features = any(v > 0 for v in feature_values if v is not None)
            has_position = pos_value and pos_value != ''
            
            # MODALITÀ 1: QUERY DIRETTA - Solo filtri geografici/posizione senza features statistiche
            # In questo caso vogliamo TUTTI i giocatori che matchano i criteri, non una ricerca per similarità
            if (has_geo_filters or has_position) and not has_stat_features and not cluster_value:
                print(f"MODALITÀ 1: QUERY DIRETTA (filtri esatti senza statistiche)")
                
                # Carica il dataset completo
                try:
                    full_df = pd.read_parquet(FULL_DATASET_PATH)
                    full_df['ID_Univoco'] = full_df.index.astype(str)
                    print(f"Dataset completo caricato: {len(full_df)} giocatori totali")
                except Exception as e:
                    print(f"Errore caricamento dataset: {e}")
                    return {'error': "Impossibile caricare il dataset per la query diretta."}
                
                # Applica filtri direttamente sul dataset completo
                filtered_df = full_df.copy()
                
                # Filtra per posizione
                if has_position:
                    # Mappa posizione ai giocatori negli artefatti di quel ruolo
                    role_pca_df = engine.pca_dataframes.get(pos_value)
                    if role_pca_df is not None:
                        valid_ids = role_pca_df.index.astype(str).tolist()
                        filtered_df = filtered_df[filtered_df['ID_Univoco'].isin(valid_ids)]
                        print(f"Filtro Posizione '{pos_value}': {len(filtered_df)} giocatori")
                
                # Filtra per nazione
                if nation_value and nation_value != '':
                    target_nation_code = str(nation_value).strip().upper()
                    filtered_df = filtered_df[filtered_df['Nation'].astype(str).str.contains(target_nation_code, case=False, na=False)]
                    print(f"Filtro Nation '{target_nation_code}': {len(filtered_df)} giocatori")
                
                # Filtra per campionato
                if league_value and league_value != '':
                    filtered_df = filtered_df[filtered_df['Comp'].astype(str).str.contains(str(league_value), case=False, na=False)]
                    print(f"Filtro Campionato '{league_value}': {len(filtered_df)} giocatori")
                
                # Aggiungi sempre DisplayAge anche se non c'è filtro età
                if 'DisplayAge' not in filtered_df.columns:
                    filtered_df['DisplayAge'] = pd.to_numeric(filtered_df['Age'], errors='coerce').round().astype('Int64')
                
                # Filtra per età se specificato
                if age_value is not None and age_value > 0:
                    filtered_df = filtered_df[
                        (filtered_df['DisplayAge'].notna()) & 
                        (filtered_df['DisplayAge'] <= age_value)
                    ]
                    print(f"Filtro Età <= {age_value}: {len(filtered_df)} giocatori")
                
                if filtered_df.empty:
                    return {'error': "Nessun giocatore trovato con i filtri specificati."}
                
                # Aggiungi colonna Stile di Gioco se possibile
                filtered_df['Stile di Gioco'] = filtered_df['ID_Univoco'].apply(
                    lambda x: engine.pca_dataframes[pos_value].loc[int(x), 'Cluster'] 
                    if pos_value and int(x) in engine.pca_dataframes[pos_value].index 
                    else None
                )
                filtered_df['Stile di Gioco'] = filtered_df['Stile di Gioco'].apply(
                    lambda c: engine._get_style_name(pos_value, int(c)) if c is not None else ''
                )
                
                # Aggiungi colonna "Similarita (Distanza)" per compatibilità con la visualizzazione
                # In modalità query diretta non c'è distanza, quindi usiamo 0 o N/A
                filtered_df['Similarita (Distanza)'] = 0.0
                
                # Prepara risultati (tutti i giocatori che matchano)
                merged_df = filtered_df
                style_name = f"{pos_value} (Query Diretta)" if pos_value else "Tutti i Ruoli (Query Diretta)"
                target_coords = {}
                
                print(f"QUERY DIRETTA: {len(merged_df)} giocatori trovati")
            
            # MODALITÀ 2: IBRIDA - Filtri geografici + Features statistiche
            # Prima applica filtri geografici, poi filtra per statistiche sul sottoinsieme
            elif has_geo_filters and has_stat_features:
                print(f"MODALITÀ 2: IBRIDA (filtri geografici + statistiche)")
                
                # Carica il dataset completo
                try:
                    full_df = pd.read_parquet(FULL_DATASET_PATH)
                    full_df['ID_Univoco'] = full_df.index.astype(str)
                    print(f"Dataset completo caricato: {len(full_df)} giocatori totali")
                except Exception as e:
                    print(f"Errore caricamento dataset: {e}")
                    return {'error': "Impossibile caricare il dataset per la ricerca ibrida."}
                
                # PASSO 1: Applica filtri geografici esatti
                filtered_df = full_df.copy()
                
                # Filtra per posizione
                if has_position:
                    role_pca_df = engine.pca_dataframes.get(pos_value)
                    if role_pca_df is not None:
                        valid_ids = role_pca_df.index.astype(str).tolist()
                        filtered_df = filtered_df[filtered_df['ID_Univoco'].isin(valid_ids)]
                        print(f"Filtro Posizione '{pos_value}': {len(filtered_df)} giocatori")
                
                # Filtra per nazione
                if nation_value and nation_value != '':
                    target_nation_code = str(nation_value).strip().upper()
                    filtered_df = filtered_df[filtered_df['Nation'].astype(str).str.contains(target_nation_code, case=False, na=False)]
                    print(f"Filtro Nation '{target_nation_code}': {len(filtered_df)} giocatori")
                
                # Filtra per campionato
                if league_value and league_value != '':
                    filtered_df = filtered_df[filtered_df['Comp'].astype(str).str.contains(str(league_value), case=False, na=False)]
                    print(f"Filtro Campionato '{league_value}': {len(filtered_df)} giocatori")
                
                # Filtra per età
                if age_value is not None and age_value > 0:
                    if 'DisplayAge' not in filtered_df.columns:
                        filtered_df['DisplayAge'] = pd.to_numeric(filtered_df['Age'], errors='coerce').round().astype('Int64')
                    filtered_df = filtered_df[
                        (filtered_df['DisplayAge'].notna()) & 
                        (filtered_df['DisplayAge'] <= age_value)
                    ]
                    print(f"Filtro Età <= {age_value}: {len(filtered_df)} giocatori")
                
                if filtered_df.empty:
                    return {'error': "Nessun giocatore trovato con i filtri geografici specificati."}
                
                # PASSO 2: Applica filtri statistici sul sottoinsieme
                print(f"\nAPPLICAZIONE FILTRI STATISTICI:")
                for feat_name, feat_value in feature_dict.items():
                    # Salta metadati
                    if feat_name in ['Age', 'Nation', 'Team', 'Comp', 'Requested_StyleName']:
                        continue
                    
                    if feat_name in filtered_df.columns and feat_value > 0:
                        before = len(filtered_df)
                        filtered_df[feat_name] = pd.to_numeric(filtered_df[feat_name], errors='coerce')
                        # Usa soglia dell'80% per flessibilità
                        threshold = feat_value * 0.8
                        filtered_df = filtered_df[
                            (filtered_df[feat_name].notna()) & 
                            (filtered_df[feat_name] >= threshold)
                        ]
                        print(f"Filtro {feat_name} >= {threshold:.1f} (richiesto: {feat_value}): {before} -> {len(filtered_df)} giocatori")
                
                if filtered_df.empty:
                    return {'error': "Nessun giocatore trovato dopo l'applicazione dei filtri statistici."}
                
                # Aggiungi DisplayAge se mancante
                if 'DisplayAge' not in filtered_df.columns:
                    filtered_df['DisplayAge'] = pd.to_numeric(filtered_df['Age'], errors='coerce').round().astype('Int64')
                
                # Aggiungi colonna Stile di Gioco se possibile
                if pos_value:
                    filtered_df['Stile di Gioco'] = filtered_df['ID_Univoco'].apply(
                        lambda x: engine.pca_dataframes[pos_value].loc[int(x), 'Cluster'] 
                        if int(x) in engine.pca_dataframes[pos_value].index 
                        else None
                    )
                    filtered_df['Stile di Gioco'] = filtered_df['Stile di Gioco'].apply(
                        lambda c: engine._get_style_name(pos_value, int(c)) if c is not None else ''
                    )
                
                # Aggiungi colonna similarità (0 perché non c'è ricerca k-NN)
                filtered_df['Similarita (Distanza)'] = 0.0
                
                merged_df = filtered_df
                style_name = f"{pos_value} (Ricerca Ibrida)" if pos_value else "Ricerca Ibrida"
                target_coords = {}
                
                print(f"RICERCA IBRIDA: {len(merged_df)} giocatori trovati")
                
            # MODALITÀ 3: RICERCA K-NN PURA - Solo features statistiche o cluster specifico
            else:
                print(f"MODALITÀ 3: K-NN PURA (ricerca per similarità)")
                
                # Determina quanti giocatori cercare
                if has_geo_filters and not has_stat_features:
                    k_search = min(2000, max(1000, k_base * 100))
                    print(f"Filtri geografici -> k_search = {k_search}")
                else:
                    # Per ricerche con statistiche, usa almeno 1000 giocatori
                    k_search = max(1000, k_base * 20)
                    print(f"Ricerca standard -> k_search = {k_search}")

                # Determina se cercare in un ruolo specifico o in tutti i ruoli
                if pos_value and pos_value != '':
                    role_code = pos_value
                    
                    if cluster_value and cluster_value != '':
                        requested_cluster_id = engine._get_cluster_id_from_name(role_code, cluster_value)
                        if requested_cluster_id is not None:
                            print(f"   --- FILTRO CLUSTER ATTIVO: {cluster_value} (ID: {requested_cluster_id}) ---")
                            results_df, style_name, target_coords = engine.find_similar_by_identikit(role_code, feature_dict, k=k_search, requested_cluster_id=requested_cluster_id)
                        else:
                            return {'error': f"Cluster '{cluster_value}' non trovato per posizione {role_code}."}
                    else:
                        print(f"   --- CERCA IN TUTTI I CLUSTER DI {role_code} ---")
                        results_df, style_name, target_coords = engine.find_similar_by_identikit_all_clusters(role_code, feature_dict, k=k_search)
                else:
                    results_df, style_name, target_coords = engine.find_similar_by_identikit_all_roles(feature_dict, k=k_search)

                if results_df is None or results_df.empty:
                    return {'error': "Nessun giocatore trovato con l'identikit specificato."}
                
                # Merge con DATABASE per avere Nation, Comp e TUTTE le statistiche originali
                results_df['ID_Univoco'] = results_df['ID_Univoco'].astype(str)
                print(f"Risultati iniziali dalla ricerca k-NN: {len(results_df)} giocatori")
                
                # Carica il dataset completo per avere accesso alle statistiche originali
                try:
                    full_df = pd.read_parquet(FULL_DATASET_PATH)
                    full_df['ID_Univoco'] = full_df.index.astype(str)
                    print(f"Dataset completo caricato: {len(full_df)} giocatori totali")
                except Exception as e:
                    print(f"Impossibile caricare dataset completo: {e}")
                    full_df = data.DATABASE_DF.copy()
                    print(f"Usando DATABASE_DF come fallback: {len(full_df)} giocatori")
                
                # Prima del merge, rimuovi colonne di metadati da results_df per evitare conflitti
                metadata_cols_to_remove = ['Nation', 'Comp', 'Team', 'Age', 'Player', 'Pos']
                for col in metadata_cols_to_remove:
                    if col in results_df.columns:
                        results_df = results_df.drop(columns=[col])
                
                # Merge con il dataset completo
                merged_df = pd.merge(results_df, full_df, on='ID_Univoco', how='left', suffixes=('_pca', ''))
                print(f"Dopo merge: {len(merged_df)} giocatori")
                
                # Se DisplayAge non esiste, prendila da Age
                if 'DisplayAge' not in merged_df.columns and 'Age' in merged_df.columns:
                    merged_df['DisplayAge'] = pd.to_numeric(merged_df['Age'], errors='coerce').round().astype('Int64')

                # APPLICAZIONE FILTRI POST-RICERCA per modalità k-NN
                print(f"\nAPPLICAZIONE FILTRI POST-RICERCA:")
                merged_df['DisplayAge'] = pd.to_numeric(merged_df['DisplayAge'], errors='coerce')
                
                # Filtra per Età Massima se specificata
                if age_value is not None and age_value > 0:
                    before = len(merged_df)
                    merged_df = merged_df[
                        (merged_df['DisplayAge'].notna()) & 
                        (merged_df['DisplayAge'] <= age_value)
                    ]
                    print(f"Filtro Età <= {age_value}: {before} -> {len(merged_df)} giocatori")
                
                # Filtra per Nation se specificata
                if nation_value and nation_value != '':
                    before = len(merged_df)
                    target_nation_code = str(nation_value).strip().upper()
                    merged_df = merged_df[merged_df['Nation'].astype(str).str.contains(target_nation_code, case=False, na=False)]
                    print(f"Filtro Nation '{target_nation_code}': {before} -> {len(merged_df)} giocatori")
                
                # Filtra per Comp (Campionato) se specificato
                if league_value and league_value != '':
                    before = len(merged_df)
                    merged_df = merged_df[merged_df['Comp'].astype(str).str.contains(str(league_value), case=False, na=False)]
                    print(f"Filtro Campionato '{league_value}': {before} -> {len(merged_df)} giocatori")
                
                # Filtra per statistiche specificate dall'utente (solo in modalità k-NN)
                if feature_dict:
                    for feat_name, feat_value in feature_dict.items():
                        if feat_name in ['Age', 'Nation', 'Team', 'Comp', 'Requested_StyleName']:
                            continue
                        
                        if feat_name in merged_df.columns and feat_value > 0:
                            merged_df[feat_name] = pd.to_numeric(merged_df[feat_name], errors='coerce')
                            threshold = feat_value * 0.8
                            merged_df = merged_df[
                                (merged_df[feat_name].notna()) & 
                                (merged_df[feat_name] >= threshold)
                            ]
                            print(f"Filtro {feat_name} >= {threshold:.1f}: {len(merged_df)} risultati")
            
            # Limita ai k risultati richiesti dopo il filtraggio
            merged_df = merged_df.head(k_base)

            if merged_df.empty:
                return {'error': "Nessun giocatore trovato dopo l'applicazione dei filtri. Prova a disabilitare i filtri geografici."}

            # Crea target_player con ruolo dinamico
            if pos_value and pos_value != '':
                target_player = {
                    'Player': f'Identikit ({pos_value})',
                    'Pos': pos_value,
                    'StyleRequested': cluster_value or ''
                }
            else:
                target_player = {
                    'Player': 'Identikit (Tutti i Ruoli)',
                    'Pos': 'ALL',
                    'StyleRequested': cluster_value or ''
                }
            
            if target_coords:
                target_player.update(target_coords)

            return {
                'target_player': target_player,
                'target_style': style_name,
                'similar_players': merged_df.to_dict('records')
            }

        # If trigger is something else, do nothing
        raise PreventUpdate

    except PreventUpdate:
        raise
    except KeyError as e:
        print(f"Errore di chiave mancante in run_similarity_calculation: {e}")
        import traceback
        traceback.print_exc()
        return {'error': f"Errore interno: dati mancanti ({str(e)}). Riprova o contatta il supporto."}
    except ValueError as e:
        print(f"Errore di valore in run_similarity_calculation: {e}")
        return {'error': f"Valore non valido: {str(e)}"}
    except Exception as e:
        print(f"Errore generico in run_similarity_calculation: {e}")
        import traceback
        traceback.print_exc()
        return {'error': "Si è verificato un errore inaspettato durante la ricerca. Riprova."}


# --- Callback: Sync visible slider to hidden k-slider input ---
@app.callback(
    Output('k-slider', 'value'),
    Input('k-slider-visible', 'value'),
    prevent_initial_call=False
)
def sync_k_slider(visible_value):
    # Mirror the visible slider value into the hidden k-slider input
    try:
        return int(visible_value)
    except Exception:
        return 10


# Callback 2c: Renderizzazione Contenuto Modal (Tabella/3D) e Gestione Bottoni
@app.callback(
    Output('modal-results-content', 'children', allow_duplicate=True),
    Output('btn-view-table', 'active'),
    Output('btn-view-3d', 'active'),
    Input('results-store', 'data'),
    Input('btn-view-table', 'n_clicks'),
    Input('btn-view-3d', 'n_clicks'),
    prevent_initial_call=True
)
def render_modal_content(store_data, btn_table_clicks, btn_3d_clicks):
    """
    Legge lo Store e decide cosa mostrare.
    Versione aggiornata con Grafico 3D "Network Style" e tema moderno.
    Con gestione errori robusta.
    """
    try:
        if not store_data:
            raise dash.exceptions.PreventUpdate
        
        if 'error' in store_data:
            return dbc.Alert(store_data['error'], color="danger"), False, False

        # Determina quale vista mostrare
        ctx = dash.callback_context
        button_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else ''
        
        show_3d = False
        if button_id == 'btn-view-3d':
            show_3d = True

        # --- 1. Ricostruisci Dati ---
        if 'target_player' not in store_data or 'similar_players' not in store_data:
            return dbc.Alert("Errore: dati dei risultati non validi.", color="danger"), False, False
        
        target_player_data = store_data['target_player']
        similar_df = pd.DataFrame(store_data['similar_players'])
        style_name = store_data.get('target_style', 'N/A')
        
        # Valida che il dataframe non sia vuoto
        if similar_df.empty:
            return dbc.Alert("Nessun giocatore simile trovato.", color="warning"), False, False

        # --- 2. Costruisci Info Card ---
        pos_string = str(target_player_data.get('Pos', '-'))
        
        # Logica di formattazione ruoli migliorata
        if pos_string == '-':
            formatted_pos = '-'
        elif ',' in pos_string:
            # Se ci sono virgole (es. "DF,MF"), splitta e pulisci
            parts = [p.strip() for p in pos_string.split(',') if p.strip()]
            formatted_pos = ', '.join(parts)
        elif len(pos_string) > 2 and len(pos_string) % 2 == 0:
            # Se è tipo "DFMF", splitta ogni 2 caratteri
            formatted_pos = ', '.join([pos_string[i:i+2] for i in range(0, len(pos_string), 2)])
        else:
            formatted_pos = pos_string

        info_card = html.Div(className="player-info-card", children=[
            html.Div(className="player-info-header", children=[
                html.I(className="fas fa-user-circle"),
                html.H5("Giocatore Selezionato")
            ]),
            html.H3(target_player_data['Player'], className="player-info-name"),
            html.Div(className="player-info-details", children=[
                html.Div(className="info-item", children=[
                    html.Span("Posizione", className="info-label"),
                    html.Span(formatted_pos, className="info-value")
                ]),
                html.Div(className="info-item", children=[
                    html.Span("Ruolo", className="info-label"),
                    html.Span(style_name or '-', className="info-value") 
                ]),
                html.Div(className="info-item", children=[
                    html.Span("Età", className="info-label"),
                    html.Span(target_player_data.get('DisplayAge', '-'), className="info-value")
                ])
            ])
        ])

        content = None

        if show_3d:
            # --- 3A. Costruisci GRAFICO 3D "NETWORK STYLE" ---
            if ('PC1' in target_player_data and 'PC2' in target_player_data and 'PC3' in target_player_data and
                'PC1' in similar_df.columns and 'PC2' in similar_df.columns and 'PC3' in similar_df.columns):
                
                fig = go.Figure()

                # A. Costruisci le LINEE di connessione (Dal Target ai Simili)
                x_lines = []
                y_lines = []
                z_lines = []
                
                t_x, t_y, t_z = target_player_data['PC1'], target_player_data['PC2'], target_player_data['PC3']

                for _, row in similar_df.iterrows():
                    x_lines.extend([t_x, row['PC1'], None])
                    y_lines.extend([t_y, row['PC2'], None])
                    z_lines.extend([t_z, row['PC3'], None])

                # Aggiungi Trace Linee (Grigio chiaro, sottili)
                fig.add_trace(go.Scatter3d(
                    x=x_lines, y=y_lines, z=z_lines,
                    mode='lines',
                    name='Connessioni',
                    line=dict(color='rgba(100, 100, 100, 0.2)', width=2), # Colore più scuro e meno trasparente
                    hoverinfo='none',
                    showlegend=False
                ))

                # B. Aggiungi i VICINI (Sfere con bordo)
                fig.add_trace(go.Scatter3d(
                    x=similar_df['PC1'], y=similar_df['PC2'], z=similar_df['PC3'],
                    mode='markers+text', # Aggiunto 'text' per visualizzare sempre il nome
                    name='Simili',
                    text=similar_df['Player'],
                    textfont=dict(color='white', size=8), # Testo bianco e più piccolo
                    textposition='top center', # Posiziona il testo sopra il marker
                    hovertemplate='<b>%{text}</b><br>Distanza: %{customdata:.2f}<extra></extra>',
                    customdata=similar_df['Similarita (Distanza)'],
                    marker=dict(
                        size=8, # Dimensione leggermente aumentata
                        color='#30ABDC', 
                        opacity=0.9,
                        line=dict(color='white', width=1.5) # Bordo più spesso
                    )
                ))

                # C. Aggiungi il TARGET (Rombo Grande Rosso)
                fig.add_trace(go.Scatter3d(
                    x=[t_x], y=[t_y], z=[t_z],
                    mode='markers+text', # Aggiunto 'text' per visualizzare sempre il nome
                    name=f'{target_player_data["Player"]} (Tu)',
                    text=[target_player_data['Player']],
                    textfont=dict(color='red', size=10, family='Arial Black'), # Testo rosso più grande e grassetto
                    textposition='bottom center', # Posiziona il testo sotto il marker
                    hovertemplate='<b>%{text}</b><br>(Giocatore Cercato)<extra></extra>',
                    marker=dict(
                        size=10, # Ancora più grande per risaltare
                        color='#E11D48', 
                        symbol='diamond', 
                        opacity=1,
                        line=dict(color='white', width=3) # Bordo ancora più spesso
                    )
                ))

                # D. Layout "Pulito" e Moderno con tema scuro per risaltare
                fig.update_layout(
                    margin=dict(l=0, r=0, b=0, t=0),
                    scene=dict(
                        xaxis=dict(title='', showgrid=True, gridcolor='rgba(100,100,100,0.5)', showticklabels=False, zeroline=False, backgroundcolor='#303030'), # Sfondo scena più scuro
                        yaxis=dict(title='', showgrid=True, gridcolor='rgba(100,100,100,0.5)', showticklabels=False, zeroline=False, backgroundcolor='#303030'),
                        zaxis=dict(title='', showgrid=True, gridcolor='rgba(100,100,100,0.5)', showticklabels=False, zeroline=False, backgroundcolor='#303030'),
                        bgcolor='#202020', # Sfondo generale della scena più scuro
                        aspectmode='cube' # Mantiene le proporzioni
                    ),
                    paper_bgcolor='rgba(0,0,0,0)', # Lo sfondo del *modal* è già gestito da CSS
                    height=500, # Ancora più alto
                    showlegend=True,
                    legend=dict(x=0, y=1, bgcolor='rgba(40,40,40,0.7)', bordercolor='#505050', borderwidth=1, font=dict(color='white')), # Legenda scura con testo bianco
                    font=dict(color='white') # Testo generale del grafico bianco
                )
                
                content = dcc.Graph(figure=fig, config={'displayModeBar': True, 'modeBarButtonsToRemove': ['resetCameraLastSave3d', 'hoverClosest3d']})
            else:
                content = dbc.Alert("Dati vettoriali 3D non disponibili per questi giocatori.", color="warning")
        else:
            # --- 3B. Costruisci TABELLA ---
            # Gestisci la colonna distanza (potrebbe non esistere o essere 0 in modalità query diretta)
            if 'Similarita (Distanza)' in similar_df.columns:
                similar_df['Distanza'] = similar_df['Similarita (Distanza)'].round(3)
                # Se tutte le distanze sono 0, significa che è una query diretta
                is_query_diretta = (similar_df['Distanza'] == 0).all()
                if is_query_diretta:
                    # In modalità query diretta, mostra "Match" invece della distanza
                    similar_df['Distanza'] = 'Match ✓'
            else:
                similar_df['Distanza'] = 'N/A'
            
            # Assicura che le colonne esistano, altrimenti usa valori di default
            cols_needed = ['Player', 'DisplayAge', 'Comp', 'Distanza']
            for col in cols_needed:
                if col not in similar_df.columns:
                    similar_df[col] = 'N/A'
            
            display_df = similar_df[cols_needed].copy()
            display_df.columns = ['Nome Giocatore', 'Età', 'Campionato', 'Similarità']
            
            table = dbc.Table.from_dataframe(
                display_df, 
                striped=True, bordered=True, hover=True, size='sm'
            )
            content = html.Div(table, style={'maxHeight': '400px', 'overflowY': 'auto'})

        return [info_card, content], not show_3d, show_3d
    
    except PreventUpdate:
        raise
    except KeyError as e:
        print(f"Errore di chiave mancante in render_modal_content: {e}")
        import traceback
        traceback.print_exc()
        error_alert = dbc.Alert(f"Errore nella visualizzazione dei risultati: dati mancanti.", color="danger")
        return [error_alert], False, False
    except Exception as e:
        print(f"Errore generico in render_modal_content: {e}")
        import traceback
        traceback.print_exc()
        error_alert = dbc.Alert("Si è verificato un errore nella visualizzazione dei risultati.", color="danger")
        return [error_alert], False, False


# --- Callback 2d: Download CSV ---
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-download-csv", "n_clicks"),
    State("results-store", "data"),
    prevent_initial_call=True
)
def download_csv(n_clicks, store_data):
    if not n_clicks or not store_data or 'error' in store_data:
        raise PreventUpdate

    # Converti i dati dello store in DataFrame
    df = pd.DataFrame(store_data['similar_players'])
    
    # Pulisci il dataframe per l'export (Rimuovi colonne tecniche se vuoi)
    export_cols = ['Player', 'Team', 'Comp', 'DisplayAge', 'Similarita (Distanza)', 'Valore_Mercato']
    # Usa intersection per evitare errori se mancano colonne
    cols_to_use = [c for c in export_cols if c in df.columns]
    df_export = df[cols_to_use]
    
    # Nome file dinamico
    target_name = store_data['target_player']['Player'].replace(" ", "_")
    filename = f"AIScout_Simili_{target_name}.csv"

    return dcc.send_data_frame(df_export.to_csv, filename, index=False)
    
# --- NUOVA Callback: Toggle Filtri su Mobile ---
@app.callback(
    Output('db-filter-bar', 'style'),
    Input('mobile-filter-btn', 'n_clicks'),
    State('db-filter-bar', 'style'),
    prevent_initial_call=True
)
def toggle_mobile_filters(n_clicks, current_style):
    """
    Mostra o nasconde la barra dei filtri su mobile.
    """
    if current_style and current_style.get('display') == 'flex':
        # Se è visibile, nascondila
        return {'display': 'none'}
    else:
        # Se è nascosta, mostrala (come blocco flex verticale)
        return {'display': 'flex', 'flex-direction': 'column'}

# --- Callback 3: Dropdown Ruoli Dinamici (Scheda 3) ---
@app.callback(
    Output('db-filter-role', 'options'),
    Input('db-filter-pos', 'value'),
    Input('startup-interval', 'n_intervals') # Aggiorna anche quando i dati sono pronti
)
def update_role_options(selected_pos, n):
    if not selected_pos:
        return with_blank(data.all_roles_options)
    
    roles_for_pos = config.CLUSTER_NAMES_MAP.get(selected_pos, {})
    options = [{'label': role_name, 'value': role_name} 
               for role_name in sorted(roles_for_pos.values())]
    return with_blank(options)

# --- Callback 4: Reset Dropdown (Scheda 3) ---
@app.callback(
    Output('db-filter-pos', 'value'),
    Output('db-filter-role', 'value'),
    Output('db-filter-league', 'value'),
    Output('db-sort-by', 'value'),
    Input('db-filter-pos', 'value'),
    Input('db-filter-role', 'value'),
    Input('db-filter-league', 'value'),
    Input('db-sort-by', 'value'),
    prevent_initial_call=True
)
def reset_dropdown_when_blank(pos_value, role_value, league_value, sort_by_value):
    triggered = dash.ctx.triggered_id
    values = {
        'db-filter-pos': pos_value,
        'db-filter-role': role_value,
        'db-filter-league': league_value,
        'db-sort-by': sort_by_value
    }
    outputs = []
    for component_id in ['db-filter-pos', 'db-filter-role', 'db-filter-league', 'db-sort-by']:
        if triggered == component_id and values[component_id] == '':
            outputs.append(None)
        else:
            outputs.append(dash.no_update)
    return outputs

# --- Callback 5: Aggiornamento Tabella Database (Scheda 3) ---
@app.callback(
    Output('db-player-rows', 'children'),
    Output('db-page-info', 'children'),
    Output('db-pagination-store', 'data'),
    Input('db-filter-name', 'value'),
    Input('db-filter-pos', 'value'),
    Input('db-filter-role', 'value'),
    Input('db-filter-age-min', 'value'),
    Input('db-filter-age-max', 'value'),
    Input('db-filter-league', 'value'),
    Input('db-sort-by', 'value'),
    Input('db-prev-page', 'n_clicks'),
    Input('db-next-page', 'n_clicks'),
    State('db-pagination-store', 'data')
)
def update_database_table(name_value, pos_value, role_value, age_min_value, age_max_value, league_value, sort_by_value,
                          prev_clicks, next_clicks, pagination_state):
    
    df_filtered = _filter_database(name_value, pos_value, role_value, age_min_value, age_max_value, league_value, sort_by_value)
    
    total_records = len(df_filtered)
    total_pages = max(1, math.ceil(total_records / ROWS_PER_PAGE)) if total_records else 1

    current_page = (pagination_state or {}).get('page', 1)
    triggered_id = dash.ctx.triggered_id

    filter_ids = {'db-filter-name', 'db-filter-pos', 'db-filter-role', 
                  'db-filter-age-min', 'db-filter-age-max', 'db-filter-league', 'db-sort-by'}

    if triggered_id in filter_ids:
        current_page = 1
    elif triggered_id == 'db-prev-page' and current_page > 1:
        current_page -= 1
    elif triggered_id == 'db-next-page' and current_page < total_pages:
        current_page += 1
    else:
        current_page = max(1, min(current_page, total_pages))

    if current_page > total_pages:
        current_page = total_pages
    
    start_index = (current_page - 1) * ROWS_PER_PAGE
    end_index = start_index + ROWS_PER_PAGE
    page_df = df_filtered.iloc[start_index:end_index] if total_records else pd.DataFrame()

    if page_df.empty:
        rows_children = [html.Div("Nessun giocatore trovato con i filtri selezionati.", className='db-empty-state')]
    else:
        rows_children = []
        for offset, (_, row) in enumerate(page_df.iterrows()):
            display_index = start_index + offset + 1
            rows_children.append(
                html.Div(className='player-row', children=[
                    html.Span(str(display_index), className='row-index'),
                    html.Span([
                        html.I(className='fas fa-futbol row-icon'),
                        html.Span(row['Player'])
                    ], className='row-name'),
                    html.Span(row['Pos'] if row['Pos'] else '-', className='row-pos'),
                    html.Span(row['DisplayAge'] if row['DisplayAge'] else '-', className='row-age'),
                    html.Span(row['NationCode'] if row['NationCode'] else '-', className='row-nat'),
                    html.Span(row['Comp'] if row['Comp'] else '-', className='row-comp')
                ])
            )

    page_info = f"Pagina {current_page} di {total_pages if total_records else 1}"
    pagination_data = {
        'page': current_page,
        'total_pages': total_pages,
        'total_records': total_records
    }

    return rows_children, page_info, pagination_data

# --- Callback 0: Lazy Loading Check & Progress Update ---
@app.callback(
    Output('search-bar', 'options'),
    Output('startup-interval', 'disabled'),
    Output('loading-screen', 'style'),
    Output('main-content-wrapper', 'style'),
    Output('loading-progress-bar', 'value'), # Nuovo output
    Output('loading-text', 'children'),      # Nuovo output
    Input('startup-interval', 'n_intervals')
)
def check_data_loaded(n):
    """
    Controlla periodicamente se i dati E i modelli sono stati caricati dai thread in background.
    Aggiorna la barra di progresso.
    Appena sono pronti, popola la barra di ricerca, nasconde il loading screen e mostra l'app.
    """
    # Leggi stato globale
    current_progress = data.LOADING_PROGRESS
    current_status = data.LOADING_STATUS
    
    # print(f"DEBUG: check_data_loaded -> Progress: {current_progress}%, Status: {current_status}")
    
    data_ready = bool(data.PLAYER_SEARCH_OPTIONS)
    engine_ready = engine.artifacts_loaded if engine else True # Se engine è None (errore), non bloccare
    
    if data_ready and engine_ready:
        print("--- Dati e Modelli pronti! Aggiornamento UI... ---")
        # Nascondi loading screen, mostra contenuto principale
        return (
            data.PLAYER_SEARCH_OPTIONS, 
            True, # Disabilita interval
            {'display': 'none'}, # Nascondi Loading
            {'display': 'block'}, # Mostra App
            100, # Progress finale
            "Caricamento Completato!" # Testo finale
        )
    
    # Se non è ancora pronto, aggiorna solo la barra e il testo
    return (
        dash.no_update, 
        False, 
        dash.no_update, 
        dash.no_update,
        current_progress,
        current_status
    )

# --- Callback: Toggle Fullscreen (Disabilitato per Web App) ---
@app.callback(
    Output('btn-fullscreen-toggle', 'style'),
    Input('btn-fullscreen-toggle', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_fullscreen(n_clicks):
    # Nascondi il bottone fullscreen in web mode
    return {'display': 'none'}

# 4. --- Esecuzione Server ---
if __name__ == '__main__':
    app.run(debug=True, port=8050)
