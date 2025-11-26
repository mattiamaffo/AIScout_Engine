from dash import dcc, html # type: ignore
import config
from data import all_roles_options, with_blank, SORT_BY_OPTIONS

database_layout = html.Div(className='glass-card db-layout-wrapper', style={'maxWidth': '95%', 'marginTop': '2rem'}, children=[
    dcc.Store(id='db-pagination-store', data={'page': 1, 'total_pages': 1, 'total_records': 0}),

    html.Div(className='glass-card-content', children=[
        # --- Header Section ---
        html.Div(className='db-header', children=[
            html.H3("Database Scouting", className='glass-subtitle'),
            html.P("Esplora, filtra e analizza l'intero database giocatori", className='identikit-sub')
        ]),

        # --- Filters Section ---
        html.Div(className='db-filters-container', children=[
            # Row 1: Search Name (Full Width)
            html.Div(className='db-search-row', children=[
                html.I(className="fas fa-search search-icon"),
                dcc.Input(
                    id='db-filter-name', 
                    placeholder='Cerca giocatore per nome...', 
                    className='db-search-input',
                    debounce=True
                )
            ]),
            
            # Row 2: Grid Filters
            html.Div(className='db-filters-grid', children=[
                # Position
                html.Div(className='filter-group', children=[
                    html.Label("Posizione", className='filter-label'),
                    dcc.Dropdown(
                        id='db-filter-pos',
                        options=with_blank([{'label': p, 'value': p} for p in config.RUOLI]),
                        placeholder='Tutte',
                        className='db-dropdown',
                        searchable=False,
                        clearable=True
                    )
                ]),
                # Role
                html.Div(className='filter-group', children=[
                    html.Label("Ruolo", className='filter-label'),
                    dcc.Dropdown(
                        id='db-filter-role',
                        options=with_blank(all_roles_options),
                        placeholder='Tutti',
                        className='db-dropdown',
                        searchable=False,
                        clearable=True
                    )
                ]),
                # Age Min
                html.Div(className='filter-group', children=[
                    html.Label("Età Min", className='filter-label'),
                    dcc.Input(
                        id='db-filter-age-min', 
                        placeholder='16', 
                        className='db-input-number',
                        type='number',
                        min=15, max=45
                    )
                ]),
                # Age Max
                html.Div(className='filter-group', children=[
                    html.Label("Età Max", className='filter-label'),
                    dcc.Input(
                        id='db-filter-age-max', 
                        placeholder='45', 
                        className='db-input-number',
                        type='number',
                        min=15, max=45
                    )
                ]),
                # League
                html.Div(className='filter-group', children=[
                    html.Label("Campionato", className='filter-label'),
                    dcc.Dropdown(
                        id='db-filter-league',
                        options=with_blank([{'label': l, 'value': l} for l in config.LEAGUES_LIST]),
                        placeholder='Tutti',
                        className='db-dropdown',
                        searchable=False,
                        clearable=True
                    )
                ]),
                # Sort By
                html.Div(className='filter-group', children=[
                    html.Label("Ordina per", className='filter-label'),
                    dcc.Dropdown(
                        id='db-sort-by',
                        options=with_blank(SORT_BY_OPTIONS),
                        placeholder='Seleziona...',
                        className='db-dropdown',
                        searchable=False,
                        clearable=True
                    )
                ]),
            ])
        ]),

        # --- Results Table Section ---
        html.Div(className='db-results-wrapper', children=[
            html.Div(className='db-table-header', children=[
                html.Span("#", className='col-header col-index'),
                html.Span("Giocatore", className='col-header col-name'),
                html.Span("Pos", className='col-header col-pos'),
                html.Span("Età", className='col-header col-age'),
                html.Span("Naz", className='col-header col-nat'),
                html.Span("Camp", className='col-header col-league'),
            ]),
            
            # Rows Container (Scrollable)
            html.Div(id='db-player-rows', className='db-table-body')
        ]),

        # --- Pagination Footer ---
        html.Div(className='db-pagination-footer', children=[
            html.Button(html.I(className='fas fa-chevron-left'), id='db-prev-page', className='pagination-btn'),
            html.Span("Pagina 1 di 1", id='db-page-info', className='pagination-info'),
            html.Button(html.I(className='fas fa-chevron-right'), id='db-next-page', className='pagination-btn')
        ])
    ])
])
