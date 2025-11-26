from dash import dcc, html # type: ignore
import config
from data import with_blank

identikit_layout = html.Div(className='glass-card', style={'maxWidth': '1200px', 'marginTop': '2rem'}, children=[
    html.Div(className='glass-card-content', children=[
        html.Div(className='identikit-header', children=[
            html.H3('Identikit', className='glass-subtitle'),
            html.P('Costruisci il tuo giocatore ideale', className='identikit-sub')
        ]),

        html.Div(className='identikit-grid-container', children=[
            # LEFT: Form Section
            html.Div(className='identikit-form-section', children=[
                html.H5("Parametri di Ricerca", className="section-title"),
                
                # Position & Cluster Row
                html.Div(className='form-row', children=[
                    html.Div(className='form-group', children=[
                        html.Label("Posizione", className="form-label"),
                        dcc.Dropdown(
                            id='identikit-pos',
                            options=with_blank([{'label': p, 'value': p} for p in config.RUOLI]),
                            placeholder='Seleziona Posizione...',
                            clearable=True,
                            className='identikit-dropdown'
                        ),
                    ]),
                    html.Div(className='form-group', children=[
                        html.Label("Stile / Cluster", className="form-label"),
                        dcc.Dropdown(
                            id='identikit-cluster',
                            options=with_blank([]),
                            placeholder='Seleziona Stile...',
                            clearable=True,
                            className='identikit-dropdown'
                        ),
                    ]),
                ]),

                # Age & League Row
                html.Div(className='form-row', children=[
                    html.Div(className='form-group', children=[
                        html.Label("Età Massima", className="form-label"),
                        dcc.Input(
                            id='identikit-age', 
                            type='number', 
                            placeholder='Es. 25', 
                            className='identikit-input', 
                            min=16, max=45
                        ),
                    ]),
                    html.Div(className='form-group', children=[
                        html.Label("Campionato", className="form-label"),
                        dcc.Dropdown(
                            id='identikit-league',
                            options=with_blank([{'label': l, 'value': l} for l in config.LEAGUES_LIST]),
                            placeholder='Tutti i Campionati',
                            clearable=True,
                            className='identikit-dropdown'
                        ),
                    ]),
                ]),

                # Nation Row
                html.Div(className='form-row', children=[
                    html.Div(className='form-group full-width', children=[
                        html.Label("Nazione", className="form-label"),
                        dcc.Dropdown(
                            id='identikit-nation',
                            options=with_blank([]),
                            placeholder='Tutte le Nazioni',
                            clearable=True,
                            className='identikit-dropdown'
                        ),
                    ]),
                ]),

                html.Div(className='identikit-actions', children=[
                    html.Button('Cerca', id='identikit-find-button', n_clicks=0, className='search-button'),
                    html.Button('Reset', id='identikit-reset-button', n_clicks=0, className='reset-button')
                ])
            ]),

            # RIGHT: Features Section
            html.Div(className='identikit-features-section', children=[
                html.H5('Caratteristiche del Ruolo', className='section-title'),
                html.Div(id='identikit-role-features', className='features-container')
            ])
        ]),

        # LEGEND: Collapsible
        html.Details(className='identikit-legend-details', children=[
            html.Summary("Mostra Legenda Caratteristiche", className='legend-summary'),
            html.Div(className='legend-grid', children=[
                    # Metriche Offensive
                html.Div(className='legend-item', children=[
                    html.Span('Gls', className='legend-key'),
                    html.Span('Goal segnati', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('Ast', className='legend-key'),
                    html.Span('Assist forniti', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('G+A', className='legend-key'),
                    html.Span('Goal + Assist', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('xG', className='legend-key'),
                    html.Span('Expected Goals (gol attesi)', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('npxG', className='legend-key'),
                    html.Span('Non-Penalty Expected Goals', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('G-PK', className='legend-key'),
                    html.Span('Goal senza rigori', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('xAG', className='legend-key'),
                    html.Span('Expected Assisted Goals', className='legend-value')
                ]),
                # Passaggi e Creazione
                html.Div(className='legend-item', children=[
                    html.Span('KP', className='legend-key'),
                    html.Span('Key Passes (passaggi chiave)', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('PPA', className='legend-key'),
                    html.Span('Passaggi nell\'area avversaria', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('PrgP', className='legend-key'),
                    html.Span('Passaggi progressivi', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('Cmp%', className='legend-key'),
                    html.Span('Percentuale completamento passaggi', className='legend-value')
                ]),
                # Possesso e Movimento
                html.Div(className='legend-item', children=[
                    html.Span('Touches', className='legend-key'),
                    html.Span('Tocchi di palla', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('Carries', className='legend-key'),
                    html.Span('Conduzioni palla', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('PrgC', className='legend-key'),
                    html.Span('Conduzioni progressive', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('PrgR', className='legend-key'),
                    html.Span('Ricezioni progressive', className='legend-value')
                ]),
                # Difesa
                html.Div(className='legend-item', children=[
                    html.Span('Tkl', className='legend-key'),
                    html.Span('Tackle tentati', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('TklW', className='legend-key'),
                    html.Span('Tackle vinti', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('Int', className='legend-key'),
                    html.Span('Intercettazioni', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('Tkl+Int', className='legend-key'),
                    html.Span('Tackle + Intercettazioni', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('Blocks', className='legend-key'),
                    html.Span('Tiri bloccati', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('Clr', className='legend-key'),
                    html.Span('Respinte difensive', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('Recov', className='legend-key'),
                    html.Span('Recuperi palla', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('Err', className='legend-key'),
                    html.Span('Errori che portano a tiri', className='legend-value')
                ]),
                # Errori e Altro
                html.Div(className='legend-item', children=[
                    html.Span('Dis', className='legend-key'),
                    html.Span('Palloni persi', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('Mis', className='legend-key'),
                    html.Span('Errori di controllo', className='legend-value')
                ]),
                # Portieri
                html.Div(className='legend-item', children=[
                    html.Span('GA', className='legend-key'),
                    html.Span('Goal subiti', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('Saves', className='legend-key'),
                    html.Span('Parate effettuate', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('Save%', className='legend-key'),
                    html.Span('Percentuale parate', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('CS', className='legend-key'),
                    html.Span('Clean Sheets (porta inviolata)', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('CS%', className='legend-key'),
                    html.Span('Percentuale Clean Sheets', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('PKA', className='legend-key'),
                    html.Span('Rigori subiti', className='legend-value')
                ]),
                html.Div(className='legend-item', children=[
                    html.Span('PKsv', className='legend-key'),
                    html.Span('Rigori parati', className='legend-value')
                ]),
            ])
        ])
    ])
])
