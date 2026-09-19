"""
Búsqueda inteligente de parqueaderos (Sprint 3).

Objetivo: que la persona NO tenga que escribir el nombre exacto tal como
lo llamamos en la base de datos. Debe funcionar escribiendo "el de
ingeniería", "sur", "parqeadero nrte" (con errores de dedo), o incluso
una intención sin nombre como "el más desocupado" o "donde quepa mi
moto".

Cómo funciona, en orden:

1. Se normaliza el texto: minúsculas, sin tildes, sin signos. Así
   "Parqueadero Sur", "parqueadero sur" y "PARQEADERO SÚR" se comparan
   igual.

2. Se detecta la INTENCIÓN de la frase (ver INTENT_PATTERNS): si la
   persona pide "el más desocupado", "el más libre", "uno para moto" o
   "para discapacitados", eso reordena los resultados aunque no haya
   escrito ningún nombre.

3. Se puntúa cada parqueadero contra el texto, comparándolo con su
   nombre oficial Y con sus alias (ParkingLot.search_aliases, editables
   desde /admin/ sin tocar código). La puntuación combina:
     - coincidencia exacta o por prefijo   (la más fuerte)
     - que el término esté contenido       (fuerte)
     - parecido difuso con difflib         (tolera errores de dedo)

4. Se suma un pequeño bono por disponibilidad, para que entre dos
   parqueaderos que empatan en texto, gane el que de verdad le sirve a
   la persona (uno lleno no debería salir primero).

No usa librerías externas a propósito: difflib y unicodedata vienen con
Python, así que esto no agrega dependencias al proyecto.
"""

import difflib
import re
import unicodedata

# Umbral mínimo de puntaje para considerar que un resultado "sirve".
# Por debajo de esto, preferimos no mostrar nada antes que mostrar algo
# que claramente no es lo que buscaban.
MIN_SCORE = 0.34

# Palabras que no aportan a la búsqueda: si alguien escribe "el
# parqueadero de ingeniería", lo que importa es "ingeniería".
STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "al", "a", "en", "para", "por", "con", "que",
    "parqueadero", "parqueaderos", "parking", "celda", "celdas",
    "puesto", "puestos", "cupo", "cupos", "espacio", "espacios",
    "quiero", "busco", "necesito", "donde", "dónde", "hay", "esta", "está",
    "mas", "más", "mejor", "cual", "cuál", "me", "mi", "sirve", "quepa",
}

# Intenciones reconocidas. Cada una tiene patrones (ya normalizados, sin
# tildes) y una función que ordena los parqueaderos según esa intención.
INTENT_PATTERNS = [
    (
        "most_available",
        [
            r"\bmas (desocupado|libre|vacio|disponible|vacia)",
            r"\bmenos (lleno|ocupado|congestionado)",
            r"\bdonde (haya|hay) (mas )?(cupo|espacio|puesto)",
            r"\b(desocupado|vacio|libre)\b",
            r"\bcon (cupo|espacio|puesto)",
        ],
    ),
    (
        "motorcycle",
        [r"\bmoto", r"\bmotos\b", r"\bmotocicleta"],
    ),
    (
        "accessibility",
        [
            r"\bpmr\b",
            # "discapaci" (no "discapacida") para que cubra tanto
            # "discapacidad" como "discapacitado/a/s".
            r"\bdiscapaci",
            r"\bmovilidad reducida",
            r"\bsilla de ruedas",
            r"\baccesib",
            r"\binclusiv",
        ],
    ),
    (
        "car",
        [r"\bcarro", r"\bauto\b", r"\bautomovil", r"\bvehiculo\b"],
    ),
    (
        "fastest",
        [r"\bmas rapido", r"\bsin fila", r"\bsin espera", r"\bmenos espera", r"\brapido\b"],
    ),
]


def normalize(text):
    """minúsculas, sin tildes, sin puntuación, espacios colapsados."""
    if not text:
        return ""
    text = text.lower().strip()
    # Descompone los caracteres acentuados y descarta la marca del acento.
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9ñ\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def meaningful_terms(normalized_query):
    """Quita las palabras de relleno; si todo era relleno, deja el texto tal cual."""
    terms = [t for t in normalized_query.split() if t not in STOPWORDS and len(t) > 1]
    return terms or normalized_query.split()


def detect_intents(normalized_query):
    """Devuelve la lista de intenciones detectadas en la frase."""
    found = []
    for intent, patterns in INTENT_PATTERNS:
        if any(re.search(p, normalized_query) for p in patterns):
            found.append(intent)
    return found


def _text_score(term, candidate):
    """
    Qué tanto se parece `term` a `candidate` (ambos ya normalizados).
    Devuelve 0.0–1.0.
    """
    if not term or not candidate:
        return 0.0
    if term == candidate:
        return 1.0
    if candidate.startswith(term) or term.startswith(candidate):
        return 0.92
    if term in candidate or candidate in term:
        return 0.80

    # Parecido difuso: tolera "nrte" -> "norte", "guayabo" -> "guayabos".
    ratio = difflib.SequenceMatcher(None, term, candidate).ratio()

    # También comparamos contra cada palabra suelta del candidato, porque
    # "ingenieria" debe pegar con el alias "el de ingenieria".
    for word in candidate.split():
        ratio = max(ratio, difflib.SequenceMatcher(None, term, word).ratio())

    return ratio if ratio >= 0.7 else 0.0


