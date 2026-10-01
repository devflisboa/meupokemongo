from datetime import date
from flask import render_template
from flask_login import current_user
from . import bp
from ...services.collection_service import get_collection_stats, get_missing_pokemon, get_pending_evolutions
from ...services.matching_service import get_active_matches_for_user
from ...services.analytics_service import log_event
from ...extensions import db
from ...models.user import User

# Meses em inglês para montar a URL do site oficial
_MONTH_EN = {
    1: "january", 2: "february", 3: "march", 4: "april",
    5: "may", 6: "june", 7: "july", 8: "august",
    9: "september", 10: "october", 11: "november", 12: "december",
}

GAME_EVENTS = [
    {
        "title": "Dia Comunitário de Outubro",
        "category": "Dia Comunitário",
        "emoji": "🌟",
        "date": "5 de out · 14h–17h",
        "description": "Capture Pokémon com taxas especiais e ganhe bônus de Candy × 3.",
        "gradient": "from-blue-400 to-blue-600",
        "badge": "bg-blue-100 text-blue-700",
        "url": "https://pokemongo.com/pt-BR/events/october-2026",
    },
    {
        "title": "Halloween 2026: Noite das Sombras",
        "category": "Evento Especial",
        "emoji": "🎃",
        "date": "15–31 de out",
        "description": "Pokémon sombrios e fantasmagóricos com aparições aumentadas.",
        "gradient": "from-orange-400 to-purple-600",
        "badge": "bg-orange-100 text-orange-700",
        "url": "https://pokemongo.com/pt-BR/events/october-2026",
    },
    {
        "title": "Hora do Spotlight — Phantump",
        "category": "Hora do Spotlight",
        "emoji": "⭐",
        "date": "6 de out · 18h–19h",
        "description": "Phantump com aparições em massa e bônus de Stardust × 2.",
        "gradient": "from-amber-300 to-amber-500",
        "badge": "bg-amber-100 text-amber-700",
        "url": "https://pokemongo.com/pt-BR/events/october-2026",
    },
    {
        "title": "Hora de Reide — Mega Gengar",
        "category": "Hora de Reide",
        "emoji": "⚔️",
        "date": "8 de out · 18h–19h",
        "description": "Mega Gengar em Reides de 5 estrelas com chance de forma shiny.",
        "gradient": "from-red-400 to-red-700",
        "badge": "bg-red-100 text-red-700",
        "url": "https://pokemongo.com/pt-BR/events/october-2026",
    },
    {
        "title": "Pesquisa Especial: Missão Espectral",
        "category": "Pesquisa Especial",
        "emoji": "📜",
        "date": "1–15 de out",
        "description": "Complete etapas de pesquisa para encontrar um Pokémon raro.",
        "gradient": "from-emerald-400 to-emerald-600",
        "badge": "bg-emerald-100 text-emerald-700",
        "url": "https://pokemongo.com/pt-BR/events/october-2026",
    },
    {
        "title": "Temporada das Colheitas",
        "category": "Temporada",
        "emoji": "🍂",
        "date": "1 out – 31 dez",
        "description": "Temporada outonal com Pokémon regionais e bônus sazonais.",
        "gradient": "from-yellow-400 to-amber-600",
        "badge": "bg-yellow-100 text-yellow-700",
        "url": "https://pokemongo.com/pt-BR/events/october-2026",
    },
]


@bp.route("/")
def index():
    log_event("PAGE_VIEW", {"page": "home"})

    stats = None
    missing = []
    pending_evolutions = []
    matches = []

    if current_user.is_authenticated:
        stats = get_collection_stats(current_user.id)
        missing = get_missing_pokemon(current_user.id)[:5]
        pending_evolutions = get_pending_evolutions(current_user.id)[:3]
        matches = get_active_matches_for_user(current_user.id)[:4]

    total_trainers = db.session.query(User).count()

    today = date.today()
    events_page_url = (
        f"https://pokemongo.com/pt-BR/events/{_MONTH_EN[today.month]}-{today.year}"
    )

    return render_template(
        "main/index.html",
        stats=stats,
        missing=missing,
        pending_evolutions=pending_evolutions,
        matches=matches,
        total_trainers=total_trainers,
        game_events=GAME_EVENTS,
        events_page_url=events_page_url,
    )
