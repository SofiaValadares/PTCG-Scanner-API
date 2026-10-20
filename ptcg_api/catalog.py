from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd

from ptcg_api.paths import SRC  # noqa: F401 — puts src/ on sys.path

from ocr.read_card import catalog_language_codes, fold_text, script_family

_STOPWORDS = {
    "de", "da", "do", "dos", "das", "e", "o", "a", "os", "as",
    "the", "of", "and", "s", "lv",
}
_WORD_EN = {
    "castelo": "castle",
    "espirito": "spirit",
    "luta": "fighting",
    "busca": "scouting",
    "bolsa": "bag",
    "faixa": "band",
    "escolha": "choice",
    "treino": "training",
    "perola": "pearl",
    "lilian": "lillie",
    "lillian": "lillie",
    "lilies": "lillie",
    "lupo": "hop",
    "vastro": "vstar",
    "preta": "black",
    "hisui": "hisuian",
}


def fold(text: str) -> str:
    return fold_text(text)


def parse_number(text: str) -> tuple[int | None, int | None]:
    match = re.search(r"(\d+)\s*[/-]\s*(\d+)", text or "")
    if match:
        return int(match.group(1)), int(match.group(2))
    digits = re.sub(r"\D", "", text or "")
    if len(digits) >= 3:
        return int(digits[:3]), int(digits[3:]) if len(digits) > 3 else None
    return None, None


def load_catalog(csv_path: Path, sets_path: Path) -> pd.DataFrame:
    raw = pd.read_csv(csv_path)
    cols = {c.lower(): c for c in raw.columns}
    if "name" not in cols or "number" not in cols or "setid" not in cols:
        raise ValueError(f"Catalog needs Name, Number, setId: {csv_path}")
    sets = pd.read_csv(sets_path)
    name_by_id = dict(zip(sets["id"].astype(str), sets["name"].astype(str)))
    rows = []
    for _, row in raw.iterrows():
        name = str(row[cols["name"]]).strip()
        number = str(row[cols["number"]]).strip()
        rarity = str(row[cols["rarity"]]).strip() if "rarity" in cols else ""
        set_id = str(row[cols["setid"]]).strip()
        collector, total = parse_number(number)
        rows.append(
            {
                "name": name,
                "number": number,
                "rarity": rarity,
                "set_id": set_id,
                "set_name": name_by_id.get(set_id, set_id),
                "collector": collector,
                "total": total,
                "name_fold": fold(name),
            }
        )
    catalog = pd.DataFrame(rows)
    catalog = catalog.drop_duplicates(subset=["name_fold", "number", "set_id"], keep="first")
    catalog["script"] = catalog["name_fold"].map(script_family)
    return catalog.reset_index(drop=True)


def load_catalogs(catalog_root: Path, preferred: str = "en") -> pd.DataFrame:
    langs = catalog_language_codes(catalog_root)
    if preferred in langs:
        langs = [preferred] + [lang for lang in langs if lang != preferred]
    frames = []
    for lang in langs:
        csv_path = catalog_root / lang / "cards.csv"
        sets_path = catalog_root / lang / "sets.csv"
        if not csv_path.is_file() or not sets_path.is_file():
            continue
        frame = load_catalog(csv_path, sets_path)
        frame["lang"] = lang
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No catalogs in {catalog_root}")
    catalog = pd.concat(frames, ignore_index=True)
    catalog = catalog.drop_duplicates(subset=["name_fold", "number", "set_id"], keep="first")
    return catalog.reset_index(drop=True)


def folded_words(text: str) -> list[str]:
    text = (text or "").replace("'s", " ").replace("’s", " ").replace(".", " ")
    words: list[str] = []
    for word in re.split(r"[^\w]+", text, flags=re.UNICODE):
        folded = fold(word)
        if not folded:
            continue
        match = re.match(r"^(.+?)(vstar|vastro|vmax|ex|gx)$", folded)
        if match and len(match.group(1)) >= 3:
            words.extend([match.group(1), match.group(2)])
        else:
            words.append(folded)
    return words


def name_tokens(text: str) -> set[str]:
    tokens = set()
    for word in folded_words(text):
        if word in _STOPWORDS or len(word) <= 1:
            continue
        tokens.add(_WORD_EN.get(word, word))
    return tokens


def edit_distance(left: str, right: str, limit: int = 2) -> int:
    if left == right:
        return 0
    if abs(len(left) - len(right)) > limit:
        return limit + 1
    if len(left) > len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for index, char in enumerate(left, start=1):
        current = [index]
        row_min = index
        for column, other in enumerate(right, start=1):
            cost = 0 if char == other else 1
            best = min(current[column - 1] + 1, previous[column] + 1, previous[column - 1] + cost)
            current.append(best)
            if best < row_min:
                row_min = best
        if row_min > limit:
            return limit + 1
        previous = current
    return previous[-1]


