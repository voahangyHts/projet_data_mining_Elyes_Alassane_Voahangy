"""Tests du quality gate (sans données : petits fichiers temporaires)."""
import json

import pytest

from src.quality_gate import main, verdict

ENTETE = "modele,seuil,roc_auc,pr_auc,f1,precision,rappel\n"


def preparer(tmp_path, pr_auc_xgb, score_champion=0.424, tolerance=0.005):
    resultats = tmp_path / "resultats.csv"
    resultats.write_text(
        ENTETE
        + "Baseline,0.18,0.824,0.397,0.424,0.366,0.505\n"
        + f"XGBoost,0.24,0.834,{pr_auc_xgb},0.442,0.418,0.47\n",
        encoding="utf-8",
    )
    champion = tmp_path / "champion.json"
    champion.write_text(
        json.dumps({
            "modele": "XGBoost",
            "metrique": "pr_auc",
            "score": score_champion,
            "tolerance": tolerance,
        }),
        encoding="utf-8",
    )
    return ["--resultats", str(resultats), "--champion", str(champion)], champion


def test_verdict_tolerance():
    assert verdict(0.424, 0.424, 0.0)
    assert verdict(0.420, 0.424, 0.005)
    assert not verdict(0.410, 0.424, 0.005)


def test_modele_identique_accepte(tmp_path):
    args, _ = preparer(tmp_path, 0.424)
    assert main(args) == 0


def test_modele_moins_bon_refuse(tmp_path):
    args, _ = preparer(tmp_path, 0.380)
    assert main(args) == 1


def test_le_meilleur_modele_est_le_candidat(tmp_path):
    # XGBoost s'effondre sous la baseline (0.397) : c'est la baseline
    # qui est comparée, et elle reste trop loin du champion -> refus
    args, _ = preparer(tmp_path, 0.100)
    assert main(args) == 1


def test_promotion_du_nouveau_champion(tmp_path):
    args, champion = preparer(tmp_path, 0.450)
    assert main(args + ["--promouvoir"]) == 0
    assert json.loads(champion.read_text(encoding="utf-8"))["score"] == 0.45


def test_pas_de_promotion_sans_option(tmp_path):
    args, champion = preparer(tmp_path, 0.450)
    assert main(args) == 0
    assert json.loads(champion.read_text(encoding="utf-8"))["score"] == 0.424


def test_metrique_absente(tmp_path):
    args, champion = preparer(tmp_path, 0.424)
    contenu = json.loads(champion.read_text(encoding="utf-8"))
    contenu["metrique"] = "inexistante"
    champion.write_text(json.dumps(contenu), encoding="utf-8")
    with pytest.raises(ValueError):
        main(args)
