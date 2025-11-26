from dash import dcc, html # type: ignore
import dash_bootstrap_components as dbc # type: ignore
from version import get_full_version_string

# Import layouts from separate files
from layouts.search_layout import search_player_layout
from layouts.identikit_layout import identikit_layout
from layouts.ai_layout import ai_assistant_layout
from layouts.database_layout import database_layout

# --- Funzione Layout Principale ---

def create_main_layout():
    """
    Crea il layout principale dell'app.
    """
    return html.Div(
        id='main-container',
        className='layout-home',
        style={'minHeight': '100vh', 'boxSizing': 'border-box', 'position': 'relative'},
        children=[
            # --- Store per i trigger di ricerca ---
            dcc.Store(id='search-trigger-store'),
            
            # --- NUOVO: Store per i RISULTATI (Dati + Info Giocatore) ---
            # Questo permette di passare i dati tra tabella, grafico e download senza ricalcolare
            dcc.Store(id='results-store'),

            # --- NUOVO: Store per la richiesta AI (Split Callback) ---
            dcc.Store(id='ai-request-store'),

            # --- NUOVO: Componente per il Download CSV ---
            dcc.Download(id="download-dataframe-csv"),
            
            # --- NUOVO: Componente per il Download PDF Report ---
            dcc.Download(id="download-report-pdf"),
            
            # --- NUOVO: Interval per startup (Fix Error) ---
            dcc.Interval(id='startup-interval', interval=1000, n_intervals=0, max_intervals=1),

            html.Img(id='app-logo', src='/assets/new_logo.png'),
            
            # --- Numero di Versione (Bottom Left) ---
            html.Div(
                className='app-version',
                children=get_full_version_string(),
                title='Versione AIScout'
            ),
            
            html.Div(id='app-navbar', className='segmented-control', children=[
                html.Div(className='nav-slider'),
                html.Button(html.I(className="fas fa-search"), id='tab-search', n_clicks=0, className='icon-nav-item active'),
                html.Button(html.I(className="fas fa-file-alt"), id='tab-identikit', n_clicks=0, className='icon-nav-item'),
                html.Button(html.I(className="fas fa-robot"), id='tab-ai-assistant', n_clicks=0, className='icon-nav-item'),
                html.Button(html.I(className="fas fa-database"), id='tab-database', n_clicks=0, className='icon-nav-item')
            ]),
            # Global hidden holder for k-slider (keeps the id available to callbacks)
            dcc.Input(id='k-slider', type='number', value=10, style={'display': 'none'}),
            
            # Store per chat history (session storage)
            dcc.Store(id='chat-history', storage_type='session', data=[]),
            
            # Include all tab layouts simultaneously (shown/hidden via CSS)
            html.Div(id='tab-content-search', children=search_player_layout, style={'display': 'block'}, className='tab-content-animated'),
            html.Div(id='tab-content-identikit', children=identikit_layout, style={'display': 'none'}, className='tab-content-animated'),
            html.Div(id='tab-content-ai-assistant', children=ai_assistant_layout, style={'display': 'none'}, className='tab-content-animated'),
            html.Div(id='tab-content-database', children=database_layout, style={'display': 'none'}, className='tab-content-animated'),
            

            # --- Popup (Modal) Aggiornato ---
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Giocatori Simili")),
                    dbc.ModalBody(
                        dcc.Loading(
                            id="modal-loading-spinner",
                            type="default",
                            # Il contenuto verrà iniettato qui dalla callback
                            children=html.Div(id="modal-results-content") 
                        )
                    ),
                    dbc.ModalFooter(
                        html.Div(style={'display': 'flex', 'gap': '10px', 'width': '100%', 'justifyContent': 'space-between'}, children=[
                            
                            # --- Gruppo Bottoni Sinistra (Azioni) ---
                            html.Div(style={'display': 'flex', 'gap': '10px'}, children=[
                                dbc.Button(
                                    [html.I(className="fas fa-table me-2"), "Tabella"], 
                                    id="btn-view-table", 
                                    color="light", 
                                    className="me-1",
                                    n_clicks=0,
                                    active=True # Default attivo
                                ),
                                dbc.Button(
                                    [html.I(className="fas fa-cube me-2"), "Spazio 3D"], 
                                    id="btn-view-3d", 
                                    color="primary", 
                                    outline=True,
                                    n_clicks=0
                                ),
                            ]),

                            # --- Gruppo Bottoni Destra (Download & Chiudi) ---
                            html.Div(style={'display': 'flex', 'gap': '10px'}, children=[
                                dbc.Button(
                                    [html.I(className="fas fa-download me-2"), "CSV"], 
                                    id="btn-download-csv", 
                                    color="success", 
                                    outline=True,
                                    n_clicks=0
                                ),
                                dbc.Button(
                                    "Chiudi", 
                                    id="modal-close-button", 
                                    color="secondary",
                                    n_clicks=0
                                )
                            ])
                        ])
                    ),
                ],
                id="results-modal",
                is_open=False,
                size="lg",
                backdrop="static",
                scrollable=True
            ),
        ]
    )