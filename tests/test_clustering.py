"""Tests de la numérotation stable des segments (sans données)."""
import numpy as np

from src.clustering import numeroter_segments


def test_segments_numerotes_par_nb_commandes_croissant():
    # le K-means a appelé « 0 » le groupe des gros clients
    labels = np.array([0, 0, 1, 1, 2, 2])
    nb_commandes = np.array([30, 34, 5, 7, 10, 12])
    assert numeroter_segments(labels, nb_commandes).tolist() == [2, 2, 0, 0, 1, 1]


def test_meme_groupes_meme_numeros_quel_que_soit_le_label_kmeans():
    nb_commandes = np.array([30, 34, 5, 7, 10, 12])
    a = numeroter_segments(np.array([0, 0, 1, 1, 2, 2]), nb_commandes)
    b = numeroter_segments(np.array([2, 2, 0, 0, 1, 1]), nb_commandes)
    assert a.tolist() == b.tolist()
