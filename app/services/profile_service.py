"""Perfil de troca (#23): localização IBGE, contato com consentimento e exclusão de conta (LGPD)."""
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from ..extensions import db

_MUNICIPIOS = Path(__file__).resolve().parent.parent / "static" / "data" / "municipios_br.json"


@lru_cache(maxsize=1)
def municipios() -> dict[str, list[str]]:
    """{UF: [municípios]} — lista oficial do IBGE empacotada com o app."""
    return json.loads(_MUNICIPIOS.read_text(encoding="utf-8"))


def _key(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def resolve_city(state: str, city: str) -> tuple[str | None, str | None]:
    """
    Valida UF + cidade contra o IBGE, tolerando caixa e acentos ("fortaleza" → "Fortaleza").
    Retorna (UF, nome oficial) ou (None, None) se inválido.
    """
    uf = (state or "").strip().upper()
    cities = municipios().get(uf)
    if not cities:
        return None, None
    wanted = _key(city)
    for name in cities:
        if _key(name) == wanted:
            return uf, name
    return None, None


def normalize_whatsapp(raw: str) -> str | None:
    """
    Aceita "(85) 99999-1234", "85999991234", "+55 85 99999-1234".
    Retorna só dígitos com DDI 55 (formato do wa.me) ou None se inválido.
    """
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) not in (10, 11) or digits[0] == "0":
        return None
    return "55" + digits


def format_whatsapp(digits: str | None) -> str:
    """5585999991234 → (85) 99999-1234 (para exibir no formulário)."""
    if not digits:
        return ""
    d = digits[2:] if digits.startswith("55") else digits
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return d


def delete_account(user) -> None:
    """Apaga o treinador e tudo que pertence a ele (LGPD)."""
    from ..models.collection import UserCollection
    from ..models.individual import UserPokemon
    from ..models.wishlist import Wishlist
    from ..models.friendship import Friendship
    from ..models.trade import TradeMatch, WhatsappClick
    from ..models.event import AnalyticsEvent

    uid = user.id
    match_ids = [
        m.id for m in db.session.query(TradeMatch.id).filter(
            db.or_(TradeMatch.wisher_id == uid, TradeMatch.owner_id == uid)
        )
    ]
    q = db.session.query
    q(WhatsappClick).filter(
        db.or_(WhatsappClick.clicker_id == uid, WhatsappClick.match_id.in_(match_ids or [-1]))
    ).delete(synchronize_session=False)
    q(TradeMatch).filter(TradeMatch.id.in_(match_ids or [-1])).delete(synchronize_session=False)
    q(Friendship).filter(
        db.or_(Friendship.requester_id == uid, Friendship.addressee_id == uid)
    ).delete(synchronize_session=False)
    for model in (UserPokemon, UserCollection, Wishlist):
        q(model).filter(model.user_id == uid).delete(synchronize_session=False)
    # eventos de analytics ficam anônimos (sem vínculo com a pessoa)
    q(AnalyticsEvent).filter(AnalyticsEvent.user_id == uid).update(
        {AnalyticsEvent.user_id: None}, synchronize_session=False
    )
    db.session.delete(user)
    db.session.commit()