def similar_name(left: str, right: str) -> bool:
    if not left or not right or left == right:
        return left == right and bool(left)
    if edit_distance(left, right, 1) > 1:
        return False
    shortest = min(len(left), len(right))
    if abs(len(left) - len(right)) == 1:
        return shortest >= 4
    return shortest >= 5


def names_equivalent(a: str, b: str) -> bool:
    if not str(a or "").strip() or not str(b or "").strip():
        return False
    left_fold, right_fold = fold(a), fold(b)
    if left_fold == right_fold or similar_name(left_fold, right_fold):
        return True
    left, right = name_tokens(a), name_tokens(b)
    if not left or not right:
        return SequenceMatcher(None, left_fold, right_fold).ratio() >= 0.8
    inter = left & right
    if not inter:
        return SequenceMatcher(None, left_fold, right_fold).ratio() >= 0.8
    if left <= right or right <= left:
        return True
    jacc = len(inter) / len(left | right)
    if jacc >= 0.5 and any(len(token) >= 4 for token in inter):
        return True
    return jacc >= 0.66 or SequenceMatcher(None, left_fold, right_fold).ratio() >= 0.8


def name_score(ocr_name: str, cat_fold: str, cat_name: str) -> float:
    query = fold(ocr_name)
    if not query or not cat_fold:
        return 0.0
    q_fam, c_fam = script_family(query), script_family(cat_fold)
    if q_fam != "none" and c_fam != "none" and q_fam != c_fam:
        return 0.0
    distance = edit_distance(query, cat_fold, 2)
    if similar_name(query, cat_fold) or (cat_name and names_equivalent(ocr_name, cat_name)):
        return 1.0
    if distance == 2:
        return 0.9
    if query in cat_fold or cat_fold in query:
        return 0.88
    return SequenceMatcher(None, query, cat_fold).ratio()


def match_catalog(
    ocr_name: str,
    ocr_number: str,
    ocr_collection: str,
    catalog: pd.DataFrame,
    set_id: str = "",
    top_n: int = 3,
) -> pd.DataFrame:
    name_w, name_exact = 1000.0, 40.0
    number_w, number_near, total_w, set_w = 50.0, 15.0, 25.0, 10.0
    collector, total = parse_number(ocr_number)
    query = fold(ocr_name)
    collection_ids = set()
    if set_id:
        collection_ids.add(set_id)
    ocr_set = (ocr_collection or "").strip()
    if ocr_set and ocr_set in set(catalog["set_id"]):
        collection_ids.add(ocr_set)

    parts = []
    q_fam = script_family(query) if query else "none"
    names = catalog if q_fam in ("none", "") else catalog.loc[catalog["script"] == q_fam]
    if query:
        exact = names.loc[names["name_fold"] == query]
        if len(exact):
            parts.append(exact)
        else:
            close = names["name_fold"].map(lambda folded: edit_distance(query, folded, 2) <= 2)
            parts.append(names.loc[close])
    if collector is not None:
        near_cat = names if query else catalog
        near = near_cat["collector"].notna() & (near_cat["collector"] - collector).abs().le(2)
        parts.append(near_cat.loc[near])
    if not parts and collection_ids:
        parts.append(catalog.loc[catalog["set_id"].isin(collection_ids)])
    pool = catalog if not parts else pd.concat(parts).drop_duplicates()
    if pool.empty:
        pool = catalog

    scored = pool.copy()
    scores = np.zeros(len(scored), dtype=np.float32)
    scores += np.asarray(
        [
            name_w * name_score(ocr_name, folded, cat_name)
            for folded, cat_name in zip(scored["name_fold"], scored["name"])
        ],
        dtype=np.float32,
    )
    if query:
        scores += np.where(scored["name_fold"].to_numpy() == query, name_exact, 0.0)
    if collector is not None:
        same = scored["collector"].to_numpy() == collector
        scores += np.where(same, number_w, 0.0)
        near = scored["collector"].notna().to_numpy() & (
            np.abs(scored["collector"].to_numpy() - collector) <= 2
        )
        scores += np.where(near & ~same, number_near, 0.0)
        if total is not None:
            scores += np.where(scored["total"].to_numpy() == total, total_w, 0.0)
    if collection_ids:
        scores += np.where(scored["set_id"].isin(collection_ids).to_numpy(), set_w, 0.0)
    scored["score"] = scores
    return scored.sort_values("score", ascending=False).head(top_n).reset_index(drop=True)
