"""
AIScout - Version Management
Sistema di versioning semantico: MAJOR.MINOR.PATCH
"""

# Versione principale dell'applicazione
__version__ = "2.0.0"

# Informazioni aggiuntive
VERSION_INFO = {
    "major": 2,
    "minor": 0,
    "patch": 0,
    "release_date": "2025-11-26",
    "codename": "Second Release"
}

def get_version_string():
    """Restituisce la stringa di versione formattata"""
    return f"v{__version__}"

def get_full_version_string():
    """Restituisce la versione completa con data"""
    return f"v{__version__} ({VERSION_INFO['release_date']})"
