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
        "title": "Semana Mundial do Espaço",
        "category": "Evento Especial",
        "emoji": "🚀",
        "date": "4–10 de out",
        "description": "Pikachu Astronauta faz estreia mundial! Pesquisa temporária gratuita com encontro garantido.",
        "gradient": "from-indigo-500 to-blue-700",
        "badge": "bg-indigo-100 text-indigo-700",
        "url": "https://pokemongo.com/en/news/world-space-week-2026",
    },
    {
        "title": "Dia Comunitário — Zorua",
        "category": "Dia Comunitário",
        "emoji": "🦊",
        "date": "10 de out · 14h–17h",
        "description": "Zorua em destaque. Evolua para Zoroark e aprenda Soco Enganador. Bônus de PE e Doces.",
        "gradient": "from-gray-600 to-gray-900",
        "badge": "bg-gray-100 text-gray-700",
        "url": "https://pokemongo.com/en/news/communityday-october-2026-zorua",
    },
    {
        "title": "Maratona das Folhas: Caminhada Companheira",
        "category": "Evento Especial",
        "emoji": "🍃",
        "date": "13–19 de out",
        "description": "Bramblin estreia no GO! Mega Manectric alcança o Super Nível. Growlithe de Hisui com Incenso.",
        "gradient": "from-emerald-500 to-green-700",
        "badge": "bg-emerald-100 text-emerald-700",
        "url": "https://pokemongo.com/en/news/fall-marathon-buddy-trek-2026",
    },
    {
        "title": "Dia de Chocar Sandile",
        "category": "Hatch Day",
        "emoji": "🥚",
        "date": "17 de out",
        "description": "Sandile em Ovos de 2 km com mais chance de Brilhante! ½ distância de incubação e Candy extra.",
        "gradient": "from-amber-400 to-orange-600",
        "badge": "bg-amber-100 text-amber-700",
        "url": "https://pokemongo.com/en/news/sandile-hatch-day-2026",
    },
    {
        "title": "adidas × Pokémon GO",
        "category": "Parceria",
        "emoji": "👟",
        "date": "até 13 fev 2027",
        "description": "Visite uma loja adidas para desbloquear pesquisa com bonê, jaqueta e encontro com Lucario.",
        "gradient": "from-slate-600 to-black",
        "badge": "bg-slate-100 text-slate-700",
        "url": "https://pokemongo.com/news/pokemon-x-adidas-2026",
    },
    {
        "title": "Área Selvagem GO 2026",
        "category": "GO Wild Area",
        "emoji": "🌿",
        "date": "6–8 nov (presencial) · 14–15 nov (global)",
        "description": "Dialga e Palkia Dinamax estreiam! Evento presencial em Sendai e Cidade do México.",
        "gradient": "from-teal-500 to-cyan-700",
        "badge": "bg-teal-100 text-teal-700",
        "url": "https://pokemongo.com/gowildarea",
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