def _lot_text_score(lot, terms):
    """
    Mejor puntaje de texto de este parqueadero contra los términos
    buscados, mirando su nombre oficial y todos sus alias.
    """
    candidates = [normalize(lot.name)] + [normalize(a) for a in lot.alias_list]
    candidates = [c for c in candidates if c]
    if not candidates or not terms:
        return 0.0

    # Para cada término buscado tomamos su mejor coincidencia, y luego
    # promediamos: así "parqueadero sur" no se ve castigado porque
    # "parqueadero" sea genérico, pero "sur ingenieria" (dos términos que
    # apuntan a lugares distintos) tampoco puntúa altísimo por uno solo.
    per_term = []
    for term in terms:
        per_term.append(max(_text_score(term, c) for c in candidates))

    best = max(per_term)
    average = sum(per_term) / len(per_term)
    # Pesamos más el mejor término que el promedio: encontrar una palabra
    # muy buena vale más que que todas sean tibias.
    return (best * 0.7) + (average * 0.3)


def _availability_bonus(lot):
    """
    Bono pequeño (0.0–0.12) por disponibilidad real. Sirve de desempate:
    entre dos parqueaderos que coinciden igual de bien con el texto,
    conviene mostrar primero el que tiene cupo.
    """
    if lot.occupancy_status == "full":
        return 0.0
    return round((1.0 - lot.occupancy_ratio) * 0.12, 4)


def _intent_bonus(lot, intents):
    """Bono por cumplir lo que la persona pidió sin nombrar un parqueadero."""
    bonus = 0.0

    if "most_available" in intents:
        # Hasta +0.6: esto domina cuando la persona no nombró ninguno.
        bonus += (1.0 - lot.occupancy_ratio) * 0.6

    if "motorcycle" in intents:
        if lot.available_motorcycles > 0:
            bonus += 0.45
        elif lot.capacity_motorcycles == 0:
            bonus -= 0.35  # no recibe motos: no tiene sentido recomendarlo

    if "accessibility" in intents:
        if lot.available_accessibility > 0:
            bonus += 0.45
        elif lot.capacity_accessibility == 0:
            bonus -= 0.35

    if "car" in intents:
        if lot.available_cars > 0:
            bonus += 0.35
        elif lot.capacity_cars == 0:
            bonus -= 0.35

    if "fastest" in intents:
        bonus += (1.0 - lot.occupancy_ratio) * 0.4

    return bonus


def _match_reason(lot, terms, intents):
    """
    Explicación corta de por qué salió este resultado, para mostrarla
    bajo el nombre. Que la persona entienda el porqué hace la búsqueda
    mucho menos mágica y más confiable.
    """
    if "motorcycle" in intents and lot.available_motorcycles > 0:
        return f"{lot.available_motorcycles} cupo(s) de moto libres"
    if "accessibility" in intents and lot.available_accessibility > 0:
        return f"{lot.available_accessibility} cupo(s) PMR libres"
    if "car" in intents and lot.available_cars > 0:
        return f"{lot.available_cars} cupo(s) de carro libres"
    if "most_available" in intents or "fastest" in intents:
        return f"{lot.available_spaces} de {lot.total_capacity} celdas libres"

    # Si pegó por un alias (y no por el nombre oficial), vale la pena
    # decirlo: así la persona ve que entendimos "el de ingeniería".
    normalized_name = normalize(lot.name)
    for alias in lot.alias_list:
        normalized_alias = normalize(alias)
        for term in terms:
            if _text_score(term, normalized_alias) >= 0.8 and _text_score(term, normalized_name) < 0.8:
                return f'También conocido como "{alias}"'

    return f"{lot.available_spaces} de {lot.total_capacity} celdas libres"


def search_parking_lots(query, lots, limit=4):
    """
    Busca entre `lots` (lista de ParkingLot ya cargados) y devuelve una
    lista de dicts ordenada por relevancia:

        [{"lot": <ParkingLot>, "score": 0.93, "reason": "..."}, ...]

    Si la consulta está vacía devuelve [] (el home muestra su orden
    normal, no hace falta buscar).
    """
    normalized = normalize(query)
    if not normalized:
        return []

    intents = detect_intents(normalized)
    terms = meaningful_terms(normalized)

    # Si la frase es SOLO una intención ("el más desocupado"), no hay
    # nombre que buscar: puntuamos únicamente por intención.
    only_intent = bool(intents) and all(
        _lot_text_score(lot, terms) < 0.5 for lot in lots
    )

    results = []
    for lot in lots:
        text_score = 0.0 if only_intent else _lot_text_score(lot, terms)
        score = text_score + _intent_bonus(lot, intents) + _availability_bonus(lot)

        if only_intent:
            # Sin texto que comparar, el umbral lo pone la intención.
            passes = bool(intents)
        else:
            passes = text_score >= MIN_SCORE or (intents and score >= MIN_SCORE)

        if passes:
            results.append({
                "lot": lot,
                "score": round(score, 4),
                "reason": _match_reason(lot, terms, intents),
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]
