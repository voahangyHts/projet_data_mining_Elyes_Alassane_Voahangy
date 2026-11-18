"""Quality gate : refuse un nouveau modèle moins bon que le champion.

Compare le meilleur modèle de reports/classification_resultats.csv au
champion enregistré dans reports/champion.json, sur la métrique choisie
(PR-AUC : adaptée aux classes déséquilibrées, ~10 % de réachats).

- Nouveau score >= champion - tolérance : accepté (code de sortie 0)
- Nouveau score <  champion - tolérance : refusé  (code de sortie 1,
  ce qui fait échouer GitHub Actions et « dvc repro »)

Lancement :
  uv run python -m src.quality_gate              # vérifier
  uv run python -m src.quality_gate --promouvoir # accepté et meilleur :
                                                 # devient le champion
"""

import argparse
import csv
import json
import sys
from pathlib import Path

RESULTATS = Path("reports/classification_resultats.csv")
CHAMPION = Path("reports/champion.json")


def lire_resultats(chemin: Path, metrique: str) -> list[dict]:
    """Lit les scores des modèles ; erreur claire si la métrique manque."""
    with chemin.open(encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))
    if not lignes:
        raise ValueError(f"{chemin} ne contient aucun modèle")
    if metrique not in lignes[0]:
        raise ValueError(f"colonne « {metrique} » absente de {chemin}")
    return [{**l, metrique: float(l[metrique])} for l in lignes]


def meilleur(resultats: list[dict], metrique: str) -> dict:
    """Le candidat : le modèle qui a le meilleur score."""
    return max(resultats, key=lambda l: l[metrique])


def verdict(candidat: float, champion: float, tolerance: float) -> bool:
    """True si le candidat n'est pas moins bon que le champion."""
    return candidat >= champion - tolerance


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--resultats", type=Path, default=RESULTATS)
    parser.add_argument("--champion", type=Path, default=CHAMPION)
    parser.add_argument(
        "--promouvoir",
        action="store_true",
        help="si le candidat est meilleur, l'enregistrer comme champion",
    )
    args = parser.parse_args(argv)

    champion = json.loads(args.champion.read_text(encoding="utf-8"))
    metrique = champion["metrique"]
    tolerance = champion.get("tolerance", 0.0)
    cand = meilleur(lire_resultats(args.resultats, metrique), metrique)
    score = cand[metrique]

    print(f"Champion : {champion['modele']} — {metrique} = {champion['score']:.3f}")
    print(f"Candidat : {cand['modele']} — {metrique} = {score:.3f}")
    print(f"Écart    : {score - champion['score']:+.3f} (tolérance {tolerance})")

    if not verdict(score, champion["score"], tolerance):
        print("REFUSÉ : le nouveau modèle est moins bon que le champion.")
        return 1

    print("ACCEPTÉ : le nouveau modèle est au moins aussi bon que le champion.")
    if args.promouvoir and score > champion["score"]:
        champion.update(modele=cand["modele"], score=score)
        args.champion.write_text(
            json.dumps(champion, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Nouveau champion enregistré dans {args.champion}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
