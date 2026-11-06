import asyncio
import calendar
import datetime
import json
import math
import os
import random
import sys
import unicodedata
from collections import deque

import pygame

LARGEUR, HAUTEUR = 1180, 740

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]
MOIS_COURTS = ["janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"]

DATE_DEBUT = datetime.date(2026, 11, 2)          # un lundi
COUT_EMPLOYE = 2300                              # coût employeur mensuel d'un temps plein (approx.)
DUREE_SERVICE = 180                              # 3 h de jeu = 180 s réelles à vitesse x1
DEBUTS = [11 * 60 + 30, 18 * 60 + 30]            # 11h30 et 18h30
NOMS_SERVICES = ["midi", "soir"]
VITESSES = [1, 2, 4, 8]
JOUR_MULT = [1.0, 1.0, 1.0, 1.0, 1.05, 0.65, 0.0]  # lundi..dimanche (samedi plus calme)
PLACES_PAR_TRAVAUX = 4
# Niveaux de local (1, 2, 3) : un local plus grand coûte plus cher mais attire plus de monde et accueille plus d'équipe
NIVEAU_FONDS = [1.0, 1.8, 3.0]                   # coefficient sur le fonds de commerce
NIVEAU_LOYER = [1.0, 1.6, 2.4]                   # coefficient sur le loyer
NIVEAU_TRAFIC = [1.0, 1.4, 1.8]                 # coefficient sur l'affluence
NIVEAU_TRAVAUX = [1.0, 1.6, 2.4]                 # coefficient sur le prix des travaux d'agrandissement
NIVEAU_EMPLOYES = [10, 14, 18]                   # vendeurs maximum
NIVEAU_MAX = 3
PART_EMPRUNTEE = 0.80                            # part du fonds de commerce financée par un prêt (apport : 20 %)
TAUX_PRET = 0.045                                # taux annuel
DUREE_PRET = 84                                  # mois (7 ans)
REVENTE_FONDS = 0.80                             # part du fonds de commerce récupérée à la revente
REVENTE_TRAVAUX = 0.40                           # part des travaux récupérée à la revente
SALAIRE_COMMERCIAL = 4200                        # responsable commercial (mensuel, pour toute l'entreprise)
SALAIRE_GESTIONNAIRE = 3100                      # gestionnaire de stock (mensuel, par boutique, avant coefficient local)
REMISE_COMMERCIAL = 0.20                         # remise sur toutes les campagnes de pub
BONUS_COMMERCIAL = 0.15                          # les campagnes attirent 15 % de clients en plus
MARGE_STOCK = 1.15                               # marge sur les quantités à commander
MARGE_STOCK_SAMEDI = 1.15                        # idem le samedi (mets 1.10 pour une marge réduite)
BONUS_PUB_MAX = 3.0                              # plafond cumulé des campagnes (+300 %)
# Ingrédients premium : chaque étoile ajoute 0,1 à la note /5 des recettes qui utilisent l'ingrédient
ETOILES_MAX = 5
ETOILES_PRIX = [1.0, 1.25, 1.55, 1.90, 2.30, 2.80]   # coefficient sur le prix d'achat selon le nombre d'étoiles
ETOILES_REP = [0, 30, 42, 54, 66, 78]                # réputation nécessaire pour débloquer chaque étoile
NOTE_PAR_ETOILE = 0.1                                # points de note (/5) par étoile
APPEAL_PAR_ETOILE = NOTE_PAR_ETOILE / 4              # la note vaut 3,5 + 4 x (attrait - 1)
APPEAL_MAX = 1.375                                   # attrait correspondant à 5/5
PRIX_REF_PAR_ETOILE = 0.02                           # le prix de référence d'une recette monte de 2 % par étoile
# Formule boisson + dessert (produits achetés tout faits, revendus environ 3 fois leur prix d'achat)
FORMULE_TAUX = 0.40                                  # part des clients qui prennent la formule
FORMULE_REMISE = 0.10                                # remise sur la boisson et le dessert de la formule
# Réputation de chaque boutique : elle décide de l'affluence. Il faut convaincre pour faire venir du monde.
AFFLUENCE_BASE = 0.90                                # coefficient général sur l'affluence (1.0 = plus de clients)
CAPACITE_CONFORT = 45                                # clients par vendeur et par service avant que des files se forment
REP_ALPHA = 0.00025                                   # vitesse d'évolution de la réputation d'une boutique, par client
REP_PREMIERE = 30.0                                  # réputation de départ de la première boutique
REP_OUVERTURE = 12.0                                 # réputation de départ d'une nouvelle boutique
OUVERTURE_JOURS_MAX = 30                             # l'offre d'ouverture n'est possible que le premier mois
PROMO_PAUSE = 14                                     # jours de pause après une promotion
PROMOS = {
    "ouverture": {"nom": "Offre d'ouverture", "remise": 0.25, "clients": 1.6, "rep": 3.0, "jours": 14, "cout": 150},
    "standard": {"nom": "Promotion", "remise": 0.15, "clients": 1.3, "rep": 1.5, "jours": 7, "cout": 100},
}
# Comptable et développeur
HONORAIRES_BASE = 350                                # honoraires mensuels du comptable
HONORAIRES_PAR_BOUTIQUE = 120                        # + par boutique
PENALITE_SANS_COMPTABLE = 0.15                       # majoration de la TVA et de l'impôt déclarés sans comptable
MODULES_DASH = [                                     # (clé, titre, prix, jours de livraison)
    ("ensemble", "Vue d'ensemble", 6000, 7),
    ("sandwichs", "Analyse des sandwichs", 5000, 7),
    ("boutiques", "Suivi des boutiques", 8000, 10),
    ("finances", "Comptes et impôts", 9000, 14),
]
# Concurrents : (type, probabilité par boutique et par jour, durée en jours, coef clients, coef prix de référence, texte)
EVENEMENTS = [
    ("ouverture", 0.004, 90, 0.88, 0.93, "Un concurrent s'installe près de {nom}"),
    ("promo", 0.012, 10, 0.92, 0.90, "Promotion agressive d'un concurrent près de {nom}"),
    ("fermeture", 0.004, 45, 1.10, 1.00, "Un concurrent ferme près de {nom}"),
]

# ---------------------------------------------------------------- DONNEES

# Prix de base d'une portion de chaque ingrédient, HT (le prix varie de +-2 % par jour)
INGREDIENTS = [
    ("Pain", 0.35), ("Jambon", 0.80), ("Beurre", 0.12), ("Poulet", 1.10),
    ("Crudités", 0.40), ("Thon", 0.95), ("Mayonnaise", 0.15),
    ("Saucisson", 1.20), ("Fromage", 0.55), ("Légumes grillés", 0.70),
]
BOISSONS = [("Eau minérale", 0.30), ("Cola", 0.45), ("Jus d'orange", 0.55), ("Thé glacé", 0.50), ("Café", 0.35)]
DESSERTS = [("Cookie", 0.55), ("Brownie", 0.80), ("Tarte aux pommes", 1.10)]
ING_NOMS = [n for n, _ in INGREDIENTS]
ING_SET = set(ING_NOMS)
ARTICLES = INGREDIENTS + BOISSONS + DESSERTS          # tout ce qui se stocke
PRIX_BASE = dict(ARTICLES)
PRIX_VENTE_EXTRAS = {n: round(p * 3, 2) for n, p in BOISSONS + DESSERTS}   # revendus 3 fois le prix d'achat
POIDS_BOISSONS = {"Eau minérale": 0.25, "Cola": 0.25, "Jus d'orange": 0.15, "Thé glacé": 0.15, "Café": 0.20}
POIDS_DESSERTS = {"Cookie": 0.40, "Brownie": 0.35, "Tarte aux pommes": 0.25}

# Durée de conservation en jours : un lot acheté le jour J est utilisable jusqu'au jour J + durée (inclus)
DUREES = {
    "Pain": 2, "Jambon": 5, "Beurre": 30, "Poulet": 3, "Crudités": 3,
    "Thon": 4, "Mayonnaise": 10, "Saucisson": 14, "Fromage": 10, "Légumes grillés": 4,
    "Eau minérale": 180, "Cola": 120, "Jus d'orange": 20, "Thé glacé": 60, "Café": 90,
    "Cookie": 12, "Brownie": 10, "Tarte aux pommes": 4,
}

# Fiscalité par pays. France : taux en vigueur (10 % sur les plats préparés, sur place comme à emporter ;
# 5,5 % sur les boissons et desserts conditionnés vendus à emporter ; IS à 15 % jusqu'à 42 500 € de bénéfice si le
# chiffre d'affaires est inférieur à 10 M€, puis 25 %). Les autres pays sont des ordres de grandeur simplifiés.
# Clés : plat_emporter, plat_place, reduit (boissons et desserts à emporter), achat (TVA sur les achats),
# is (taux d'impôt sur les bénéfices), locales (taxes locales, part du loyer annuel).
FISCALITE = {
    "France": {"plat_emporter": 0.10, "plat_place": 0.10, "reduit": 0.055, "achat": 0.055, "is": 0.25, "locales": 0.06},
    "Belgique": {"plat_emporter": 0.06, "plat_place": 0.12, "reduit": 0.06, "achat": 0.06, "is": 0.25, "locales": 0.04},
    "Suisse": {"plat_emporter": 0.026, "plat_place": 0.081, "reduit": 0.026, "achat": 0.026, "is": 0.14, "locales": 0.03},
    "Royaume-Uni": {"plat_emporter": 0.20, "plat_place": 0.20, "reduit": 0.20, "achat": 0.0, "is": 0.25, "locales": 0.05},
    "Espagne": {"plat_emporter": 0.10, "plat_place": 0.10, "reduit": 0.10, "achat": 0.10, "is": 0.25, "locales": 0.04},
    "Italie": {"plat_emporter": 0.10, "plat_place": 0.10, "reduit": 0.10, "achat": 0.10, "is": 0.24, "locales": 0.04},
    "Pays-Bas": {"plat_emporter": 0.09, "plat_place": 0.09, "reduit": 0.09, "achat": 0.09, "is": 0.25, "locales": 0.04},
    "Allemagne": {"plat_emporter": 0.07, "plat_place": 0.07, "reduit": 0.07, "achat": 0.07, "is": 0.30, "locales": 0.04},
    "Canada": {"plat_emporter": 0.14975, "plat_place": 0.14975, "reduit": 0.14975, "achat": 0.0, "is": 0.265, "locales": 0.04},
    "États-Unis": {"plat_emporter": 0.0889, "plat_place": 0.0889, "reduit": 0.0889, "achat": 0.0, "is": 0.26, "locales": 0.05},
    "Japon": {"plat_emporter": 0.08, "plat_place": 0.10, "reduit": 0.08, "achat": 0.08, "is": 0.30, "locales": 0.03},
    "Émirats arabes unis": {"plat_emporter": 0.05, "plat_place": 0.05, "reduit": 0.05, "achat": 0.05, "is": 0.09, "locales": 0.02},
    "Singapour": {"plat_emporter": 0.09, "plat_place": 0.09, "reduit": 0.09, "achat": 0.09, "is": 0.17, "locales": 0.03},
    "Australie": {"plat_emporter": 0.10, "plat_place": 0.10, "reduit": 0.10, "achat": 0.0, "is": 0.30, "locales": 0.03},
}
CHAMPS_FISCAUX = ("ca_ht", "cogs", "pertes", "salaires", "loyers", "interets", "autres", "locales", "honoraires")


def impot_societes(pays, profit, ca_groupe):
    """Impôt sur les bénéfices d'un pays pour l'exercice en cours."""
    if profit <= 0:
        return 0.0
    if pays != "France":
        return profit * FISCALITE[pays]["is"]
    if ca_groupe < 10_000_000:
        impot = min(profit, 42500) * 0.15 + max(0.0, profit - 42500) * 0.25
    else:
        impot = profit * 0.25
    if ca_groupe >= 7_630_000:                       # contribution sociale de 3,3 % au-delà de 763 000 € d'IS
        impot += 0.033 * max(0.0, impot - 763000)
    return impot


def facteur_reputation(rep):
    """Part de l'affluence qui vient avec la réputation : 20 -> 0,29 ; 50 -> 0,73 ; 70 -> 0,97 ; 90 -> 1,28."""
    return 0.15 + 1.35 * (max(0.0, min(100.0, rep)) / 100) ** 1.4


def acc_vide():
    return {"ca_ttc": 0.0, "ca_ht": 0.0, "extras_ht": 0.0, "tva_coll": 0.0, "tva_deduc": 0.0, "achats_ht": 0.0,
            "cogs": 0.0, "pertes": 0.0, "salaires": 0.0, "loyers": 0.0, "interets": 0.0, "prets": 0.0,
            "autres": 0.0, "locales": 0.0, "honoraires": 0.0, "penalites": 0.0, "servis": 0, "att": 0, "rup": 0, "salle": 0, "formules": 0}


def jours_du_mois(d):
    return calendar.monthrange(d.year, d.month)[1]


def premier_mois_suivant(d):
    return datetime.date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def maximum_places(depart):
    """Places maximales d'un local : on peut ajouter des tranches de 4 places, environ +50 %."""
    paliers = max(1, int(depart * 0.5 / PLACES_PAR_TRAVAUX + 0.5))
    return depart + PLACES_PAR_TRAVAUX * paliers


def sieges_niveau(base, niveau):
    """Places de départ et places maximales d'un local. Un local de niveau supérieur démarre plus grand
    que le maximum du niveau précédent."""
    depart = base
    maxi = maximum_places(depart)
    for _ in range(niveau - 1):
        depart = maxi + PLACES_PAR_TRAVAUX
        maxi = maximum_places(depart)
    return depart, maxi


def cle_lieu(lieu_):
    return lieu_["ville"] + "/" + lieu_["nom"]


def nb_resto(g, ville=None):
    return sum(1 for r in g.restos if ville is None or r["lieu"]["ville"] == ville)


def nb_etranger(g):
    return sum(1 for r in g.restos if r["lieu"]["pays"] != "France")


def nb_actifs(g):
    return sum(1 for m in g.menu if m["etat"] == "actif")


RECETTES = [
    {"nom": "Jambon-beurre", "ing": ["Pain", "Jambon", "Beurre"], "prix_ref": 4.80,
     "dev": 0, "reqs": []},
    {"nom": "Poulet-crudités", "ing": ["Pain", "Poulet", "Crudités", "Mayonnaise"], "prix_ref": 6.20,
     "dev": 0, "reqs": []},
    {"nom": "Thon-mayo", "ing": ["Pain", "Thon", "Crudités", "Mayonnaise"], "prix_ref": 5.60,
     "dev": 150, "reqs": [("Réputation 30+", lambda g: g.rep >= 30)]},
    {"nom": "Végétarien", "ing": ["Pain", "Légumes grillés", "Fromage", "Crudités"], "prix_ref": 6.20,
     "dev": 250, "reqs": [("Réputation 40+", lambda g: g.rep >= 40)]},
    {"nom": "Le Lyonnais", "ing": ["Pain", "Saucisson", "Fromage", "Beurre"], "prix_ref": 6.80,
     "dev": 400, "reqs": [("Réputation 50+", lambda g: g.rep >= 50)]},
]


def lieu(ville, pays, nom, cout, loyer, trafic, part_midi, emporter, sieges, sens, reqs,
         salaire=1.0, niveau=1.0, cout_ing=1.0):
    """salaire = coefficient sur le salaire local, niveau = coefficient sur les prix de vente locaux,
    cout_ing = coefficient sur le prix des ingrédients."""
    return {"ville": ville, "pays": pays, "nom": nom, "cout": cout, "loyer": loyer, "trafic": trafic,
            "part_midi": part_midi, "emporter": emporter, "sieges": sieges, "sens": sens, "reqs": reqs,
            "salaire": salaire, "niveau": niveau, "cout_ing": cout_ing}


def rep_min(n):
    return (f"Réputation {n}+", lambda g: g.rep >= n)


def resto_min(n):
    return (f"{n} restaurants ouverts", lambda g: nb_resto(g) >= n)


def etranger_min(n):
    return (f"{n} restaurant{'s' if n > 1 else ''} à l'étranger", lambda g: nb_etranger(g) >= n)


# Pour ajouter une ville : copie une ligne, change les chiffres et les conditions.
# lieu(ville, pays, nom, fonds de commerce (local de niveau 1), loyer/mois, affluence, part du midi, part à emporter,
#      places, sensibilité au prix, conditions, coefficient salaires, coefficient prix de vente, coefficient ingrédients)
# Les prix du fonds de commerce sont des ordres de grandeur : annonces de sandwicheries de 40 à 120 m² en France
# (Lyon : 150 000 à 300 000 €, Paris : 100 000 à 450 000 €), estimations pour l'étranger.
LIEUX = [
    lieu("Lyon", "France", "Part-Dieu", 200000, 2800, 150, 0.70, 0.75, 8, 1.2, []),
    lieu("Lyon", "France", "République", 280000, 3600, 220, 0.55, 0.60, 14, 1.2,
         [rep_min(40), ("Avoir lancé une pub", lambda g: g.pubs_lancees >= 1)]),
    lieu("Lyon", "France", "Université", 150000, 2600, 200, 0.50, 0.70, 16, 2.0,  # étudiants : sensibles au prix
         [rep_min(45), ("3 sandwichs au menu", lambda g: nb_actifs(g) >= 3)]),
    lieu("Paris", "France", "Châtelet", 550000, 7000, 450, 0.60, 0.65, 20, 1.0,
         [rep_min(60), ("3 restaurants à Lyon", lambda g: nb_resto(g, "Lyon") >= 3),
          ("4 sandwichs au menu", lambda g: nb_actifs(g) >= 4)], 1.1, 1.15, 1.05),
    lieu("Paris", "France", "Quartier Latin", 260000, 4200, 380, 0.50, 0.55, 18, 1.8,
         [rep_min(65), ("1 restaurant à Paris", lambda g: nb_resto(g, "Paris") >= 1)], 1.1, 1.10, 1.05),
    lieu("Paris", "France", "La Défense", 480000, 8200, 520, 0.78, 0.70, 16, 0.9,
         [rep_min(68), ("2 restaurants à Paris", lambda g: nb_resto(g, "Paris") >= 2)], 1.1, 1.20, 1.05),
    lieu("Marseille", "France", "Vieux-Port", 220000, 4200, 300, 0.55, 0.65, 16, 1.2,
         [rep_min(66), resto_min(5)]),
    lieu("Bordeaux", "France", "Saint-Pierre", 200000, 3800, 280, 0.55, 0.60, 14, 1.3,
         [rep_min(68), resto_min(6)]),
    lieu("Lille", "France", "Grand-Place", 190000, 3400, 270, 0.55, 0.60, 14, 1.2,
         [rep_min(70), resto_min(7)]),
    lieu("Bruxelles", "Belgique", "Grand-Place", 260000, 4800, 340, 0.55, 0.65, 16, 1.2,
         [rep_min(72), resto_min(8)], 1.05, 1.05, 1.0),
    lieu("Toulouse", "France", "Capitole", 185000, 3600, 270, 0.55, 0.60, 14, 1.3,
         [rep_min(70), resto_min(9)]),
    lieu("Nantes", "France", "Bouffay", 160000, 3400, 260, 0.55, 0.60, 14, 1.3,
         [rep_min(70), resto_min(10)]),
    lieu("Genève", "Suisse", "Cornavin", 650000, 9500, 330, 0.65, 0.65, 14, 0.9,
         [rep_min(74), etranger_min(1)], 1.7, 1.7, 1.3),
    lieu("Barcelone", "Espagne", "Eixample", 320000, 5200, 400, 0.55, 0.60, 18, 1.2,
         [rep_min(74), etranger_min(1)], 0.8, 0.95, 0.95),
    lieu("Londres", "Royaume-Uni", "Soho", 900000, 12500, 480, 0.55, 0.70, 14, 1.0,
         [rep_min(76), etranger_min(2)], 1.35, 1.5, 1.15),
    lieu("Milan", "Italie", "Duomo", 520000, 7200, 430, 0.60, 0.65, 16, 1.1,
         [rep_min(76), etranger_min(2)], 0.95, 1.15, 1.05),
    lieu("Amsterdam", "Pays-Bas", "Centrum", 450000, 6800, 420, 0.55, 0.70, 14, 1.1,
         [rep_min(76), etranger_min(3)], 1.3, 1.35, 1.1),
    lieu("Berlin", "Allemagne", "Mitte", 300000, 5600, 430, 0.55, 0.70, 16, 1.2,
         [rep_min(76), etranger_min(3)], 1.05, 1.1, 1.0),
    lieu("Montréal", "Canada", "Plateau", 330000, 6800, 430, 0.55, 0.65, 16, 1.2,
         [rep_min(78), etranger_min(4)], 1.15, 1.3, 1.15),
    lieu("New York", "États-Unis", "Midtown", 1400000, 18000, 560, 0.65, 0.80, 12, 0.9,
         [rep_min(78), etranger_min(5)], 1.7, 1.8, 1.25),
    lieu("Tokyo", "Japon", "Shibuya", 800000, 11000, 560, 0.60, 0.75, 12, 1.0,
         [rep_min(78), etranger_min(6)], 0.95, 1.3, 1.1),
    lieu("Dubaï", "Émirats arabes unis", "Marina", 1100000, 16000, 520, 0.55, 0.70, 14, 0.9,
         [rep_min(78), etranger_min(7)], 0.9, 2.0, 1.3),
    lieu("Singapour", "Singapour", "Raffles Place", 1000000, 15000, 540, 0.65, 0.75, 12, 0.9,
         [rep_min(78), etranger_min(8)], 1.0, 1.7, 1.2),
    lieu("Sydney", "Australie", "Surry Hills", 700000, 11000, 470, 0.55, 0.65, 14, 1.1,
         [rep_min(78), etranger_min(9)], 1.5, 1.5, 1.3),
]

PUBS = [
    {"nom": "Réseaux sociaux", "cout": 250, "bonus": 0.20, "jours": 7},
    {"nom": "Panneaux en ville", "cout": 900, "bonus": 0.45, "jours": 10},
    {"nom": "Spot TV régional (20h)", "cout": 9000, "bonus": 0.50, "jours": 7, "tv": True},
    {"nom": "Spot TV national (grande écoute)", "cout": 60000, "bonus": 0.90, "jours": 10, "tv": True},
    {"nom": "Match de championnat (mi-temps)", "cout": 140000, "bonus": 1.30, "jours": 10, "tv": True},
    {"nom": "Finale de coupe / grand match", "cout": 400000, "bonus": 2.00, "jours": 14, "tv": True},
]

LIBELLES = {
    "prep_midi": "Préparation du service du midi",
    "midi": "Service du midi (11:30 - 14:30)",
    "prep_soir": "Préparation du service du soir",
    "soir": "Service du soir (18:30 - 21:30)",
    "bilan": "Fermeture : bilan de la journée",
    "ferme": "Dimanche : fermé",
}


def heure(minute):
    return f"{minute // 60:02d}:{minute % 60:02d}"


def eur(x, dec=0):
    if abs(x) < 0.5 * 10 ** -dec:
        x = 0.0
    return f"{x:,.{dec}f} €".replace(",", " ")


def poisson(lam):
    if lam <= 0:
        return 0
    limite = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        p *= random.random()
        if p <= limite:
            return k
        k += 1


def profil(idx):
    # Les clients arrivent petit à petit, avec un pic en milieu de service
    centre, ecart = (65, 40) if idx == 0 else (75, 45)
    poids = [math.exp(-0.5 * ((t - centre) / ecart) ** 2) for t in range(DUREE_SERVICE)]
    total = sum(poids)
    return [p / total for p in poids]


PROFILS = [profil(0), profil(1)]


def stats_vides():
    return {"servis": 0, "att": 0, "rup": 0, "salle": 0, "ca": 0.0, "ht": 0.0, "formules": 0}


# ---------------------------------------------------------------- LOGIQUE

# ---------------------------------------------------------------- SAUVEGARDE

DOSSIER_SAUVEGARDES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sauvegardes")
VERSION_SAUVEGARDE = 1
AUTOSAVE = False      # activé par main() : une auto-sauvegarde est écrite chaque matin


def _enc(x):
    """Prépare une donnée pour le JSON : dates, tuples, ensembles."""
    if isinstance(x, dict):
        return {k: _enc(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set, deque)):
        return [_enc(v) for v in x]
    if isinstance(x, datetime.date):
        return {"__date__": x.isoformat()}
    return x


def _dec(x):
    if isinstance(x, dict):
        if set(x) == {"__date__"}:
            return datetime.date.fromisoformat(x["__date__"])
        return {k: _dec(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_dec(v) for v in x]
    return x


def chemin_sauvegarde(nom):
    return os.path.join(DOSSIER_SAUVEGARDES, nom + ".json")


def _cle_stockage_web(nom):
    return f"sandwich_empire_{nom}"


def _lire_donnees_sauvegarde(nom):
    """Lit une sauvegarde depuis localStorage dans le navigateur ou depuis le disque sur ordinateur."""
    try:
        if sys.platform == "emscripten":
            from platform import window
            brut = window.localStorage.getItem(_cle_stockage_web(nom))
            if brut is None:
                return None
            return json.loads(str(brut))
        with open(chemin_sauvegarde(nom), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def ecrire_sauvegarde(g, nom):
    donnees = {
        "version": VERSION_SAUVEGARDE,
        "meta": {"enregistre": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "date_jeu": g.date.isoformat(),
                 "caisse": g.caisse, "restos": len(g.restos)},
        "etat": g.vers_dict(),
    }
    if sys.platform == "emscripten":
        # Les sauvegardes restent dans le navigateur de l'utilisateur, sans serveur ni compte.
        from platform import window
        window.localStorage.setItem(_cle_stockage_web(nom), json.dumps(donnees, ensure_ascii=False))
        return
    os.makedirs(DOSSIER_SAUVEGARDES, exist_ok=True)
    chemin = chemin_sauvegarde(nom)
    with open(chemin + ".tmp", "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False)
    os.replace(chemin + ".tmp", chemin)


def lire_meta(nom):
    donnees = _lire_donnees_sauvegarde(nom)
    return donnees.get("meta") if donnees else None


def lire_sauvegarde(nom):
    """Retourne la partie sauvegardée, ou None si le fichier est absent ou illisible."""
    donnees = _lire_donnees_sauvegarde(nom)
    if not donnees:
        return None
    try:
        return Jeu.depuis_dict(donnees["etat"])
    except Exception:
        return None


class Jeu:
    def __init__(self):
        self.date = DATE_DEBUT
        self.caisse = 8000.0
        self.rep = REP_PREMIERE                   # réputation de la marque : moyenne pondérée des boutiques
        self.prix_ing = dict(PRIX_BASE)
        self.prix_veille = dict(PRIX_BASE)
        self.menu = []
        for rec in RECETTES:
            actif = rec["dev"] == 0
            self.menu.append({
                "rec": rec, "etat": "actif" if actif else "verrouille",
                # attrait caché : on le découvre grâce aux avis après quelques ventes
                "appeal": random.uniform(0.9, 1.1) if actif else random.uniform(0.65, 1.35),
                "ventes": 0, "ventes_jour": 0,
            })
        self.pubs = []
        self.pubs_lancees = 0
        self.restos = []
        self.sel = 0                      # boutique sélectionnée dans l'interface
        self.commercial = None            # responsable commercial : {"depuis": date} ou None
        self.comptable = None             # comptable : {"depuis": date} ou None
        self.modules = {}                 # tableaux de bord commandés : clé -> date de livraison
        self.locaux_vendus = {}           # locaux vendus, en attente du rachat d'un local de niveau supérieur
        self.phase = "prep_midi"
        self.minute = 10 * 60
        self.service_idx = 0
        self.vitesse = 1
        self.pause = False
        self.onglet = "courses"
        self.journal = deque(maxlen=4)
        self.fini = False
        self.etoiles = {n: 0 for n in ING_NOMS}   # niveau premium de chaque ingrédient (0 à 5 étoiles)
        self.formule = True                       # formule boisson + dessert
        self.mois = acc_vide()                    # compteurs du mois en cours
        self.mois_sand = {}                       # par recette : ventes, CA HT, coût des produits
        self.mois_resto = {}                      # par boutique
        self.mois_extras = {}                     # boissons et desserts vendus
        self.annee = {}                           # comptes de l'exercice par pays (pour l'impôt sur les bénéfices)
        self.is_paye = {}
        self.tva_credit = 0.0
        self.historique = []                      # un résumé par mois écoulé
        self.ruptures = set()
        self.ouvrir_resto(LIEUX[0], premier=True, prix_fonds=LIEUX[0]["cout"] * 0.5)
        self.restos[0]["rep"] = REP_PREMIERE
        self.log("Bienvenue ! Un employé t'aide à Part-Dieu. Commande tes ingrédients avant le service du midi.")

    # --- sauvegarde
    def vers_dict(self):
        """État complet de la partie (hors service : les clients en cours ne sont pas conservés)."""
        d = {}
        for cle, val in vars(self).items():
            if cle == "ruptures":
                continue
            if cle == "menu":
                d[cle] = [{**{k: v for k, v in mn.items() if k != "rec"}, "rec": mn["rec"]["nom"]} for mn in val]
            elif cle == "restos":
                restos = []
                for r in val:
                    c = dict(r)
                    c["lieu"] = cle_lieu(r["lieu"])
                    for k in ("file", "prep", "mangent", "cuis", "taux"):
                        c[k] = []
                    restos.append(c)
                d[cle] = restos
            else:
                d[cle] = val
        return _enc(d)

    @classmethod
    def depuis_dict(cls, donnees):
        d = _dec(donnees)
        g = cls.__new__(cls)
        recettes = {rec["nom"]: rec for rec in RECETTES}
        lieux = {cle_lieu(x): x for x in LIEUX}
        for cle, val in d.items():
            setattr(g, cle, val)
        g.menu = [{**mn, "rec": recettes[mn["rec"]]} for mn in d["menu"]]
        for r in g.restos:
            r["lieu"] = lieux[r["lieu"]]
        g.journal = deque(d["journal"], maxlen=4)
        g.ruptures = set()
        g.pause = False
        if g.phase in ("midi", "soir"):       # ne devrait pas arriver : on reprend au début du service
            g.phase = "prep_midi" if g.phase == "midi" else "prep_soir"
        base = cls()                          # valeurs par défaut des champs ajoutés depuis la sauvegarde
        for cle, val in vars(base).items():
            if not hasattr(g, cle):
                setattr(g, cle, val)
        return g

    # --- utilitaires
    def log(self, message):
        self.journal.append(message)

    def en_service(self):
        return self.phase in ("midi", "soir")

    def actifs(self):
        return [m for m in self.menu if m["etat"] == "actif"]

    def etoiles_recette(self, mn):
        return sum(self.etoiles[i] for i in mn["rec"]["ing"])

    def prix_ref_eff(self, mn):
        """Prix de référence national : il monte avec les étoiles premium."""
        return mn["rec"]["prix_ref"] * (1 + PRIX_REF_PAR_ETOILE * self.etoiles_recette(mn))

    def appeal_eff(self, mn, bonus=None):
        if bonus is None:
            bonus = APPEAL_PAR_ETOILE * self.etoiles_recette(mn)
        return min(APPEAL_MAX, mn["appeal"] + bonus)

    def note_recette(self, mn):
        """Note /5 d'après l'attrait caché et les étoiles."""
        return max(1.0, min(5.0, 3.5 + (self.appeal_eff(mn) - 1.0) * 4))

    def cout_recette(self, r, mn):
        return sum(self.prix_achat(r, i) for i in mn["rec"]["ing"])

    def facteur_clients(self, r):
        f = 1.0
        for e in r["concurrence"]:
            f *= e["clients"]
        return f

    def comp_prix(self, r):
        f = 1.0
        for e in r["concurrence"]:
            f *= e["prix"]
        return f

    def prix_local_ref(self, r, mn):
        """Prix de référence dans cette boutique : niveau de prix local, étoiles, concurrence."""
        return self.prix_ref_eff(mn) * r["lieu"]["niveau"] * self.comp_prix(r)

    def ratio_prix(self, r, mn):
        return self.prix_effectif(r, mn) / self.prix_local_ref(r, mn)

    def prix_defaut(self, r, mn):
        return round(self.prix_ref_eff(mn) * r["lieu"]["niveau"], 1)

    def tva_moyenne(self, r):
        f = FISCALITE[r["lieu"]["pays"]]
        e = r["lieu"]["emporter"]
        return e * f["plat_emporter"] + (1 - e) * f["plat_place"]

    def tva_extra(self, f, nom, emporter):
        if nom == "Café" or not emporter:
            return f["plat_emporter"] if emporter else f["plat_place"]
        return f["reduit"]

    def fiche_resto(self, r):
        cle = cle_lieu(r["lieu"])
        if cle not in self.mois_resto:
            self.mois_resto[cle] = {"nom": r["lieu"]["nom"], "ville": r["lieu"]["ville"], "servis": 0, "partis": 0,
                                    "ca_ht": 0.0, "cogs": 0.0, "ttc": 0.0}
        return self.mois_resto[cle]

    def compter(self, champ, montant, pays="France"):
        """Enregistre une charge ou un produit dans le mois et dans l'exercice du pays concerné."""
        self.mois[champ] += montant
        if champ in CHAMPS_FISCAUX:
            if pays not in self.annee:
                self.annee[pays] = {c: 0.0 for c in CHAMPS_FISCAUX}
            self.annee[pays][champ] += montant

    def changer_etoiles(self, nom, delta):
        """Monte ou descend le niveau premium d'un ingrédient ; les prix de vente suivent le prix de référence."""
        nouveau = self.etoiles[nom] + delta
        if nouveau < 0 or nouveau > ETOILES_MAX:
            return
        if delta > 0 and self.rep < ETOILES_REP[nouveau]:
            return
        avant = {mn["rec"]["nom"]: self.prix_ref_eff(mn) for mn in self.menu}
        self.etoiles[nom] = nouveau
        for r in self.restos:
            for mn in self.menu:
                n = mn["rec"]["nom"]
                r["prix"][n] = round(r["prix"][n] * self.prix_ref_eff(mn) / avant[n], 2)
        self.log(f"{nom} : {nouveau} étoile{'s' if nouveau > 1 else ''} "
                 f"(achat x{ETOILES_PRIX[nouveau]:.2f}, note +{NOTE_PAR_ETOILE * nouveau:.1f}).")

    def nb_cuisiniers(self, r):
        return len(r["employes"]) + (1 if r["proprio"] else 0)

    def attrait(self, mn, r):
        return max(0.05, min(1.4, 1 - r["lieu"]["sens"] * (self.ratio_prix(r, mn) - 1)))

    def note(self, r, score):
        """Fait évoluer la réputation de la boutique ; une promotion accélère le mouvement."""
        alpha = REP_ALPHA * (r["promo"]["rep"] if r["promo"] else 1.0)
        r["rep"] += (score - r["rep"]) * alpha
        r["rep"] = max(0.0, min(100.0, r["rep"]))

    def maj_rep_marque(self):
        """Réputation de la marque : moyenne pondérée des boutiques ouvertes depuis au moins 10 jours."""
        if not self.restos:
            return
        anciens = [r for r in self.restos if (self.date - r["ouvert_le"]).days >= 10] or self.restos
        poids = [r["lieu"]["trafic"] * NIVEAU_TRAFIC[r["niveau"] - 1] for r in anciens]
        self.rep = sum(r["rep"] * w for r, w in zip(anciens, poids)) / sum(poids)

    def affluence_prevue(self, r):
        """Clients attendus au prochain service du midi, en % de ce que l'équipe peut servir."""
        date, _ = self.fenetre_commande()
        return 100 * self.demande(r, 0, date, False) / max(1.0, self.nb_cuisiniers(r) * CAPACITE_CONFORT)

    # --- promotions
    def prix_effectif(self, r, mn):
        remise = r["promo"]["remise"] if r["promo"] else 0.0
        return r["prix"][mn["rec"]["nom"]] * (1 - remise)

    def peut_promo(self, r, cle):
        if self.en_service() or r["promo"] or self.fini:
            return False
        if r["promo_cd"] and self.date < r["promo_cd"]:
            return False
        if cle == "ouverture" and (r["offre_ouverture"] or (self.date - r["ouvert_le"]).days > OUVERTURE_JOURS_MAX):
            return False
        return self.caisse >= PROMOS[cle]["cout"]

    def lancer_promo(self, r, cle):
        if not self.peut_promo(r, cle):
            return
        pr = PROMOS[cle]
        self.caisse -= pr["cout"]
        self.compter("autres", pr["cout"], r["lieu"]["pays"])
        r["promo"] = {"cle": cle, "nom": pr["nom"], "jours": pr["jours"], "remise": pr["remise"],
                      "clients": pr["clients"], "rep": pr["rep"]}
        if cle == "ouverture":
            r["offre_ouverture"] = True
        self.log(f"{pr['nom']} à {r['lieu']['nom']} : -{pr['remise']:.0%} pendant {pr['jours']} jours, "
                 f"plus de clients et une réputation qui monte plus vite.")

    def promos_jour(self):
        for r in self.restos:
            if r["promo"]:
                r["promo"]["jours"] -= 1
                if r["promo"]["jours"] <= 0:
                    self.log(f"Fin de l'offre « {r['promo']['nom']} » à {r['lieu']['nom']}.")
                    r["promo"] = None
                    r["promo_cd"] = self.date + datetime.timedelta(days=PROMO_PAUSE)

    # --- comptable et développeur
    def honoraires(self):
        return HONORAIRES_BASE + HONORAIRES_PAR_BOUTIQUE * len(self.restos)

    def embaucher_comptable(self):
        if self.en_service() or self.comptable:
            return
        self.comptable = {"depuis": self.date}
        self.log(f"Comptable engagé : {eur(self.prorata_embauche(self.honoraires()))} ce mois, "
                 f"puis {eur(self.honoraires())}/mois (selon le nombre de boutiques).")

    def licencier_comptable(self):
        if self.en_service() or not self.comptable:
            return
        montant = self.prorata_depart(self.honoraires(), self.comptable["depuis"])
        self.comptable = None
        self.caisse -= montant
        self.compter("honoraires", montant, "France")
        self.log(f"Comptable parti : {eur(montant)} d'honoraires versés pour ce mois.")

    def module_ok(self, cle):
        d = self.modules.get(cle)
        return d is not None and d <= self.date

    def module_attente(self, cle):
        d = self.modules.get(cle)
        return d is not None and d > self.date

    def commander_module(self, cle):
        _, titre, cout, jours = next(m for m in MODULES_DASH if m[0] == cle)
        if self.en_service() or cle in self.modules or self.caisse < cout:
            return
        self.caisse -= cout
        self.compter("autres", cout)
        self.modules[cle] = self.date + datetime.timedelta(days=jours)
        self.log(f"Développeur engagé pour « {titre} » : {eur(cout)}, livraison sous {jours} jours.")

    def resto_sel(self):
        if not self.restos:
            return None
        self.sel = max(0, min(self.sel, len(self.restos) - 1))
        return self.restos[self.sel]

    # --- stocks par boutique (lots avec date de péremption)
    def ajouter_lot(self, r, nom, qte, per, prix, et=0):
        r["stock"][nom].append({"qte": qte, "per": per, "prix": prix, "et": et})
        r["stock"][nom].sort(key=lambda lot: lot["per"])

    def stock_total(self, r, nom):
        return sum(lot["qte"] for lot in r["stock"][nom])

    def en_livraison(self, r, nom):
        return sum(q for n, q, _p, _e in r["livraison"] if n == nom)

    def dlc(self, r, nom):
        return r["stock"][nom][0]["per"] if r["stock"][nom] else None

    def dispo(self, r, mn):
        return all(self.stock_total(r, i) >= 1 for i in mn["rec"]["ing"])

    def prelever(self, r, nom):
        """Utilise une portion du lot le plus proche de sa péremption."""
        for lot in r["stock"][nom]:
            if lot["qte"] >= 1:
                lot["qte"] -= 1
                if lot["qte"] <= 0:
                    r["stock"][nom] = [x for x in r["stock"][nom] if x is not lot]
                return lot
        return None

    def rendre(self, r, nom, lot):
        lot["qte"] += 1
        if not any(x is lot for x in r["stock"][nom]):
            r["stock"][nom].append(lot)
            r["stock"][nom].sort(key=lambda x: x["per"])

    def prix_achat(self, r, nom):
        """Prix d'achat HT d'une portion dans cette boutique (pays, niveau premium)."""
        return self.prix_ing[nom] * r["lieu"]["cout_ing"] * ETOILES_PRIX[self.etoiles.get(nom, 0)]

    def peek_etoiles(self, r, nom):
        for lot in r["stock"][nom]:
            if lot["qte"] >= 1:
                return lot["et"]
        return 0

    def bonus_stock(self, r, mn):
        return APPEAL_PAR_ETOILE * sum(self.peek_etoiles(r, i) for i in mn["rec"]["ing"])

    def remplir_stock_initial(self, r):
        utiles = {i for mn in self.actifs() for i in mn["rec"]["ing"]}
        for nom in utiles:
            qte = 120 if nom == "Pain" else 60
            self.ajouter_lot(r, nom, qte, self.date + datetime.timedelta(days=DUREES[nom]), self.prix_achat(r, nom))
        if self.formule:
            for nom, _p in BOISSONS + DESSERTS:
                qte = 40 if nom in POIDS_BOISSONS else 20
                self.ajouter_lot(r, nom, qte, self.date + datetime.timedelta(days=DUREES[nom]), self.prix_achat(r, nom))

    def bonus_pub(self):
        bonus = sum(p["bonus"] for p in self.pubs)
        if self.commercial:
            bonus *= 1 + BONUS_COMMERCIAL
        return min(BONUS_PUB_MAX, bonus)

    # --- demande et prévisions
    def demande(self, r, idx, date, bruit=True):
        lieu_ = r["lieu"]
        actifs = self.actifs()
        if not actifs:
            return 0.0
        part = lieu_["part_midi"] if idx == 0 else 1 - lieu_["part_midi"]
        appeals = [self.appeal_eff(m) for m in actifs]
        somme_appeal = sum(appeals)
        attr = sum(a * self.attrait(m, r) for a, m in zip(appeals, actifs)) / somme_appeal
        moy_appeal = somme_appeal / len(actifs)
        variete = 1 + 0.05 * (len(actifs) - 1)
        bonus = self.bonus_pub()
        d = (lieu_["trafic"] * NIVEAU_TRAFIC[r["niveau"] - 1] * part * facteur_reputation(r["rep"]) * AFFLUENCE_BASE * (r["promo"]["clients"] if r["promo"] else 1.0) * (1 + bonus)
             * JOUR_MULT[date.weekday()] * variete * attr * math.sqrt(moy_appeal) * self.facteur_clients(r))
        if bruit:
            d *= random.uniform(0.85, 1.15)
        return d

    def besoin_prevu(self, r, date, idxs):
        actifs = self.actifs()
        poids = [self.appeal_eff(m) * self.attrait(m, r) for m in actifs]
        somme = sum(poids) or 1.0
        besoin = {n: 0.0 for n, _ in ARTICLES}
        total = 0.0
        marge = MARGE_STOCK_SAMEDI if date.weekday() == 5 else MARGE_STOCK
        for idx in idxs:
            d = min(self.demande(r, idx, date, False), self.nb_cuisiniers(r) * 85)
            total += d
            for m, w in zip(actifs, poids):
                for i in m["rec"]["ing"]:
                    besoin[i] += d * w / somme * marge
            if self.formule:
                for nom, w in {**POIDS_BOISSONS, **POIDS_DESSERTS}.items():
                    besoin[nom] += d * FORMULE_TAUX * w * marge
        return {n: math.ceil(v) for n, v in besoin.items()}, round(total)

    def fenetre_commande(self):
        """Services couverts par la prochaine livraison : celle du matin, ou celle du lendemain matin."""
        if self.phase == "prep_midi":
            return self.date, [0, 1]
        d = self.date + datetime.timedelta(days=1)
        if d.weekday() == 6:
            d += datetime.timedelta(days=1)
        return d, [0, 1]

    def a_commander(self, r):
        date, idxs = self.fenetre_commande()
        besoin, _ = self.besoin_prevu(r, date, idxs)
        reste_soir = self.besoin_prevu(r, self.date, [1])[0] if self.phase == "prep_soir" else None
        res = {}
        for nom, _p in ARTICLES:
            dispo = self.stock_total(r, nom)
            if reste_soir:
                dispo = max(0, dispo - reste_soir[nom])
            dispo += self.en_livraison(r, nom)
            res[nom] = max(0, math.ceil(besoin[nom] - dispo))
        return res

    # --- salaires et loyers au prorata des jours
    def salaire(self, r):
        return COUT_EMPLOYE * r["lieu"]["salaire"]

    def prorata_embauche(self, montant):
        """Salaire du mois en cours pour quelqu'un embauché aujourd'hui (jours restants / jours du mois)."""
        restant = (premier_mois_suivant(self.date) - self.date).days
        return montant * restant / jours_du_mois(self.date)

    def prorata_depart(self, montant, depuis):
        """Salaire dû pour les jours travaillés ce mois-ci par quelqu'un qui part aujourd'hui."""
        jours = max(1, (self.date - depuis).days)
        return montant * jours / jours_du_mois(self.date)

    def cout_embauche(self, r):
        return self.prorata_embauche(self.salaire(r))

    def cout_licenciement(self, r):
        if not r["employes"]:
            return 0.0
        return self.prorata_depart(self.salaire(r), r["employes"][-1]["depuis"])

    def salaire_gestionnaire(self, r):
        return SALAIRE_GESTIONNAIRE * r["lieu"]["salaire"]

    def cout_pub(self, pub):
        return pub["cout"] * (1 - REMISE_COMMERCIAL if self.commercial else 1)

    def charges_mensuelles(self):
        """Salaires, honoraires et loyers qui seront prélevés à la prochaine échéance (1er du mois)."""
        suivant = premier_mois_suivant(self.date)
        dim = jours_du_mois(self.date)
        salaires = loyers = prets = 0.0
        for r in self.restos:
            for emp in r["employes"]:
                salaires += self.salaire(r) * (suivant - emp["depuis"]).days / dim
            if r["gestionnaire"]:
                salaires += self.salaire_gestionnaire(r) * (suivant - r["gestionnaire"]["depuis"]).days / dim
            loyers += r["loyer"] * (suivant - r["loyer_depuis"]).days / dim
            if r["pret"]:
                prets += r["pret"]["mensualite"]
        if self.commercial:
            salaires += SALAIRE_COMMERCIAL * (suivant - self.commercial["depuis"]).days / dim
        if self.comptable:
            salaires += self.honoraires() * (suivant - self.comptable["depuis"]).days / dim
        return salaires, loyers, prets

    def cout_agrandissement(self, r):
        base = PLACES_PAR_TRAVAUX * 350 * max(1.0, r["lieu"]["loyer"] / 3000)
        return round(base * NIVEAU_TRAVAUX[r["niveau"] - 1], -1)

    def places_max(self, r):
        return sieges_niveau(r["lieu"]["sieges"], r["niveau"])[1]

    def employes_max(self, r):
        return NIVEAU_EMPLOYES[r["niveau"] - 1]

    # --- achat, financement et vente des locaux
    def niveau_a_acheter(self, lieu_):
        return self.locaux_vendus.get(cle_lieu(lieu_), {}).get("niveau", 1)

    def prix_local(self, lieu_):
        return lieu_["cout"] * NIVEAU_FONDS[self.niveau_a_acheter(lieu_) - 1]

    def loyer_niveau(self, lieu_, niveau):
        return lieu_["loyer"] * NIVEAU_LOYER[niveau - 1]

    def apport(self, lieu_):
        return self.prix_local(lieu_) * (1 - PART_EMPRUNTEE)

    def creer_pret(self, capital):
        t = TAUX_PRET / 12
        return {"capital": capital, "mensualite": capital * t / (1 - (1 + t) ** -DUREE_PRET), "mois": DUREE_PRET}

    def dettes_sortie_detail(self, r):
        sal = sum(self.prorata_depart(self.salaire(r), e["depuis"]) for e in r["employes"])
        if r["gestionnaire"]:
            sal += self.prorata_depart(self.salaire_gestionnaire(r), r["gestionnaire"]["depuis"])
        loyer = r["loyer"] * max(0, (self.date - r["loyer_depuis"]).days) / jours_du_mois(self.date)
        return sal, loyer

    def dettes_sortie(self, r):
        """Salaires et loyer des jours écoulés dans le mois, dus quand on quitte le local."""
        return sum(self.dettes_sortie_detail(r))

    def net_vente(self, r):
        """Ce que rapporte la vente du local, après remboursement du prêt et solde des salaires et du loyer."""
        produit = r["prix_fonds"] * REVENTE_FONDS + r["travaux"] * REVENTE_TRAVAUX
        dette = r["pret"]["capital"] if r["pret"] else 0.0
        return produit - dette - self.dettes_sortie(r)

    def peut_vendre(self, r):
        return (not self.en_service() and r["niveau"] < NIVEAU_MAX and r["sieges"] >= self.places_max(r))

    def vendre_local(self, r):
        if not self.peut_vendre(r):
            return
        net = self.net_vente(r)
        self.caisse += net
        sal, loyer = self.dettes_sortie_detail(r)
        self.compter("salaires", sal, r["lieu"]["pays"])
        self.compter("loyers", loyer, r["lieu"]["pays"])
        self.locaux_vendus[cle_lieu(r["lieu"])] = {
            "niveau": r["niveau"] + 1, "stock": r["stock"], "livraison": r["livraison"],
            "employes": len(r["employes"]), "gestionnaire": bool(r["gestionnaire"]), "proprio": r["proprio"], "rep": r["rep"],
        }
        self.restos = [x for x in self.restos if x is not r]
        self.maj_rep_marque()
        self.log(f"Local de {r['lieu']['nom']} vendu (niveau {r['niveau']}) : {eur(net)} nets. "
                 f"Rachetez un local de niveau {r['niveau'] + 1} dans le secteur.")

    # --- actions du joueur
    def ouvrir_resto(self, lieu_, premier=False, niveau=1, prix_fonds=0.0, pret=None, reprise=None):
        depart = sieges_niveau(lieu_["sieges"], niveau)[0]
        nb_employes = reprise["employes"] if reprise else (1 if premier else 2)
        r = {
            "lieu": lieu_, "niveau": niveau, "proprio": reprise["proprio"] if reprise else premier,
            "employes": [{"depuis": self.date} for _ in range(nb_employes)],
            "sieges": depart, "stock": {n: [] for n, _ in ARTICLES}, "livraison": [],
            "loyer": self.loyer_niveau(lieu_, niveau), "loyer_depuis": self.date, "gestionnaire": None,
            "prix_fonds": prix_fonds, "travaux": 0.0, "pret": pret, "concurrence": [], "prix": {},
            "rep": reprise["rep"] * 0.7 if reprise else REP_OUVERTURE, "ouvert_le": self.date,
            "promo": None, "promo_cd": None, "offre_ouverture": False,
            "file": [], "prep": [], "mangent": [], "cuis": [], "taux": [],
            "svc": stats_vides(), "jour": stats_vides(), "veille": None, "aff": 0.0,
        }
        if reprise:
            r["stock"], r["livraison"] = reprise["stock"], reprise["livraison"]
            if reprise["gestionnaire"]:
                r["gestionnaire"] = {"depuis": self.date}
        self.restos.append(r)
        for mn in self.menu:
            r["prix"][mn["rec"]["nom"]] = self.prix_defaut(r, mn)
        if not reprise:
            self.remplir_stock_initial(r)
        return r

    def conditions_ok(self, obj):
        return all(test(self) for _, test in obj["reqs"])

    def peut_ouvrir(self, lieu_, financer=False):
        if self.en_service() or any(r["lieu"] is lieu_ for r in self.restos):
            return False
        if self.niveau_a_acheter(lieu_) == 1 and not self.conditions_ok(lieu_):
            return False
        return self.caisse >= (self.apport(lieu_) if financer else self.prix_local(lieu_))

    def ouvrir(self, lieu_, financer=False):
        """Achète le fonds de commerce (comptant, ou avec un prêt qui couvre 80 % du prix)."""
        if not self.peut_ouvrir(lieu_, financer):
            return
        niveau = self.niveau_a_acheter(lieu_)
        prix = self.prix_local(lieu_)
        payer = self.apport(lieu_) if financer else prix
        self.caisse -= payer
        pret = self.creer_pret(prix - payer) if financer else None
        reprise = self.locaux_vendus.pop(cle_lieu(lieu_), None)
        self.ouvrir_resto(lieu_, False, niveau, prix, pret, reprise)
        if reprise:
            self.log(f"Local de niveau {niveau} acheté à {lieu_['nom']} : équipe et stock repris.")
        else:
            self.log(f"Nouveau restaurant : {lieu_['ville']} - {lieu_['nom']} (2 employés, stock de départ offert).")

    def embaucher(self, r):
        if self.en_service() or len(r["employes"]) >= self.employes_max(r):
            return
        cout = self.cout_embauche(r)
        r["employes"].append({"depuis": self.date})
        self.log(f"Embauche à {r['lieu']['nom']} : {eur(cout)} pour ce mois (à payer le 1er), puis {eur(self.salaire(r))}/mois.")

    def licencier(self, r):
        mini = 0 if r["proprio"] else 1
        if self.en_service() or len(r["employes"]) <= mini:
            return
        montant = self.cout_licenciement(r)
        r["employes"].pop()
        self.caisse -= montant
        self.compter("salaires", montant, r["lieu"]["pays"])
        self.log(f"Licenciement à {r['lieu']['nom']} : {eur(montant)} versés pour les jours travaillés ce mois-ci.")

    def embaucher_commercial(self):
        if self.en_service() or self.commercial:
            return
        self.commercial = {"depuis": self.date}
        self.log(f"Responsable commercial embauché : {eur(self.prorata_embauche(SALAIRE_COMMERCIAL))} ce mois, "
                 f"puis {eur(SALAIRE_COMMERCIAL)}/mois.")

    def licencier_commercial(self):
        if self.en_service() or not self.commercial:
            return
        montant = self.prorata_depart(SALAIRE_COMMERCIAL, self.commercial["depuis"])
        self.commercial = None
        self.caisse -= montant
        self.compter("salaires", montant, "France")
        self.log(f"Responsable commercial parti : {eur(montant)} versés pour les jours travaillés ce mois-ci.")

    def embaucher_gestionnaire(self, r):
        if self.en_service() or r["gestionnaire"]:
            return
        r["gestionnaire"] = {"depuis": self.date}
        self.log(f"Gestionnaire de stock embauché à {r['lieu']['nom']} : "
                 f"{eur(self.prorata_embauche(self.salaire_gestionnaire(r)))} ce mois, puis "
                 f"{eur(self.salaire_gestionnaire(r))}/mois. Il commandera au lancement du service du matin.")

    def licencier_gestionnaire(self, r):
        if self.en_service() or not r["gestionnaire"]:
            return
        montant = self.prorata_depart(self.salaire_gestionnaire(r), r["gestionnaire"]["depuis"])
        r["gestionnaire"] = None
        self.caisse -= montant
        self.compter("salaires", montant, r["lieu"]["pays"])
        self.log(f"Gestionnaire de stock parti de {r['lieu']['nom']} : {eur(montant)} versés.")

    def commandes_automatiques(self):
        """Au lancement du service du matin, les gestionnaires commandent le nécessaire pour leur boutique,
        avec les pubs, la réputation et les prix du moment."""
        total = 0.0
        n = 0
        for r in self.restos:
            if r["gestionnaire"]:
                avant = self.mois["achats_ht"]
                self.commander_necessaire(r)
                total += self.mois["achats_ht"] - avant
                n += 1
        if n:
            self.log(f"Gestionnaires de stock : {n} boutique{'s' if n > 1 else ''} réapprovisionnée"
                     f"{'s' if n > 1 else ''} ({eur(total)}).")

    def agrandir(self, r):
        cout = self.cout_agrandissement(r)
        if self.en_service() or self.caisse < cout or r["sieges"] + PLACES_PAR_TRAVAUX > self.places_max(r):
            return
        self.caisse -= cout
        r["travaux"] += cout
        r["sieges"] += PLACES_PAR_TRAVAUX
        self.log(f"Salle agrandie à {r['lieu']['nom']} : {r['sieges']} places.")

    def commander(self, r, nom, qte):
        """Livraison immédiate le matin avant le premier service, sinon le lendemain matin. Prix HT + TVA."""
        if self.en_service() or self.fini or qte <= 0:
            return
        prix = self.prix_achat(r, nom)
        taux = FISCALITE[r["lieu"]["pays"]]["achat"]
        cout_ht = qte * prix
        cout_ttc = cout_ht * (1 + taux)
        if self.caisse < cout_ttc:
            return
        self.caisse -= cout_ttc
        self.mois["achats_ht"] += cout_ht
        self.mois["tva_deduc"] += cout_ht * taux
        et = self.etoiles.get(nom, 0)
        if self.phase == "prep_midi":
            self.ajouter_lot(r, nom, qte, self.date + datetime.timedelta(days=DUREES[nom]), prix, et)
        else:
            r["livraison"].append((nom, qte, prix, et))

    def commander_necessaire(self, r):
        taux = FISCALITE[r["lieu"]["pays"]]["achat"]
        for nom, qte in self.a_commander(r).items():
            if qte > 0:
                qte = min(qte, int(self.caisse // (self.prix_achat(r, nom) * (1 + taux))))
                if qte > 0:
                    self.commander(r, nom, qte)

    def acheter_pub(self, pub):
        cout = self.cout_pub(pub)
        if self.caisse < cout:
            return
        self.caisse -= cout
        self.compter("autres", cout)
        self.pubs_lancees += 1
        for p in self.pubs:
            if p["nom"] == pub["nom"]:
                p["jours"] = pub["jours"]
                break
        else:
            self.pubs.append(dict(pub))
        self.log(f"Campagne lancée : {pub['nom']}.")

    def developper(self, mn):
        rec = mn["rec"]
        if mn["etat"] == "verrouille" and self.caisse >= rec["dev"] and self.conditions_ok(rec):
            self.caisse -= rec["dev"]
            self.compter("autres", rec["dev"])
            mn["etat"] = "actif"
            self.log(f"Nouvelle recette au menu : {rec['nom']}. À toi de voir si elle plaît !")

    def basculer(self, mn):
        if mn["etat"] == "actif" and nb_actifs(self) > 1:
            mn["etat"] = "retire"
        elif mn["etat"] == "retire":
            mn["etat"] = "actif"

    def changer_prix(self, r, mn, delta):
        n = mn["rec"]["nom"]
        r["prix"][n] = round(max(1.0, min(60.0, r["prix"][n] + delta)), 2)

    def prix_conseilles(self, r):
        for mn in self.menu:
            r["prix"][mn["rec"]["nom"]] = self.prix_defaut(r, mn)

    def copier_prix(self, source):
        """Applique à toutes les boutiques les prix de `source`, ajustés au niveau de prix local."""
        for r in self.restos:
            if r is source:
                continue
            for mn in self.menu:
                n = mn["rec"]["nom"]
                r["prix"][n] = round(source["prix"][n] / source["lieu"]["niveau"] * r["lieu"]["niveau"], 2)

    def basculer_formule(self):
        self.formule = not self.formule

    def regler_vitesse(self, v):
        self.vitesse = v

    def basculer_pause(self):
        if self.en_service():
            self.pause = not self.pause

    def action_principale(self):
        if self.fini:
            return
        if self.phase == "prep_midi":
            self.commandes_automatiques()
            self.lancer_service(0)
        elif self.phase == "prep_soir":
            self.lancer_service(1)
        elif self.phase in ("bilan", "ferme"):
            self.nouveau_jour()

    def espace(self):
        if self.en_service():
            self.basculer_pause()
        else:
            self.action_principale()

    # --- simulation
    def lancer_service(self, idx):
        self.service_idx = idx
        self.phase = NOMS_SERVICES[idx]
        self.minute = DEBUTS[idx]
        self.pause = False
        self.ruptures.clear()
        for r in self.restos:
            r["file"], r["prep"], r["mangent"] = [], [], []
            r["cuis"] = [0.0] * self.nb_cuisiniers(r)
            r["svc"] = stats_vides()
            d = self.demande(r, idx, self.date)
            r["aff"] = d / max(1.0, self.nb_cuisiniers(r) * CAPACITE_CONFORT)
            r["taux"] = [d * p for p in PROFILS[idx]]
        self.log(f"Ouverture du service du {NOMS_SERVICES[idx]}.")

    def tick(self):
        """Fait avancer le jeu d'une minute."""
        m = self.minute
        for r in self.restos:
            self.tick_resto(r, m)
        self.minute += 1
        if self.minute >= DEBUTS[self.service_idx] + DUREE_SERVICE:
            self.fin_service()

    def tick_resto(self, r, m):
        t = m - DEBUTS[self.service_idx]
        lam = r["taux"][t] if 0 <= t < len(r["taux"]) else 0
        for _ in range(poisson(lam)):
            self.arrivee(r, m)

        restants = []
        for c in r["file"]:
            if m - c["arrive"] >= c["patience"]:
                self.perdu(r, c, "att")
            else:
                restants.append(c)
        r["file"] = restants

        for i in range(len(r["cuis"])):
            if r["cuis"][i] <= m and r["file"]:
                c = r["file"].pop(0)
                duree = random.uniform(1.0, 2.2)
                r["cuis"][i] = m + duree
                c["pret"] = m + duree
                r["prep"].append(c)

        encore = []
        for c in r["prep"]:
            if c["pret"] <= m:
                self.servi(r, c, m)
            else:
                encore.append(c)
        r["prep"] = encore
        r["mangent"] = [f for f in r["mangent"] if f > m]

    def sieges_occupes(self, r):
        return len(r["mangent"]) + sum(1 for c in r["file"] + r["prep"] if not c["emporter"])

    def arrivee(self, r, m):
        lieu_ = r["lieu"]
        actifs = self.actifs()
        for mn in actifs:
            nom = mn["rec"]["nom"]
            cle = (lieu_["nom"], nom)
            if not self.dispo(r, mn) and cle not in self.ruptures:
                self.ruptures.add(cle)
                self.log(f"Rupture de stock : {nom} ! ({lieu_['nom']})")

        emporter = random.random() < lieu_["emporter"]
        if not emporter and self.sieges_occupes(r) >= r["sieges"]:
            if random.random() < 0.5:
                emporter = True
            else:
                self.perdu(r, None, "salle")
                return

        dispo = [mn for mn in actifs if self.dispo(r, mn)]
        if not dispo:
            self.perdu(r, None, "rup")
            return
        poids = [self.appeal_eff(mn, self.bonus_stock(r, mn)) * self.attrait(mn, r) for mn in dispo]
        mn = random.choices(dispo, weights=poids)[0]
        lots = [(i, self.prelever(r, i)) for i in mn["rec"]["ing"]]
        bonus = APPEAL_PAR_ETOILE * sum(lot["et"] for _, lot in lots)
        extras = []
        if self.formule and random.random() < FORMULE_TAUX:
            for poids_extras in (POIDS_BOISSONS, POIDS_DESSERTS):
                en_stock = [(n, w) for n, w in poids_extras.items() if self.stock_total(r, n) >= 1]
                if en_stock:
                    n = random.choices([x[0] for x in en_stock], weights=[x[1] for x in en_stock])[0]
                    lots.append((n, self.prelever(r, n)))
                    extras.append(n)
        patience = random.uniform(6, 11) if emporter else random.uniform(9, 15)
        r["file"].append({"arrive": m, "patience": patience, "emporter": emporter, "mn": mn, "lots": lots,
                          "bonus": bonus, "extras": extras})

    def perdu(self, r, c, motif):
        r["svc"][motif] += 1
        self.mois[motif] += 1
        self.fiche_resto(r)["partis"] += 1
        if c is not None:  # la commande n'a pas été préparée : on remet les produits dans leur lot
            for nom, lot in c["lots"]:
                self.rendre(r, nom, lot)
        self.note(r, {"att": 10, "rup": 15, "salle": 40}[motif])

    def servi(self, r, c, m):
        mn = c["mn"]
        nom = mn["rec"]["nom"]
        pays = r["lieu"]["pays"]
        f = FISCALITE[pays]
        ratio = self.ratio_prix(r, mn)
        attente = m - c["arrive"]
        appeal = self.appeal_eff(mn, c["bonus"])
        score = 55 + 35 * (appeal - 0.7) / 0.6 + 10 * (1 - attente / c["patience"])
        score -= max(0.0, ratio - 1.05) * 80
        self.note(r, max(0.0, min(100.0, score)))

        prix = self.prix_effectif(r, mn)
        ht_sand = prix / (1 + (f["plat_emporter"] if c["emporter"] else f["plat_place"]))
        ttc_extras = ht_extras = 0.0
        for n in c["extras"]:
            p = PRIX_VENTE_EXTRAS[n] * (1 - FORMULE_REMISE)
            ttc_extras += p
            ht_extras += p / (1 + self.tva_extra(f, n, c["emporter"]))
        ttc = prix + ttc_extras
        ht = ht_sand + ht_extras
        cogs_sand = sum(lot["prix"] for n, lot in c["lots"] if n in ING_SET)
        cogs_extras = sum(lot["prix"] for n, lot in c["lots"] if n not in ING_SET)

        self.caisse += ttc
        mo = self.mois
        mo["ca_ttc"] += ttc
        mo["tva_coll"] += ttc - ht
        mo["servis"] += 1
        mo["extras_ht"] += ht_extras
        self.compter("ca_ht", ht, pays)
        self.compter("cogs", cogs_sand + cogs_extras, pays)
        if c["extras"]:
            mo["formules"] += 1
        stat = self.mois_sand.setdefault(nom, {"ventes": 0, "ca_ht": 0.0, "cogs": 0.0})
        stat["ventes"] += 1
        stat["ca_ht"] += ht_sand
        stat["cogs"] += cogs_sand
        for n in c["extras"]:
            self.mois_extras[n] = self.mois_extras.get(n, 0) + 1
        fiche = self.fiche_resto(r)
        fiche["servis"] += 1
        fiche["ca_ht"] += ht
        fiche["cogs"] += cogs_sand + cogs_extras
        fiche["ttc"] += ttc
        r["svc"]["servis"] += 1
        r["svc"]["ca"] += ttc
        r["svc"]["ht"] += ht
        if c["extras"]:
            r["svc"]["formules"] += 1
        mn["ventes"] += 1
        mn["ventes_jour"] += 1
        if not c["emporter"]:
            r["mangent"].append(m + random.uniform(12, 25))

    def fin_service(self):
        m = self.minute
        for r in self.restos:
            for c in r["file"]:
                self.perdu(r, c, "att")
            r["file"] = []
            for c in r["prep"]:
                self.servi(r, c, m)
            r["prep"] = []
            for k, v in r["svc"].items():
                r["jour"][k] += v
        ca = sum(r["svc"]["ca"] for r in self.restos)
        self.maj_rep_marque()
        self.log(f"Fin du service du {NOMS_SERVICES[self.service_idx]} : chiffre d'affaires {eur(ca)}.")
        if self.service_idx == 0:
            self.phase = "prep_soir"
            self.minute = 16 * 60
            self.onglet = "courses"
        else:
            self.phase = "bilan"
            self.minute = 21 * 60 + 30
            self.onglet = "bilan"

    def nouveau_jour(self):
        for r in self.restos:
            r["veille"] = dict(r["jour"])
            r["jour"] = stats_vides()
        for mn in self.menu:
            mn["ventes_jour"] = 0
        ancien = self.date
        self.date += datetime.timedelta(days=1)
        if self.date.month != ancien.month:
            self.fin_de_mois(ancien, self.date)
        self.maj_prix()
        self.perimer()
        self.promos_jour()
        self.evenements_concurrents()
        self.maj_rep_marque()
        if self.date.weekday() != 6:
            self.livrer()
        for p in self.pubs:
            p["jours"] -= 1
        for p in [p for p in self.pubs if p["jours"] <= 0]:
            self.log(f"La campagne « {p['nom']} » est terminée.")
        self.pubs = [p for p in self.pubs if p["jours"] > 0]
        self.onglet = "courses"
        self.minute = 10 * 60
        self.phase = "ferme" if self.date.weekday() == 6 else "prep_midi"
        if self.caisse < -3000 * max(1, len(self.restos)):
            self.fini = True
            self.log("Faillite ! Les dettes sont trop lourdes.")
        elif AUTOSAVE:
            try:
                ecrire_sauvegarde(self, "auto")
            except Exception:
                pass

    def evenements_concurrents(self):
        """Chaque jour, des concurrents peuvent s'installer, faire des promotions ou fermer près d'une boutique."""
        for r in self.restos:
            for e in r["concurrence"]:
                e["jours"] -= 1
            finis = [e for e in r["concurrence"] if e["jours"] <= 0]
            r["concurrence"] = [e for e in r["concurrence"] if e["jours"] > 0]
            if any(e["type"] == "ouverture" for e in finis):
                self.log(f"Le concurrent près de {r['lieu']['nom']} s'est fait sa place : les clients reviennent.")
            tirage = random.random()
            cumul = 0.0
            for type_, proba, jours, clients, prix, texte in EVENEMENTS:
                cumul += proba
                if tirage < cumul:
                    if len(r["concurrence"]) < 3 and not any(e["type"] == type_ for e in r["concurrence"]):
                        r["concurrence"].append({"type": type_, "jours": jours, "clients": clients, "prix": prix})
                        self.log(f"{texte.format(nom=r['lieu']['nom'])} : clients {clients - 1:+.0%}, "
                                 f"prix de référence {prix - 1:+.0%} pendant {jours} jours.".replace("+-", "-"))
                    break

    def maj_prix(self):
        for nom, base in ARTICLES:
            self.prix_veille[nom] = self.prix_ing[nom]
            p = self.prix_ing[nom] * (1 + random.uniform(-0.02, 0.02))
            self.prix_ing[nom] = max(base * 0.75, min(base * 1.35, p))

    def perimer(self):
        """Les lots dont la date est dépassée sont jetés."""
        portions = 0
        valeur = 0.0
        for r in self.restos:
            perdu_r = 0.0
            for nom in r["stock"]:
                gardes = []
                for lot in r["stock"][nom]:
                    if lot["per"] < self.date:
                        portions += lot["qte"]
                        perdu_r += lot["qte"] * lot["prix"]
                    else:
                        gardes.append(lot)
                r["stock"][nom] = gardes
            if perdu_r:
                self.compter("pertes", perdu_r, r["lieu"]["pays"])
                valeur += perdu_r
        if portions:
            self.log(f"Péremption : {int(portions)} portions jetées ({eur(valeur)}).")

    def livrer(self):
        """Livraison du matin : les lots arrivent frais, avec leur propre date de péremption."""
        for r in self.restos:
            for nom, qte, prix, et in r["livraison"]:
                self.ajouter_lot(r, nom, qte, self.date + datetime.timedelta(days=DUREES[nom]), prix, et)
            r["livraison"] = []

    def fin_de_mois(self, ancien, nouveau):
        dim = jours_du_mois(ancien)
        salaires = loyers = prets = locales = 0.0
        for r in self.restos:
            pays = r["lieu"]["pays"]
            sal = 0.0
            for emp in r["employes"]:
                sal += self.salaire(r) * (nouveau - emp["depuis"]).days / dim
                emp["depuis"] = nouveau
            if r["gestionnaire"]:
                sal += self.salaire_gestionnaire(r) * (nouveau - r["gestionnaire"]["depuis"]).days / dim
                r["gestionnaire"]["depuis"] = nouveau
            loyer = r["loyer"] * (nouveau - r["loyer_depuis"]).days / dim
            r["loyer_depuis"] = nouveau
            interet = 0.0
            if r["pret"]:
                p = r["pret"]
                interet = p["capital"] * TAUX_PRET / 12
                p["capital"] -= p["mensualite"] - interet
                p["mois"] -= 1
                prets += p["mensualite"]
                if p["mois"] <= 0 or p["capital"] <= 1:
                    r["pret"] = None
            self.compter("salaires", sal, pays)
            self.compter("loyers", loyer, pays)
            self.compter("interets", interet, pays)
            salaires += sal
            loyers += loyer
            if ancien.month == 12:          # taxes locales, payées une fois par an
                taxe = r["loyer"] * 12 * FISCALITE[pays]["locales"]
                self.compter("locales", taxe, pays)
                locales += taxe
        if self.commercial:
            sal = SALAIRE_COMMERCIAL * (nouveau - self.commercial["depuis"]).days / dim
            self.commercial["depuis"] = nouveau
            self.compter("salaires", sal, "France")
            salaires += sal
        if self.comptable:
            hon = self.honoraires() * (nouveau - self.comptable["depuis"]).days / dim
            self.comptable["depuis"] = nouveau
            self.compter("honoraires", hon, "France")
            salaires += hon
        self.mois["prets"] += prets

        # TVA : collectée sur les ventes moins déductible sur les achats, reversée chaque mois
        tva_nette = self.mois["tva_coll"] - self.mois["tva_deduc"] - self.tva_credit
        if tva_nette > 0:
            tva_payee = tva_nette
            self.tva_credit = 0.0
        else:
            tva_payee = 0.0
            self.tva_credit = -tva_nette

        # Impôt sur les bénéfices : acompte mensuel d'après le résultat de l'exercice, régularisé en décembre
        ca_groupe = sum(a["ca_ht"] for a in self.annee.values())
        impots = 0.0
        for pays, a in self.annee.items():
            profit = (a["ca_ht"] - a["cogs"] - a["pertes"] - a["salaires"] - a["loyers"] - a["interets"]
                      - a["autres"] - a["locales"] - a["honoraires"])
            du = impot_societes(pays, profit, ca_groupe)
            paye = self.is_paye.get(pays, 0.0)
            a_payer = du - paye
            if ancien.month != 12:
                a_payer = max(0.0, a_payer)
            self.is_paye[pays] = paye + a_payer
            impots += a_payer

        # sans comptable : déclarations en retard ou erronées, majoration de la TVA et de l'impôt
        penalites = 0.0 if self.comptable else PENALITE_SANS_COMPTABLE * (tva_payee + max(0.0, impots))
        self.mois["penalites"] += penalites
        self.caisse -= salaires + loyers + prets + locales + tva_payee + impots + penalites
        m = self.mois
        marge_brute = m["ca_ht"] - m["cogs"]
        avant_is = (marge_brute - m["pertes"] - m["salaires"] - m["loyers"] - m["interets"] - m["autres"]
                    - m["locales"] - m["honoraires"])
        self.historique.append({
            "label": f"{MOIS_COURTS[ancien.month - 1]} {str(ancien.year)[2:]}",
            "mois": dict(m), "sand": {k: dict(v) for k, v in self.mois_sand.items()},
            "restos": {k: dict(v) for k, v in self.mois_resto.items()}, "extras": dict(self.mois_extras),
            "tva_payee": tva_payee, "is": impots, "avant_is": avant_is, "net": avant_is - impots - penalites,
            "penalites": penalites, "comptable": bool(self.comptable),
            "rep": self.rep, "caisse": self.caisse, "nb_restos": len(self.restos),
        })
        self.historique = self.historique[-36:]
        self.mois = acc_vide()
        self.mois_sand = {}
        self.mois_resto = {}
        self.mois_extras = {}
        if nouveau.month == 1:
            self.annee = {}
            self.is_paye = {}
        self.log(f"Fin de mois : salaires {eur(salaires)}, loyers {eur(loyers)}"
                 f"{', prêts ' + eur(prets) if prets else ''}, TVA {eur(tva_payee)}, impôts {eur(impots)}.")


# ================================================================ AFFICHAGE ART DECO

jeu = None
boutons = []
screen = clock = FOND_SURF = None

CHEMIN_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sandwichs")

# ---------------------------------------------------------------- PALETTE ART DECO

NUIT = (11, 16, 30)
PANNEAU_FOND = (15, 22, 41)
CARTE_FOND = (24, 34, 60)
OR = (212, 175, 55)
OR_CLAIR = (246, 220, 130)
OR_SOMBRE = (128, 98, 34)
CREME = (244, 236, 216)
CREME_SOMBRE = (178, 170, 146)
EMERAUDE = (14, 92, 78)
EMERAUDE_CLAIR = (26, 128, 106)
BORDEAUX = (118, 28, 42)
BORDEAUX_CLAIR = (156, 42, 58)
VERT = (96, 206, 150)
ROUGE = (226, 96, 84)

# Polices : Copperplate / Futura si elles existent sur le Mac, sinon police par défaut
FAMILLES = {
    "titre": ("copperplate,copperplategothic,didot,baskerville,georgia", False),
    "corps": ("futura,avenirnext,avenir,helveticaneue,arial", False),
    "gras": ("futura,avenirnext,avenir,helveticaneue,arial", True),
}
T_MINI = ("corps", 15)
T_PETIT = ("corps", 17)
T_NORMAL = ("corps", 19)
T_GRAS = ("gras", 18)
T_TITRE = ("titre", 22)
T_TITRE_G = ("titre", 26)
T_GRAND = ("titre", 40)

_polices = {}
_cache_txt = {}
_images = {}
_maitres = {}


def police(cle):
    if cle not in _polices:
        famille, taille = cle
        noms, gras = FAMILLES[famille]
        chemin = None
        try:
            chemin = pygame.font.match_font(noms, bold=gras)
        except Exception:
            chemin = None
        try:
            _polices[cle] = pygame.font.Font(chemin, taille)
        except Exception:
            _polices[cle] = pygame.font.Font(None, taille)
    return _polices[cle]


def rendu(txt, cle, couleur):
    k = (txt, cle, couleur)
    s = _cache_txt.get(k)
    if s is None:
        if len(_cache_txt) > 3000:
            _cache_txt.clear()
        s = police(cle).render(txt, True, couleur)
        _cache_txt[k] = s
    return s


def texte(txt, pos, cle=T_PETIT, couleur=CREME, ancre="g", max_w=None):
    """Ancres : g = gauche, c = centré (x et y), cx = centré en x, d = aligné à droite."""
    fam, taille = cle
    if max_w:
        while taille > 11 and police((fam, taille)).size(txt)[0] > max_w:
            taille -= 1
        cle = (fam, taille)
    surf = rendu(txt, cle, couleur)
    x, y = pos
    w, h = surf.get_width(), surf.get_height()
    if ancre == "c":
        x, y = x - w // 2, y - h // 2
    elif ancre == "cx":
        x -= w // 2
    elif ancre == "d":
        x -= w
    screen.blit(surf, (int(x), int(y)))
    return w


# ---------------------------------------------------------------- OUTILS DE DESSIN

def pans(rect, c):
    x, y, w, h = [int(v) for v in rect]
    c = max(1, min(c, w // 2, h // 2))
    return [(x + c, y), (x + w - c, y), (x + w, y + c), (x + w, y + h - c),
            (x + w - c, y + h), (x + c, y + h), (x, y + h - c), (x, y + c)]


def poly_alpha(cible, couleur, points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x0, y0 = int(min(xs)), int(min(ys))
    w, h = int(max(xs)) - x0 + 2, int(max(ys)) - y0 + 2
    tmp = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(tmp, couleur, [(px - x0, py - y0) for px, py in points])
    cible.blit(tmp, (x0, y0))


def losange(cx, cy, r, couleur):
    pygame.draw.polygon(screen, couleur, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)])


def cadre(rect, fond, bord=OR, c=10, ep=2, interieur=True):
    pts = pans(rect, c)
    pygame.draw.polygon(screen, fond, pts)
    pygame.draw.polygon(screen, bord, pts, ep)
    if interieur:
        x, y, w, h = rect
        pygame.draw.polygon(screen, OR_SOMBRE, pans((x + 5, y + 5, w - 10, h - 10), max(2, c - 4)), 1)


def carte(rect):
    cadre(rect, CARTE_FOND, OR_SOMBRE, 8, 1, False)


def eventail(cx, cy, r, rayons=9, clair=OR, sombre=OR_SOMBRE, centre=NUIT):
    pts = []
    for k in range(rayons + 1):
        a = math.pi * k / rayons
        pts.append((cx + r * math.cos(a), cy - r * math.sin(a)))
    for k in range(rayons):
        pygame.draw.polygon(screen, clair if k % 2 == 0 else sombre, [(cx, cy), pts[k], pts[k + 1]])
    pygame.draw.arc(screen, clair, (cx - r, cy - r, 2 * r, 2 * r), 0, math.pi, 2)
    pygame.draw.line(screen, clair, (cx - r, cy), (cx + r, cy), 2)
    rr = max(3, int(r * 0.34))
    pygame.draw.circle(screen, centre, (cx, cy), rr)
    pygame.draw.arc(screen, clair, (cx - rr, cy - rr, 2 * rr, 2 * rr), 0, math.pi, 2)


def etoile(cx, cy, r, couleur):
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    pygame.draw.polygon(screen, couleur, pts)


def eur_court(x):
    a = abs(x)
    if a >= 1_000_000:
        return f"{x / 1_000_000:.1f} M€".replace(".", ",")
    if a >= 10_000:
        return f"{x / 1000:.0f} k€"
    if a >= 1000:
        return f"{x / 1000:.1f} k€".replace(".", ",")
    return f"{x:.0f} €"


def carte_kpi(x, y, w, h, titre, valeur, couleur=CREME, sous_titre=None):
    carte((x, y, w, h))
    texte(titre.upper(), (x + 10, y + 5), T_MINI, OR, max_w=w - 20)
    texte(valeur, (x + 10, y + 20), T_TITRE_G, couleur, max_w=w - 20)
    if sous_titre:
        texte(sous_titre, (x + 10, y + h - 17), T_MINI, CREME_SOMBRE, max_w=w - 20)


def graphique(rect, titre, labels, barres, ligne=None, nom_barres="", nom_ligne=""):
    x, y, w, h = rect
    cadre(rect, CARTE_FOND, OR_SOMBRE, 8, 1, False)
    texte(titre, (x + 12, y + 8), T_PETIT, OR_CLAIR, max_w=w - 24)
    if not labels:
        texte("Les courbes apparaîtront après le premier mois complet.", (x + w // 2, y + h // 2), T_PETIT,
              CREME_SOMBRE, "c", max_w=w - 30)
        return
    zx, zy, zw, zh = x + 62, y + 40, w - 80, h - 92
    valeurs = list(barres) + list(ligne or [])
    vmax, vmin = max(max(valeurs), 0.0), min(min(valeurs), 0.0)
    if vmax == vmin:
        vmax = vmin + 1.0

    def ypix(v):
        return zy + zh * (vmax - v) / (vmax - vmin)

    for k in range(5):
        v = vmin + (vmax - vmin) * k / 4
        yy = int(ypix(v))
        pygame.draw.line(screen, (44, 54, 84), (zx, yy), (zx + zw, yy), 1)
        texte(eur_court(v), (zx - 6, yy - 8), T_MINI, CREME_SOMBRE, "d")
    pygame.draw.line(screen, OR_SOMBRE, (zx, int(ypix(0))), (zx + zw, int(ypix(0))), 2)
    n = len(labels)
    pas = zw / n
    bw = max(6, min(36, pas * 0.6))
    centres = []
    for i, v in enumerate(barres):
        cx = zx + pas * i + pas / 2
        centres.append(cx)
        y0, y1 = int(ypix(max(v, 0))), int(ypix(min(v, 0)))
        pygame.draw.rect(screen, OR if v >= 0 else ROUGE, (int(cx - bw / 2), y0, int(bw), max(1, y1 - y0)))
        texte(labels[i], (cx, zy + zh + 8), T_MINI, CREME_SOMBRE, "cx", max_w=pas)
    if ligne:
        pts = [(int(centres[i]), int(ypix(v))) for i, v in enumerate(ligne)]
        for a, b in zip(pts, pts[1:]):
            pygame.draw.line(screen, VERT, a, b, 3)
        for pt in pts:
            pygame.draw.circle(screen, VERT, pt, 4)
    lx = x + 12
    if nom_barres:
        pygame.draw.rect(screen, OR, (lx, y + h - 20, 12, 10))
        lx += 18 + texte(nom_barres, (lx + 18, y + h - 23), T_MINI, CREME_SOMBRE)
    if nom_ligne and ligne:
        pygame.draw.circle(screen, VERT, (lx + 24, y + h - 15), 4)
        texte(nom_ligne, (lx + 34, y + h - 23), T_MINI, CREME_SOMBRE)


def jauge(x, y, w, h, valeur):
    pygame.draw.polygon(screen, (22, 30, 54), pans((x, y, w, h), 4))
    largeur = int((w - 4) * max(0.0, min(100.0, valeur)) / 100)
    if largeur > 8:
        pygame.draw.polygon(screen, OR, pans((x + 2, y + 2, largeur, h - 4), 3))
    pygame.draw.polygon(screen, OR_SOMBRE, pans((x, y, w, h), 4), 1)


def panneau(rect, titre=None, c=14):
    cadre(rect, PANNEAU_FOND, OR, c)
    if titre:
        x, y, w, h = rect
        cx, ty = x + w // 2, y + 24
        lw = texte(titre.upper(), (cx, ty), T_TITRE_G, OR_CLAIR, "c")
        for sens in (-1, 1):
            debut = cx + sens * (lw // 2 + 26)
            fin = x + 34 if sens < 0 else x + w - 34
            pygame.draw.line(screen, OR, (debut, ty), (fin, ty), 1)
            pygame.draw.line(screen, OR_SOMBRE, (debut, ty + 4), (fin, ty + 4), 1)
            losange(cx + sens * (lw // 2 + 16), ty, 4, OR)


STYLES = {
    "normal": ((14, 92, 78), (26, 128, 106), OR, CREME),
    "principal": ((118, 28, 42), (160, 44, 60), OR_CLAIR, CREME),
    "onglet": ((22, 30, 54), (36, 48, 84), OR_SOMBRE, CREME_SOMBRE),
    "onglet_actif": ((196, 158, 52), (226, 190, 76), OR_CLAIR, NUIT),
}


def bouton(rect, label, actif, action, style="normal", cle=T_PETIT):
    rect = pygame.Rect(rect)
    fond, fond_h, bord, txt = STYLES[style]
    survol = actif and rect.collidepoint(pygame.mouse.get_pos())
    if not actif:
        fond, bord, txt = (28, 34, 52), (86, 74, 46), (118, 116, 126)
    elif survol:
        fond, bord = fond_h, OR_CLAIR
    pts = pans(rect, 6)
    pygame.draw.polygon(screen, fond, pts)
    if actif and rect.h >= 20:
        poly_alpha(screen, (255, 255, 255, 28), pans((rect.x + 3, rect.y + 3, rect.w - 6, rect.h // 2 - 3), 3))
    pygame.draw.polygon(screen, bord, pts, 2)
    texte(label, rect.center, cle, txt, "c", max_w=rect.w - 14)
    boutons.append((rect, action, actif))


def silhouette(cx, base_y, couleur, t=1.0):
    pygame.draw.circle(screen, couleur, (int(cx), int(base_y - 15 * t)), max(2, int(3.6 * t)))
    pygame.draw.polygon(screen, couleur, [(cx - 5 * t, base_y), (cx - 4 * t, base_y - 10 * t),
                                          (cx + 4 * t, base_y - 10 * t), (cx + 5 * t, base_y)])


def cuisinier(cx, base_y, actif):
    corps = OR_CLAIR if actif else (104, 110, 130)
    pygame.draw.polygon(screen, corps, [(cx - 5, base_y), (cx - 4, base_y - 10), (cx + 4, base_y - 10), (cx + 5, base_y)])
    pygame.draw.circle(screen, (232, 196, 160), (cx, base_y - 14), 3)
    pygame.draw.rect(screen, CREME, (cx - 3, base_y - 19, 6, 3))
    pygame.draw.circle(screen, CREME, (cx, base_y - 20), 4)


def devanture(x, y, w, h):
    pygame.draw.rect(screen, (30, 42, 72), (x, y + h // 3, w, h - h // 3))
    n = 6
    lw = w / n
    for k in range(n):
        col = EMERAUDE_CLAIR if k % 2 == 0 else CREME
        x0 = int(x + k * lw)
        pygame.draw.rect(screen, col, (x0, y, int(lw) + 1, h // 3))
        pygame.draw.circle(screen, col, (int(x0 + lw / 2), y + h // 3), max(2, int(lw / 2)))
    pygame.draw.rect(screen, NUIT, (x + w // 2 - 6, y + h // 2 + 4, 12, h // 2 - 4))
    pygame.draw.rect(screen, OR, (x + w // 2 - 6, y + h // 2 + 4, 12, h // 2 - 4), 1)
    pygame.draw.rect(screen, (74, 104, 146), (x + 5, y + h // 2 + 6, w // 2 - 15, h // 3 - 2))
    pygame.draw.rect(screen, (74, 104, 146), (x + w // 2 + 10, y + h // 2 + 6, w // 2 - 15, h // 3 - 2))
    pygame.draw.rect(screen, OR, (x, y + h // 3, w, h - h // 3), 1)


def construire_fond():
    fond = pygame.Surface((LARGEUR, HAUTEUR))
    for y in range(HAUTEUR):
        t = y / HAUTEUR
        pygame.draw.line(fond, (int(9 + 8 * t), int(13 + 11 * t), int(26 + 18 * t)), (0, y), (LARGEUR, y))
    r = 30
    pas_y = 15
    for ligne in range(-1, HAUTEUR // pas_y + 3):
        y = ligne * pas_y
        t = max(0.0, min(1.0, y / HAUTEUR))
        base = (int(9 + 8 * t), int(13 + 11 * t), int(26 + 18 * t))
        decal = 0 if ligne % 2 == 0 else r
        for x0 in range(-2 * r, LARGEUR + 2 * r, 2 * r):
            cx = x0 + decal
            for k, rr in enumerate((r, int(r * 0.76), int(r * 0.52), int(r * 0.28))):
                ton = (base[0] + (7 if k % 2 == 0 else 3), base[1] + (9 if k % 2 == 0 else 4),
                       base[2] + (15 if k % 2 == 0 else 7))
                pygame.draw.circle(fond, ton, (cx, y), rr)
                pygame.draw.circle(fond, (base[0] + 14, base[1] + 18, base[2] + 28), (cx, y), rr, 1)
    return fond


# ---------------------------------------------------------------- SANDWICHS DESSINES PAR LE CODE

S = 3  # suréchantillonnage : on dessine en grand puis on réduit pour lisser


class Toile:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.surf = pygame.Surface((w * S, h * S), pygame.SRCALPHA)
        self.surf.fill((150, 110, 60, 0))

    def _p(self, pts):
        return [(int(x * S), int(y * S)) for x, y in pts]

    def poly(self, pts, col, larg=0):
        pygame.draw.polygon(self.surf, col, self._p(pts), int(larg * S) if larg else 0)

    def ellipse(self, x, y, w, h, col, larg=0):
        pygame.draw.ellipse(self.surf, col, (int(x * S), int(y * S), max(2, int(w * S)), max(2, int(h * S))),
                            int(larg * S) if larg else 0)

    def ligne(self, a, b, col, larg=1.0):
        pygame.draw.line(self.surf, col, (int(a[0] * S), int(a[1] * S)), (int(b[0] * S), int(b[1] * S)),
                         max(1, int(larg * S)))

    def polyligne(self, pts, col, larg=1.0):
        P = self._p(pts)
        for i in range(len(P) - 1):
            pygame.draw.line(self.surf, col, P[i], P[i + 1], max(1, int(larg * S)))

    def voile(self, pts, col):
        poly_alpha(self.surf, col, self._p(pts))

    def remplir(self, pts, haut, bas, taches=(), graine=1):
        """Remplit un polygone avec un dégradé vertical et des petites taches de texture."""
        P = self._p(pts)
        x0, y0 = min(p[0] for p in P), min(p[1] for p in P)
        w, h = max(p[0] for p in P) - x0 + 2, max(p[1] for p in P) - y0 + 2
        g = pygame.Surface((w, h), pygame.SRCALPHA)
        for yy in range(h):
            t = yy / max(1, h - 1)
            c = (int(haut[0] + (bas[0] - haut[0]) * t), int(haut[1] + (bas[1] - haut[1]) * t),
                 int(haut[2] + (bas[2] - haut[2]) * t), 255)
            pygame.draw.line(g, c, (0, yy), (w, yy))
        rnd = random.Random(graine)
        for (rx, ry, rw, rh, n, couleurs, rmin, rmax) in taches:
            for _ in range(n):
                px = (rx + rnd.random() * rw) * S - x0
                py = (ry + rnd.random() * rh) * S - y0
                r = (rmin + rnd.random() * (rmax - rmin)) * S
                pygame.draw.ellipse(g, rnd.choice(couleurs), (int(px), int(py), max(2, int(r * 1.7)), max(2, int(r))))
        m = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(m, (255, 255, 255, 255), [(px - x0, py - y0) for px, py in P])
        g.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.surf.blit(g, (x0, y0))

    def reduire(self, w=None, h=None):
        return pygame.transform.smoothscale(self.surf, (w or self.w, h or self.h))


def vague(x0, x1, y, amp, freq, phase=0.0, pas=3.0):
    n = max(2, int((x1 - x0) / pas))
    return [(x0 + (x1 - x0) * i / n, y + amp * math.sin((x0 + (x1 - x0) * i / n) * freq + phase)) for i in range(n + 1)]


def demi_ellipse(xc, yb, a, b, haut=True, expo=0.72, n=56):
    pts = []
    for i in range(n + 1):
        t = math.pi * i / n
        s = math.sin(t) ** expo
        pts.append((xc + a * math.cos(t), yb - b * s if haut else yb + b * s))
    return pts


def tranche(t, x0, x1, yh, yb, amp, freq, ph, haut, bas, trait=None, clair=None, taches=(), graine=1, amp2=None):
    h_pts = vague(x0, x1, yh, amp, freq, ph)
    b_pts = vague(x0, x1, yb, amp2 or amp, freq, ph + 1.1)
    t.remplir(h_pts + b_pts[::-1], haut, bas, taches, graine)
    if clair:
        t.polyligne(h_pts, clair, 0.9)
    if trait:
        t.polyligne(b_pts, trait, 0.9)


def laitue(t, y, x0=18, x1=222):
    haut = vague(x0, x1, y, 2.6, 0.9, 0.0, 2.0)
    bas = vague(x0, x1, y + 8, 3.2, 0.55, 1.0, 2.0)
    t.remplir(haut + bas[::-1], (178, 224, 112), (84, 146, 50))
    t.polyligne(vague(x0, x1, y + 3.5, 1.8, 0.9, 0.6, 2.0), (214, 240, 156), 0.8)
    t.polyligne(bas, (60, 112, 38), 0.8)


def tomates(t, y, xs):
    for x in xs:
        t.ellipse(x - 20, y, 40, 11, (190, 44, 38))
        t.ellipse(x - 16, y + 1.8, 32, 6, (232, 92, 76))
        t.ellipse(x - 8, y + 3, 12, 2.4, (250, 168, 148))


def garniture_jambon(t):
    tranche(t, 26, 214, 86, 92, 1.2, 0.25, 0.3, (252, 236, 160), (238, 212, 118), (212, 184, 88))
    for k, (yh, yb, ph) in enumerate(((74, 88, 0.0), (62, 76, 1.7))):
        tranche(t, 16 - k * 2, 224 + k * 2, yh, yb, 3.4, 0.21, ph, (250, 178, 178), (222, 116, 126), (190, 88, 100),
                (255, 214, 214), amp2=4.0)
        t.polyligne(vague(22, 218, (yh + yb) / 2, 2.6, 0.21, ph + 0.5), (255, 218, 218), 1.0)
    tranche(t, 28, 212, 57, 62, 1.0, 0.3, 0.0, (252, 238, 168), (240, 216, 124))


def garniture_poulet(t):
    tranche(t, 24, 216, 85, 91, 1.4, 0.3, 0.4, (252, 246, 228), (240, 230, 200), (214, 202, 168))
    for yh, yb, ph in ((73, 87, 0.2), (63, 76, 1.5)):
        tranche(t, 18, 222, yh, yb, 2.4, 0.2, ph, (240, 212, 166), (206, 166, 118), (172, 130, 86), (250, 232, 196))
        for x in range(32, 210, 22):
            t.ligne((x, yh + 3), (x + 8, yb - 2), (150, 104, 64), 1.6)
    tomates(t, 60, (52, 118, 184))
    laitue(t, 55)


def garniture_thon(t):
    tranche(t, 22, 218, 64, 91, 3.2, 0.5, 0.0, (228, 186, 162), (190, 140, 116), (160, 112, 92), None,
            taches=[(26, 64, 188, 27, 130, [(246, 216, 196), (172, 122, 100), (212, 164, 138)], 0.5, 1.5)], graine=5)
    for x, y in ((36, 66), (92, 64), (148, 66), (190, 65)):
        t.ellipse(x, y, 28, 9, (252, 246, 232))
        t.ellipse(x + 3, y + 1.5, 16, 3.4, (255, 252, 244))
    for x in (58, 136):
        t.ellipse(x, 59, 26, 9, (160, 200, 116))
        t.ellipse(x + 4, 60.5, 18, 5, (212, 234, 172))
    laitue(t, 55)


def garniture_vegetarien(t):
    tranche(t, 24, 216, 84, 91, 1.4, 0.3, 0.4, (252, 248, 230), (238, 230, 200), (212, 204, 170))
    legumes = ((73, 86, 0.3, (126, 176, 76), (68, 120, 44), (42, 84, 28)),
               (64, 77, 1.4, (106, 66, 120), (64, 36, 80), (40, 22, 56)),
               (57, 68, 2.2, (228, 82, 48), (176, 44, 30), (130, 30, 22)))
    for yh, yb, ph, c1, c2, c3 in legumes:
        tranche(t, 18, 222, yh, yb, 2.6, 0.19, ph, c1, c2, c3, None)
        for x in range(30, 210, 20):
            t.ligne((x, yh + 3), (x + 7, yb - 2), c3, 1.5)
    laitue(t, 55)


def garniture_lyonnais(t):
    tranche(t, 26, 214, 86, 92, 1.2, 0.25, 0.3, (252, 236, 160), (238, 212, 118), (212, 184, 88))
    tranche(t, 20, 220, 74, 87, 1.8, 0.22, 0.9, (248, 212, 104), (222, 170, 52), (190, 136, 34), (255, 232, 150))
    for x, y in ((50, 78), (110, 80), (172, 77)):
        t.ellipse(x, y, 10, 4.5, (200, 144, 40))
    for k in range(7):
        cx = 34 + k * 28
        y = 59 + (k % 2) * 3
        t.ellipse(cx - 18, y, 36, 21, (104, 30, 34))
        t.ellipse(cx - 16, y + 1.5, 32, 17, (150, 52, 54))
        t.ellipse(cx - 12, y + 3, 24, 10, (172, 72, 68))
        for dx, dy in ((-9, 6), (-2, 9), (6, 5), (10, 10), (0, 4)):
            t.ellipse(cx + dx, y + dy, 3.2, 2.6, (244, 226, 214))


GARNITURES = {
    "Jambon-beurre": garniture_jambon, "Poulet-crudités": garniture_poulet, "Thon-mayo": garniture_thon,
    "Végétarien": garniture_vegetarien, "Le Lyonnais": garniture_lyonnais,
}


def top_y(x):
    u = max(0.0, 1 - ((x - 120) / 102) ** 2)
    return 56 - 30 * (math.sqrt(u) ** 0.72)


def creer_sandwich(nom):
    t = Toile(240, 130)
    t.ellipse(16, 106, 208, 18, (0, 0, 0, 90))
    # pain du dessous
    bas = demi_ellipse(120, 92, 104, 20, haut=False, expo=0.7)
    t.remplir(bas, (208, 152, 80), (130, 80, 34),
              taches=[(24, 94, 192, 16, 70, [(150, 96, 44), (226, 176, 102), (172, 112, 56)], 0.4, 1.0)], graine=3)
    t.remplir([(18, 90), (222, 90), (217, 96), (23, 96)], (246, 230, 190), (228, 200, 148))
    GARNITURES.get(nom, garniture_jambon)(t)
    # pain du dessus
    haut = demi_ellipse(120, 56, 102, 30, haut=True, expo=0.72)
    t.remplir(haut, (234, 182, 102), (176, 114, 52),
              taches=[(24, 26, 192, 30, 110, [(250, 224, 164), (166, 104, 46), (196, 136, 70)], 0.4, 1.1)], graine=7)
    for k in range(5):
        cx = 50 + k * 35
        yh = top_y(cx) + 6
        t.poly([(cx - 13, 51), (cx - 5, 51), (cx + 7, yh), (cx - 1, yh)], (246, 214, 152))
        t.polyligne([(cx - 13, 51), (cx - 1, yh)], (156, 100, 46), 0.9)
    t.voile([(34, 46), (60, 32), (120, 25), (170, 28), (150, 34), (90, 38), (50, 50)], (255, 244, 210, 70))
    t.remplir([(20, 55), (220, 55), (215, 62), (25, 62)], (248, 232, 194), (232, 206, 156),
              taches=[(28, 56, 184, 6, 26, [(214, 186, 140), (226, 200, 154)], 0.5, 1.0)], graine=11)
    return t.reduire()


def slug(nom):
    s = unicodedata.normalize("NFD", nom.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace(" ", "-")


def charger_perso(nom):
    chemin = os.path.join(CHEMIN_ASSETS, slug(nom) + ".png")
    try:
        if os.path.exists(chemin):
            return pygame.image.load(chemin).convert_alpha()
    except Exception:
        pass
    return None


def image_sandwich(nom, w):
    cle = (nom, w)
    if cle not in _images:
        if nom not in _maitres:
            _maitres[nom] = charger_perso(nom) or creer_sandwich(nom)
        base = _maitres[nom]
        h = max(1, int(w * base.get_height() / base.get_width()))
        _images[cle] = pygame.transform.smoothscale(base, (w, h))
    return _images[cle]


# ---------------------------------------------------------------- ICONES D'INGREDIENTS

def creer_icone(nom):
    t = Toile(28, 28)
    t.ellipse(0.5, 0.5, 27, 27, OR)
    t.ellipse(2, 2, 24, 24, (18, 28, 50))
    if nom == "Pain":
        t.remplir(demi_ellipse(14, 14.5, 10, 6, True, 0.8), (232, 180, 100), (176, 114, 52))
        t.remplir(demi_ellipse(14, 14.5, 10, 4, False, 0.8), (190, 130, 66), (140, 86, 38))
        for x in (8, 12.5, 17):
            t.ligne((x, 13), (x + 2.5, 9.5), (246, 214, 152), 1.2)
    elif nom == "Jambon":
        tranche(t, 6, 22, 9, 18, 1.4, 0.7, 0.0, (250, 178, 178), (222, 116, 126), (190, 88, 100), (255, 218, 218))
    elif nom == "Beurre":
        t.poly([(7, 12), (21, 12), (21, 19), (7, 19)], (240, 212, 118))
        t.poly([(7, 12), (10, 8.5), (24, 8.5), (21, 12)], (252, 238, 168))
        t.poly([(21, 12), (24, 8.5), (24, 15.5), (21, 19)], (214, 184, 84))
    elif nom == "Poulet":
        t.ellipse(6, 8, 16, 12, (206, 166, 118))
        t.ellipse(7.5, 9, 13, 8, (240, 212, 166))
        for x in (9, 13, 17):
            t.ligne((x, 10), (x + 2, 16), (150, 104, 64), 1.2)
    elif nom == "Crudités":
        t.ellipse(5, 7, 16, 13, (96, 160, 62))
        t.ellipse(7, 8, 12, 8, (170, 220, 108))
        t.ellipse(13, 12, 9, 9, (200, 48, 40))
        t.ellipse(15, 13.5, 4, 3, (250, 168, 148))
    elif nom == "Thon":
        t.ellipse(5, 9, 15, 10, (112, 142, 174))
        t.poly([(18, 14), (24, 9), (24, 19)], (112, 142, 174))
        t.ellipse(8, 12, 2.2, 2.2, NUIT)
        t.ellipse(8, 14, 9, 3, (172, 196, 220))
    elif nom == "Mayonnaise":
        t.ellipse(7, 9, 14, 11, (250, 242, 220))
        t.ellipse(9, 5.5, 10, 7, (255, 250, 236))
        t.ellipse(11, 4.5, 6, 3, (255, 253, 244))
    elif nom == "Saucisson":
        t.ellipse(6, 7.5, 16, 13, (104, 30, 34))
        t.ellipse(7.5, 9, 13, 10, (156, 56, 58))
        for dx, dy in ((10, 11), (14, 13), (16, 10), (12, 16)):
            t.ellipse(dx, dy, 2.2, 1.8, (244, 226, 214))
    elif nom == "Fromage":
        t.poly([(5, 19), (23, 19), (23, 9)], (222, 170, 52))
        t.poly([(5, 19), (23, 9), (23, 7)], (250, 218, 118))
        t.ellipse(14, 14, 3, 3, (190, 136, 34))
        t.ellipse(19, 16, 2.4, 2.4, (190, 136, 34))
    elif nom == "Légumes grillés":
        t.ellipse(6, 8, 14, 11, (84, 48, 100))
        t.ellipse(8, 9, 8, 4, (140, 100, 156))
        t.poly([(17, 9), (23, 7), (21, 12)], (96, 160, 62))
    elif nom == "Eau minérale":
        t.poly([(11, 8), (17, 8), (17, 10), (19, 13), (19, 22), (9, 22), (9, 13), (11, 10)], (150, 200, 235))
        t.poly([(11, 5), (17, 5), (17, 8), (11, 8)], (60, 100, 160))
        t.poly([(9, 15), (19, 15), (19, 18), (9, 18)], (240, 248, 255))
    elif nom == "Cola":
        t.poly([(9, 8), (19, 8), (19, 22), (9, 22)], (196, 40, 40))
        t.ellipse(9, 6, 10, 4, (200, 204, 210))
        t.poly([(9, 13), (19, 12), (19, 15), (9, 16)], (250, 240, 240))
    elif nom == "Jus d'orange":
        t.poly([(8, 8), (20, 8), (18, 22), (10, 22)], (240, 150, 30))
        t.ellipse(8, 6.5, 12, 3, (252, 200, 90))
        t.ligne((16, 4), (14, 14), (200, 60, 50), 1.2)
    elif nom == "Thé glacé":
        t.poly([(8, 8), (20, 8), (18, 22), (10, 22)], (190, 110, 40))
        t.ellipse(8, 6.5, 12, 3, (230, 170, 100))
        t.ellipse(15, 6, 8, 8, (250, 230, 90))
    elif nom == "Café":
        t.ellipse(7, 11, 14, 11, (244, 236, 216))
        t.ellipse(8.5, 12, 11, 4, (110, 64, 36))
        t.ellipse(19, 13, 5, 6, (244, 236, 216), 1.4)
        t.ligne((11, 4), (12, 9), (230, 230, 240), 1.0)
        t.ligne((15, 4), (16, 9), (230, 230, 240), 1.0)
    elif nom == "Cookie":
        t.ellipse(5, 6, 18, 17, (206, 150, 84))
        for dx, dy in ((9, 10), (14, 9), (12, 14), (17, 15), (8, 17)):
            t.ellipse(dx, dy, 3, 3, (84, 48, 28))
    elif nom == "Brownie":
        t.poly([(6, 10), (22, 10), (22, 21), (6, 21)], (84, 48, 28))
        t.poly([(6, 10), (9, 7), (25, 7), (22, 10)], (120, 76, 46))
        t.ellipse(10, 13, 3, 2.4, (200, 150, 100))
        t.ellipse(15, 16, 3, 2.4, (200, 150, 100))
    elif nom == "Tarte aux pommes":
        t.ellipse(4, 7, 20, 16, (210, 150, 70))
        t.ellipse(7, 9, 14, 11, (240, 200, 110))
        for k in range(5):
            t.ligne((9 + k * 2.4, 11), (10 + k * 2.4, 19), (190, 120, 50), 1.0)
    return t.reduire()


def icone(nom, x, y, taille=24):
    cle = ("icone", nom, taille)
    if cle not in _images:
        if ("icone", nom) not in _maitres:
            _maitres[("icone", nom)] = creer_icone(nom)
        _images[cle] = pygame.transform.smoothscale(_maitres[("icone", nom)], (taille, taille))
    screen.blit(_images[cle], (x, y))


def cameo(x, y, w, h):
    cadre((x, y, w, h), (16, 44, 50), OR, 10, 2)
    pygame.draw.polygon(screen, (22, 60, 64), pans((x + 8, y + 8, w - 16, h - 16), 7))


ui = {"service": 0, "resto": 0, "bilan": 0, "dash_b": 0, "courses_cat": "ing", "menu_vue": "sand", "dash_vue": "dev", "ecran": "jeu", "quitter": False, "confirme": False}
CONCURRENCE = (240, 150, 70)


def page_debut(cle, total, par_page):
    nb = max(1, math.ceil(total / par_page))
    ui[cle] = max(0, min(ui[cle], nb - 1))
    return ui[cle] * par_page


def changer_page(cle, delta):
    ui[cle] += delta


def pager(cle, total, par_page, cx, y):
    nb = max(1, math.ceil(total / par_page))
    if nb <= 1:
        return
    p = ui[cle]
    bouton((cx - 80, y, 40, 28), "<", p > 0, lambda: changer_page(cle, -1), "onglet")
    texte(f"{p + 1}/{nb}", (cx, y + 14), T_NORMAL, OR_CLAIR, "c")
    bouton((cx + 40, y, 40, 28), ">", p < nb - 1, lambda: changer_page(cle, 1), "onglet")


def zone_clic(rect, action):
    boutons.append((pygame.Rect(rect), action, True))


def molette(delta):
    if jeu.en_service():
        cle, total, pp = "service", len(jeu.restos), 5
    elif jeu.onglet == "resto":
        cle, total, pp = "resto", len(LIEUX), 5
    elif jeu.onglet == "bilan":
        cle, total, pp = "bilan", len(jeu.restos), 7
    elif jeu.onglet == "dash" and ui["dash_vue"] == "boutiques":
        cle, total, pp = "dash_b", len(jeu.restos), 7
    else:
        return
    nb = max(1, math.ceil(total / pp))
    ui[cle] = max(0, min(nb - 1, ui[cle] + delta))


def libelle_dlc(r, nom):
    d = jeu.dlc(r, nom)
    if d is None:
        return "-", CREME_SOMBRE
    j = (d - jeu.date).days
    if j <= 0:
        return "auj.", ROUGE
    if j == 1:
        return "1 j", OR_CLAIR
    return f"{j} j", CREME


# ---------------------------------------------------------------- ECRANS

def init_ecran():
    global screen, clock, FOND_SURF
    pygame.init()
    screen = pygame.display.set_mode((LARGEUR, HAUTEUR))
    pygame.display.set_caption("Sandwich Empire")
    clock = pygame.time.Clock()
    FOND_SURF = construire_fond()
    screen.blit(FOND_SURF, (0, 0))
    texte("Préparation du restaurant...", (LARGEUR // 2, HAUTEUR // 2), T_TITRE_G, OR_CLAIR, "c")
    pygame.display.flip()
    for rec in RECETTES:
        for largeur in (138, 92):
            image_sandwich(rec["nom"], largeur)
    for nom, _p in ARTICLES:
        for taille in (20, 22, 24, 26):
            cle = ("icone", nom, taille)
            if cle not in _images:
                icone(nom, -100, -100, taille)


def dessiner_entete():
    pygame.draw.rect(screen, (8, 12, 24), (0, 0, LARGEUR, 68))
    pygame.draw.line(screen, OR, (0, 67), (LARGEUR, 67), 2)
    pygame.draw.line(screen, OR_SOMBRE, (0, 71), (LARGEUR, 71), 1)
    eventail(50, 52, 32)
    d = jeu.date
    texte(heure(jeu.minute), (92, 12), T_GRAND, CREME)
    texte(f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]} {d.year}".upper(), (250, 12), T_PETIT, OR_CLAIR,
          max_w=250)
    texte(LIBELLES[jeu.phase], (250, 38), T_PETIT, CREME_SOMBRE, max_w=250)

    texte("CAISSE", (520, 8), T_MINI, OR)
    texte(eur(jeu.caisse), (520, 26), T_TITRE_G, OR_CLAIR if jeu.caisse >= 0 else ROUGE, max_w=160)
    texte("RÉPUTATION", (700, 8), T_MINI, OR)
    texte(f"{jeu.rep:.0f}", (830, 8), T_MINI, CREME, "d")
    pygame.draw.polygon(screen, (22, 30, 54), pans((700, 30, 130, 14), 4))
    largeur = int(126 * jeu.rep / 100)
    if largeur > 8:
        pygame.draw.polygon(screen, OR, pans((702, 32, largeur, 10), 3))
    pygame.draw.polygon(screen, OR_SOMBRE, pans((700, 30, 130, 14), 4), 1)
    for k in range(1, 10):
        pygame.draw.line(screen, NUIT, (700 + k * 13, 33), (700 + k * 13, 40), 1)

    x0 = LARGEUR - 16 - 4 * 48
    for i, v in enumerate(VITESSES):
        bouton((x0 + i * 48, 18, 44, 32), f"x{v}", True, lambda v=v: jeu.regler_vitesse(v),
               "onglet_actif" if jeu.vitesse == v else "onglet")
    if jeu.en_service():
        bouton((x0 - 112, 18, 104, 32), "Reprendre" if jeu.pause else "Pause", True, jeu.basculer_pause, "principal")
    else:
        bouton((x0 - 138, 18, 130, 32), "Sauvegarder", True, action_sauvegarder)


def panneau_menu_service():
    eventail(435, 430, 175, 13, (24, 34, 58), (18, 26, 48), (14, 20, 38))
    panneau((20, 436, 830, 200), "Au menu")
    for k, mn in enumerate(jeu.menu):
        x = 34 + k * 162
        cameo(x, 476, 152, 76)
        img = image_sandwich(mn["rec"]["nom"], 138)
        screen.blit(img, (x + (152 - img.get_width()) // 2, 476 + (76 - img.get_height()) // 2 + 2))
        texte(mn["rec"]["nom"], (x + 76, 566), T_PETIT, OR_CLAIR, "cx", max_w=150)
        if mn["etat"] == "verrouille":
            poly_alpha(screen, (11, 16, 30, 150), pans((x, 476, 152, 76), 10))
            texte("à développer", (x + 76, 590), T_PETIT, CREME_SOMBRE, "cx")
        elif mn["etat"] == "retire":
            texte("retiré du menu", (x + 76, 590), T_PETIT, CREME_SOMBRE, "cx")
        else:
            prix = jeu.resto_sel()["prix"][mn["rec"]["nom"]] if jeu.restos else mn["rec"]["prix_ref"]
            texte(f"{prix:.2f} €  |  {mn['ventes_jour']} vendus", (x + 76, 590), T_PETIT, CREME, "cx", max_w=150)


def dessiner_service():
    m = jeu.minute
    n = len(jeu.restos)
    if n <= 3:
        panneau_menu_service()
        debut = 0
    else:
        debut = page_debut("service", n, 5)
    for i, r in enumerate(jeu.restos[debut:debut + 5]):
        idx = debut + i
        y = 80 + i * 110
        lieu_ = r["lieu"]
        choisi = idx == jeu.sel
        cadre((20, y, 830, 102), CARTE_FOND, OR_CLAIR if choisi else OR_SOMBRE, 10, 2 if choisi else 1, False)
        zone_clic((20, y, 830, 102), lambda k=idx: setattr(jeu, "sel", k))
        devanture(34, y + 14, 62, 50)
        w = texte(lieu_["nom"].upper(), (110, y + 8), T_TITRE, OR_CLAIR, max_w=240)
        texte(lieu_["ville"], (110 + w + 12, y + 12), T_MINI, CREME_SOMBRE)
        aff = r["aff"] * 100
        promo = f"  |  {r['promo']['nom']}" if r["promo"] else ""
        texte(f"Réputation {r['rep']:.0f}  |  Affluence {aff:.0f} %{promo}", (840, y + 11), T_PETIT,
              ROUGE if aff > 100 else (OR_CLAIR if r["promo"] else CREME_SOMBRE), "d", max_w=330)
        texte(f"File : {len(r['file'])}", (110, y + 34), T_PETIT)
        for j, c in enumerate(r["file"][:33]):
            frac = 1 - (m - c["arrive"]) / c["patience"]
            col = VERT if frac > 0.5 else (OR_CLAIR if frac > 0.25 else ROUGE)
            silhouette(212 + j * 17, y + 54, col)
        texte("Cuisine", (110, y + 60), T_PETIT)
        pas_c = min(20, 170 // max(1, len(r["cuis"])))
        for j, fin in enumerate(r["cuis"]):
            cuisinier(196 + j * pas_c, y + 78, fin > m)
        occ = jeu.sieges_occupes(r)
        places = r["sieges"]
        texte(f"Salle : {occ}/{places}", (370, y + 60), T_PETIT)
        pas_s = min(15.0, 370 / places)
        cote = max(4, int(pas_s) - 3)
        for j in range(places):
            pygame.draw.rect(screen, VERT if j < occ else (52, 62, 90), (470 + int(j * pas_s), y + 62, cote, cote),
                             border_radius=2)
        s = r["svc"]
        texte(f"Servis {s['servis']}  |  Partis : attente {s['att']}, rupture {s['rup']}, "
              f"salle pleine {s['salle']}  |  CA {eur(s['ca'])}", (34, y + 82), T_PETIT, CREME, max_w=790)

    r = jeu.resto_sel()
    panneau((870, 80, 290, 332), "Stock")
    if r is not None:
        texte(f"{r['lieu']['nom']} ({r['lieu']['ville']})", (1015, 116), T_MINI, CREME_SOMBRE, "cx", max_w=260)
        for i, (nom, _p) in enumerate(INGREDIENTS):
            yy = 138 + i * 26
            q = jeu.stock_total(r, nom)
            icone(nom, 886, yy, 22)
            texte(nom, (914, yy + 2), T_PETIT, max_w=104)
            dtxt, dcol = libelle_dlc(r, nom)
            texte(dtxt, (1076, yy + 4), T_MINI, dcol, "d")
            texte(f"{q:.0f}", (1138, yy + 2), T_GRAS, ROUGE if q < 8 else CREME, "d")

    panneau((870, 420, 290, 140), "Publicités")
    if jeu.pubs:
        for i, p in enumerate(jeu.pubs):
            texte(f"{p['nom']} ({p['jours']} j)", (890, 460 + i * 24), T_PETIT, VERT, max_w=250)
    else:
        texte("Aucune pub active", (890, 460), T_PETIT, CREME_SOMBRE)
    servis = sum(r["svc"]["servis"] for r in jeu.restos)
    ca = sum(r["svc"]["ca"] for r in jeu.restos)
    texte(f"Total : {servis} servis, {eur(ca)}", (890, 520), T_NORMAL, OR_CLAIR, max_w=250)

    cadre((870, 570, 290, 66), PANNEAU_FOND, OR_SOMBRE, 10, 1, False)
    if n > 1:
        texte("Clique une boutique pour voir son stock", (885, 576), T_MINI, CREME_SOMBRE, max_w=265)
    if n > 5:
        pager("service", n, 5, 1015, 598)

    if jeu.pause:
        poly_alpha(screen, (0, 0, 0, 120), pans((20, 80, 830, 550), 10))
        texte("PAUSE", (435, 330), T_GRAND, OR_CLAIR, "c")


def resume_sauvegarde(nom, libelle):
    meta = lire_meta(nom)
    if not meta:
        return None
    d = datetime.date.fromisoformat(meta["date_jeu"])
    n = meta["restos"]
    quand = meta["enregistre"][:5] + " " + meta["enregistre"][-5:]
    return (f"{libelle} : {d.day} {MOIS[d.month - 1]} {d.year}, {eur(meta['caisse'])}, "
            f"{n} boutique{'s' if n > 1 else ''} ({quand})")


def action_sauvegarder():
    if jeu.en_service():
        jeu.log("Sauvegarde impossible pendant un service : attends la fin du service.")
        return
    try:
        ecrire_sauvegarde(jeu, "partie")
        jeu.log("Partie sauvegardée.")
    except Exception as e:
        jeu.log(f"Échec de la sauvegarde : {e}")


def action_charger(nom):
    global jeu
    g = lire_sauvegarde(nom)
    if g is None:
        jeu.log("Sauvegarde introuvable ou illisible.")
        return
    jeu = g
    ui["ecran"] = "jeu"
    ui["confirme"] = False
    ui["vente"] = None
    for cle in ("service", "resto", "bilan", "dash_b"):
        ui[cle] = 0
    jeu.log("Partie chargée.")


def action_nouvelle():
    global jeu
    if ui["ecran"] == "menu" and not ui["confirme"]:
        ui["confirme"] = True
        return
    jeu = Jeu()
    ui["ecran"] = "jeu"
    ui["confirme"] = False
    ui["vente"] = None
    for cle in ("service", "resto", "bilan", "dash_b"):
        ui[cle] = 0


def action_ecran(nom):
    ui["ecran"] = nom
    ui["confirme"] = False


def action_quitter():
    # Dans un navigateur, on ne peut pas fermer l'onglet : retour à l'écran titre.
    if sys.platform == "emscripten":
        ui["ecran"] = "titre"
        ui["confirme"] = False
    else:
        ui["quitter"] = True


def bouton_menu(y, label, actif, action, style="normal"):
    bouton((LARGEUR // 2 - 280, y, 560, 44), label, actif, action, style, T_GRAS)


def dessiner_titre():
    screen.blit(FOND_SURF, (0, 0))
    eventail(LARGEUR // 2, 230, 110)
    texte("SANDWICH EMPIRE", (LARGEUR // 2, 282), T_GRAND, OR_CLAIR, "c")
    texte("D'une sandwicherie lyonnaise à une chaîne mondiale", (LARGEUR // 2, 328), T_NORMAL, CREME_SOMBRE, "c")
    y = 374
    manuelle = resume_sauvegarde("partie", "Continuer")
    auto = resume_sauvegarde("auto", "Auto-sauvegarde")
    if manuelle:
        bouton_menu(y, manuelle, True, lambda: action_charger("partie"), "principal")
        y += 56
    if auto:
        bouton_menu(y, auto, True, lambda: action_charger("auto"))
        y += 56
    bouton_menu(y, "Nouvelle partie", True, action_nouvelle, "onglet" if (manuelle or auto) else "principal")
    y += 56
    bouton_menu(y, "Quitter", True, action_quitter, "onglet")


def dessiner_menu_pause():
    poly_alpha(screen, (0, 0, 0, 175), [(0, 0), (LARGEUR, 0), (LARGEUR, HAUTEUR), (0, HAUTEUR)])
    cadre((LARGEUR // 2 - 320, 130, 640, 480), PANNEAU_FOND, OR, 14)
    texte("MENU", (LARGEUR // 2, 176), T_GRAND, OR_CLAIR, "c")
    y = 226
    bouton_menu(y, "Reprendre la partie", True, lambda: action_ecran("jeu"), "principal")
    y += 52
    bouton_menu(y, "Sauvegarder maintenant" if not jeu.en_service() else "Sauvegarde possible entre deux services",
                not jeu.en_service(), action_sauvegarder)
    y += 52
    m1 = resume_sauvegarde("partie", "Charger")
    bouton_menu(y, m1 or "Charger la sauvegarde (aucune)", bool(m1), lambda: action_charger("partie"), "onglet")
    y += 52
    m2 = resume_sauvegarde("auto", "Charger l'auto-sauvegarde")
    bouton_menu(y, m2 or "Charger l'auto-sauvegarde (aucune)", bool(m2), lambda: action_charger("auto"), "onglet")
    y += 52
    bouton_menu(y, "Cliquer encore : la partie en cours sera perdue" if ui["confirme"] else "Nouvelle partie", True,
                action_nouvelle, "principal" if ui["confirme"] else "onglet")
    y += 52
    bouton_menu(y, "Quitter", True, action_quitter, "onglet")
    if jeu.journal:
        texte(jeu.journal[-1], (LARGEUR // 2, 580), T_PETIT, OR_CLAIR, "c", max_w=600)


def choisir_resto(delta):
    jeu.sel = (jeu.sel + delta) % len(jeu.restos)


def onglet_courses():
    panneau((20, 116, 1140, 520), "Courses")
    r = jeu.resto_sel()
    if r is None:
        texte("Aucune boutique ouverte.", (40, 170), T_NORMAL, CREME_SOMBRE)
        return
    n = len(jeu.restos)
    eventail(1035, 470, 100, 11, (34, 44, 70), (24, 32, 54), PANNEAU_FOND)

    bouton((40, 156, 40, 30), "<", n > 1, lambda: choisir_resto(-1), "onglet")
    texte(f"{r['lieu']['nom']} ({r['lieu']['ville']})".upper(), (270, 171), T_TITRE, OR_CLAIR, "c", max_w=330)
    bouton((460, 156, 40, 30), ">", n > 1, lambda: choisir_resto(1), "onglet")
    cat = ui["courses_cat"]
    bouton((640, 156, 230, 30), "Ingrédients", True, lambda: ui.__setitem__("courses_cat", "ing"),
           "onglet_actif" if cat == "ing" else "onglet")
    bouton((880, 156, 250, 30), "Boissons et desserts", True, lambda: ui.__setitem__("courses_cat", "extras"),
           "onglet_actif" if cat == "extras" else "onglet")
    if jeu.phase == "prep_midi":
        texte("Livraison immédiate : le matin, avant l'ouverture. Prix HT, TVA en plus.", (40, 192), T_PETIT, VERT,
              max_w=700)
    else:
        texte("Livraison demain matin, avant le premier service. Prix HT, TVA en plus.", (40, 192), T_PETIT, OR_CLAIR,
              max_w=700)
    if r["gestionnaire"]:
        texte("Gestionnaire en poste : il commande quand tu lances le service du matin.", (40, 210), T_MINI, VERT,
              max_w=700)

    liste = INGREDIENTS if cat == "ing" else BOISSONS + DESSERTS
    taux = FISCALITE[r["lieu"]["pays"]]["achat"]
    for titre, x in (("ARTICLE", 76), ("QUALITÉ" if cat == "ing" else "VENTE TTC", 200), ("PRIX HT", 346),
                     ("VEILLE", 414), ("STOCK", 482), ("DLC", 562)):
        texte(titre, (x, 230), T_MINI, OR)
    pygame.draw.line(screen, OR_SOMBRE, (40, 246), (870, 246), 1)
    for i, (nom, _p) in enumerate(liste):
        y = 252 + i * 24
        p = jeu.prix_achat(r, nom)
        v = jeu.prix_veille[nom] * r["lieu"]["cout_ing"] * ETOILES_PRIX[jeu.etoiles.get(nom, 0)]
        var = (p / v - 1) * 100 if v else 0
        icone(nom, 44, y, 20)
        texte(nom, (74, y + 1), T_PETIT, max_w=122)
        if cat == "ing":
            niv = jeu.etoiles[nom]
            bouton((198, y, 22, 20), "-", niv > 0, lambda nom=nom: jeu.changer_etoiles(nom, -1), "onglet")
            for k in range(ETOILES_MAX):
                etoile(235 + k * 15, y + 10, 6, OR_CLAIR if k < niv else (52, 62, 90))
            suivant_ok = niv < ETOILES_MAX and jeu.rep >= ETOILES_REP[niv + 1]
            bouton((312, y, 22, 20), "+", suivant_ok, lambda nom=nom: jeu.changer_etoiles(nom, 1), "normal")
        else:
            texte(f"{PRIX_VENTE_EXTRAS[nom]:.2f} €", (200, y + 2), T_PETIT, OR_CLAIR)
        texte(f"{p:.2f} €", (346, y + 1), T_PETIT)
        texte(f"{var:+.1f} %", (414, y + 3), T_MINI, ROUGE if var > 0.05 else (VERT if var < -0.05 else CREME_SOMBRE))
        stock = jeu.stock_total(r, nom)
        attente = jeu.en_livraison(r, nom)
        texte(f"{stock:.0f}", (482, y + 1), T_PETIT, ROUGE if stock + attente < 10 else CREME)
        if attente:
            texte(f"+{attente}", (518, y + 4), T_MINI, OR_CLAIR)
        dtxt, dcol = libelle_dlc(r, nom)
        texte(dtxt, (562, y + 2), T_PETIT, dcol)
        for j, q in enumerate((10, 50, 100)):
            bouton((628 + j * 78, y, 70, 20), f"+{q}", jeu.caisse >= q * p * (1 + taux),
                   lambda r=r, n=nom, q=q: jeu.commander(r, n, q))
    texte(f"Achats ce mois : {eur(jeu.mois['achats_ht'])} HT", (40, 500), T_PETIT, CREME_SOMBRE, max_w=500)
    if cat == "ing":
        texte("Chaque étoile : +0,1 de note aux recettes qui utilisent l'ingrédient, achat plus cher, "
              "prix de référence +2 % (tes prix suivent).", (40, 522), T_PETIT, OR_CLAIR, max_w=1090)
        prochain = [ETOILES_REP[i + 1] for i in jeu.etoiles.values() if i < ETOILES_MAX]
        manque = [x for x in prochain if x > jeu.rep]
        if manque:
            texte(f"Prochain palier d'étoiles débloqué à la réputation {min(manque)}. Seuls les nouveaux achats changent "
                  f"de qualité.", (40, 544), T_PETIT, CREME_SOMBRE, max_w=1090)
    else:
        texte("Produits achetés tout faits, revendus environ 3 fois leur prix dans la formule (onglet Menu).", (40, 522),
              T_PETIT, OR_CLAIR, max_w=1090)
    texte("Un gestionnaire de stock (onglet Restaurants) calcule et commande à ta place. "
          "Livraisons uniquement le matin avant le premier service.", (40, 590), T_PETIT, CREME_SOMBRE, max_w=1090)


def onglet_menu():
    panneau((20, 116, 1140, 520), "Menu et prix")
    r = jeu.resto_sel()
    if r is None:
        texte("Aucune boutique ouverte.", (40, 170), T_NORMAL, CREME_SOMBRE)
        return
    n = len(jeu.restos)
    bouton((40, 156, 40, 30), "<", n > 1, lambda: choisir_resto(-1), "onglet")
    texte(f"{r['lieu']['nom']} ({r['lieu']['ville']})".upper(), (270, 171), T_TITRE, OR_CLAIR, "c", max_w=330)
    bouton((460, 156, 40, 30), ">", n > 1, lambda: choisir_resto(1), "onglet")
    vue = ui["menu_vue"]
    bouton((520, 156, 150, 30), "Sandwichs", True, lambda: ui.__setitem__("menu_vue", "sand"),
           "onglet_actif" if vue == "sand" else "onglet")
    bouton((680, 156, 240, 30), "Formule boisson + dessert", True, lambda: ui.__setitem__("menu_vue", "formule"),
           "onglet_actif" if vue == "formule" else "onglet")
    bouton((930, 156, 200, 30), "Promotions", True, lambda: ui.__setitem__("menu_vue", "promo"),
           "onglet_actif" if vue == "promo" else "onglet")
    if vue == "formule":
        menu_formule(r)
        return
    if vue == "promo":
        menu_promos(r)
        return

    if r["concurrence"]:
        infos = []
        for e in r["concurrence"]:
            nom = {"ouverture": "nouveau concurrent", "promo": "promotion d'un concurrent",
                   "fermeture": "fermeture d'un concurrent"}[e["type"]]
            infos.append(f"{nom} (clients {e['clients'] - 1:+.0%}, prix de réf. {e['prix'] - 1:+.0%}, {e['jours']} j)")
        texte("Concurrence : " + " ; ".join(infos), (40, 193), T_MINI, CONCURRENCE, max_w=690)
    else:
        texte(f"Prix de cette boutique uniquement. Niveau de prix local x{r['lieu']['niveau']:.2f}.", (40, 193), T_MINI,
              CREME_SOMBRE, max_w=690)
    bouton((740, 188, 180, 24), "Prix conseillés", True, lambda: jeu.prix_conseilles(r), "onglet")
    bouton((930, 188, 200, 24), "Copier vers toutes", n > 1, lambda: jeu.copier_prix(r), "onglet")

    for i, mn in enumerate(jeu.menu):
        rec = mn["rec"]
        y = 218 + i * 82
        carte((30, y, 1120, 78))
        cameo(42, y + 4, 140, 70)
        img = image_sandwich(rec["nom"], 126)
        screen.blit(img, (42 + (140 - img.get_width()) // 2, y + 4 + (70 - img.get_height()) // 2 + 2))
        verrou = mn["etat"] == "verrouille"
        if verrou:
            poly_alpha(screen, (11, 16, 30, 150), pans((42, y + 4, 140, 70), 10))
        texte(rec["nom"].upper(), (196, y + 5), T_TITRE, OR_CLAIR, max_w=215)
        for k, ing in enumerate(rec["ing"]):
            icone(ing, 196 + k * 28, y + 30, 22)
        if verrou:
            texte("Pas encore développé", (196, y + 56), T_PETIT, CREME_SOMBRE)
            for j, (label, test) in enumerate(rec["reqs"]):
                ok = test(jeu)
                texte(("[x] " if ok else "[ ] ") + label, (470, y + 12 + j * 22), T_PETIT, VERT if ok else CREME_SOMBRE)
            texte(f"Mise au point : {eur(rec['dev'])}", (470, y + 50), T_PETIT)
            bouton((900, y + 22, 230, 34), "Développer et tester",
                   jeu.caisse >= rec["dev"] and jeu.conditions_ok(rec), lambda m=mn: jeu.developper(m))
            continue
        prix = r["prix"][rec["nom"]]
        cout = jeu.cout_recette(r, mn)
        marge = prix / (1 + jeu.tva_moyenne(r)) - cout
        stars = jeu.etoiles_recette(mn)
        etoile(204, y + 66, 6, OR_CLAIR if stars else (52, 62, 90))
        texte(f"{stars} premium" if stars else "standard", (214, y + 58), T_MINI, CREME_SOMBRE)
        if mn["etat"] != "actif":
            texte("Retiré du menu", (300, y + 58), T_MINI, CREME_SOMBRE)
        texte(f"Coût : {cout:.2f} € HT", (440, y + 6), T_NORMAL, max_w=270)
        texte(f"Prix de référence ici : {jeu.prix_local_ref(r, mn):.2f} €", (440, y + 30), T_PETIT, CREME_SOMBRE,
              max_w=280)
        texte(f"Marge HT : {marge:.2f} €", (440, y + 52), T_PETIT, VERT if marge > 0 else ROUGE, max_w=280)
        for k, delta in enumerate((-0.5, -0.1)):
            bouton((730 + k * 50, y + 6, 46, 26), f"{delta:+.1f}", True,
                   lambda m=mn, d=delta: jeu.changer_prix(r, m, d))
        texte(f"{prix:.2f} €", (875, y + 19), T_TITRE_G, OR_CLAIR, "c")
        for k, delta in enumerate((0.1, 0.5)):
            bouton((930 + k * 50, y + 6, 46, 26), f"{delta:+.1f}", True,
                   lambda m=mn, d=delta: jeu.changer_prix(r, m, d))
        bonus = NOTE_PAR_ETOILE * stars
        if mn["ventes"] >= 25:
            texte(f"Note : {jeu.note_recette(mn):.1f}/5 ({mn['ventes']} ventes)", (730, y + 48), T_PETIT, OR_CLAIR,
                  max_w=300)
        else:
            texte(f"Note : ? (+{bonus:.1f} premium) ({mn['ventes']}/25 ventes)", (730, y + 48), T_PETIT,
                  CREME_SOMBRE, max_w=300)
        libelle = "Retirer" if mn["etat"] == "actif" else "Remettre"
        bouton((1040, y + 6, 100, 26), libelle, mn["etat"] != "actif" or nb_actifs(jeu) > 1,
               lambda m=mn: jeu.basculer(m), "onglet")


def raison_promo(r, cle):
    if r["promo"]:
        return "Une offre est déjà en cours."
    if r["promo_cd"] and jeu.date < r["promo_cd"]:
        d = r["promo_cd"]
        return f"Pause : de nouveau disponible le {d.day} {MOIS[d.month - 1]}."
    if cle == "ouverture":
        if r["offre_ouverture"]:
            return "Offre d'ouverture déjà utilisée."
        if (jeu.date - r["ouvert_le"]).days > OUVERTURE_JOURS_MAX:
            return "Réservée aux 30 premiers jours de la boutique."
    return ""


def menu_promos(r):
    age = (jeu.date - r["ouvert_le"]).days
    texte("RÉPUTATION DE LA BOUTIQUE", (40, 204), T_TITRE, OR_CLAIR)
    jauge(40, 236, 360, 18, r["rep"])
    texte(f"{r['rep']:.0f}/100", (412, 234), T_NORMAL)
    aff = jeu.affluence_prevue(r)
    texte(f"Ouverte depuis {age} jours. Affluence prévue au prochain midi : {aff:.0f} % de ce que l'équipe sert sans file.",
          (40, 264), T_PETIT, ROUGE if aff > 100 else CREME, max_w=1090)
    base = facteur_reputation(70)
    effet = "   ".join(f"{x} : {100 * facteur_reputation(x) / base:.0f} %" for x in (20, 40, 50, 70, 90))
    texte("Effet de la réputation sur l'affluence (100 % à 70) :  " + effet, (40, 288), T_PETIT, CREME_SOMBRE, max_w=1090)
    for i, cle in enumerate(("ouverture", "standard")):
        pr = PROMOS[cle]
        x = 40 + i * 558
        carte((x, 318, 540, 200))
        texte(pr["nom"].upper(), (x + 16, 328), T_TITRE, OR_CLAIR)
        texte(f"-{pr['remise']:.0%} sur les sandwichs pendant {pr['jours']} jours.", (x + 16, 360), T_NORMAL, CREME,
              max_w=508)
        texte(f"+{pr['clients'] - 1:.0%} de clients, et la réputation monte {pr['rep']:g} fois plus vite.",
              (x + 16, 384), T_PETIT, CREME, max_w=508)
        texte("Une seule fois, pendant le premier mois de la boutique." if cle == "ouverture"
              else f"Utilisable à tout moment, avec {PROMO_PAUSE} jours de pause ensuite.", (x + 16, 406), T_PETIT,
              CREME_SOMBRE, max_w=508)
        texte(f"Coût de lancement : {eur(pr['cout'])}. Les prix remisés rognent la marge.", (x + 16, 428), T_PETIT,
              CREME_SOMBRE, max_w=508)
        raison = raison_promo(r, cle)
        if raison:
            texte(raison, (x + 16, 450), T_PETIT, OR_CLAIR, max_w=508)
        bouton((x + 16, 478, 508, 34), f"Lancer : {pr['nom']}", jeu.peut_promo(r, cle),
               lambda r=r, c=cle: jeu.lancer_promo(r, c), "principal" if cle == "ouverture" else "normal", T_GRAS)
    if r["promo"]:
        texte(f"En cours : {r['promo']['nom']} (-{r['promo']['remise']:.0%}), encore {r['promo']['jours']} jours.",
              (40, 540), T_NORMAL, VERT, max_w=1090)
    else:
        texte("Aucune offre en cours dans cette boutique.", (40, 540), T_NORMAL, CREME_SOMBRE)
    texte("Sans offre, une nouvelle boutique démarre à 12 de réputation : il faut convaincre pour faire venir du monde.",
          (40, 580), T_PETIT, CREME_SOMBRE, max_w=1090)


def menu_formule(r):
    bouton((40, 198, 300, 34), "Formule ACTIVE" if jeu.formule else "Formule désactivée", True, jeu.basculer_formule,
           "principal" if jeu.formule else "onglet", T_GRAS)
    texte(f"{FORMULE_TAUX:.0%} des clients ajoutent une boisson et un dessert (au hasard), avec {FORMULE_REMISE:.0%} "
          f"de remise.", (360, 206), T_PETIT, CREME, max_w=770)
    f = FISCALITE[r["lieu"]["pays"]]
    for titre, x in (("ARTICLE", 76), ("ACHAT HT", 300), ("VENTE TTC", 410), ("MARGE HT", 520),
                     ("VENDUS CE MOIS", 640), ("STOCK", 800), ("DLC", 880)):
        texte(titre, (x, 250), T_MINI, OR)
    pygame.draw.line(screen, OR_SOMBRE, (40, 268), (1120, 268), 1)
    for i, (nom, _p) in enumerate(BOISSONS + DESSERTS):
        y = 276 + i * 30
        achat = jeu.prix_achat(r, nom)
        vente = PRIX_VENTE_EXTRAS[nom] * (1 - FORMULE_REMISE)
        marge = vente / (1 + jeu.tva_extra(f, nom, True)) - achat
        icone(nom, 44, y, 24)
        texte(nom, (76, y + 3), T_NORMAL, max_w=200)
        texte(f"{achat:.2f} €", (300, y + 3), T_PETIT)
        texte(f"{vente:.2f} €", (410, y + 3), T_PETIT, OR_CLAIR)
        texte(f"{marge:.2f} €", (520, y + 3), T_PETIT, VERT if marge > 0 else ROUGE)
        texte(f"{jeu.mois_extras.get(nom, 0)}", (640, y + 3), T_PETIT)
        stock = jeu.stock_total(r, nom)
        texte(f"{stock:.0f}", (800, y + 3), T_PETIT, ROUGE if stock < 10 else CREME)
        dtxt, dcol = libelle_dlc(r, nom)
        texte(dtxt, (880, y + 4), T_PETIT, dcol)
    texte("Les boissons et desserts s'achètent tout faits (onglet Courses) et se revendent environ 3 fois leur prix. "
          "Sans stock, la formule n'est pas proposée.", (40, 540), T_PETIT, CREME_SOMBRE, max_w=1090)


def demander_vente(r):
    if ui.get("vente") is r:
        ui["vente"] = None
        jeu.vendre_local(r)
    else:
        ui["vente"] = r


def onglet_restos():
    panneau((20, 116, 1140, 520), "Restaurants et équipe")
    debut = page_debut("resto", len(LIEUX), 5)
    libre = not jeu.en_service()
    for i, lieu_ in enumerate(LIEUX[debut:debut + 5]):
        y = 154 + i * 90
        carte((30, y, 1120, 84))
        devanture(44, y + 14, 64, 50)
        r = next((x for x in jeu.restos if x["lieu"] is lieu_), None)
        w = texte(lieu_["nom"].upper(), (126, y + 5), T_TITRE, OR_CLAIR, max_w=240)
        texte(f"{lieu_['ville']}, {lieu_['pays']}", (126 + w + 12, y + 9), T_MINI, CREME_SOMBRE, max_w=200)
        if r:
            aff = jeu.affluence_prevue(r)
            texte(f"Réputation {r['rep']:.0f}  |  Affluence prévue {aff:.0f} %", (705, y + 9), T_MINI,
                  ROUGE if aff > 100 else CREME_SOMBRE, "d", max_w=270)
        if r:
            nb = len(r["employes"])
            equipe = ("vous + " if r["proprio"] else "") + f"{nb} employé{'s' if nb > 1 else ''}"
            if r["gestionnaire"]:
                equipe += " + gestionnaire de stock"
            texte(f"Équipe : {equipe}  |  Salle : {r['sieges']}/{jeu.places_max(r)} places", (126, y + 28), T_NORMAL,
                  max_w=570)
            texte(f"Local niveau {r['niveau']}  |  Loyer {eur(r['loyer'])}/mois  |  "
                  f"Salaire {eur(jeu.salaire(r))}/mois par employé", (126, y + 49), T_PETIT, CREME_SOMBRE, max_w=570)
            v = r["veille"]
            if v:
                partis = v["att"] + v["rup"] + v["salle"]
                texte(f"Hier : {v['servis']} servis, {partis} partis, CA {eur(v['ca'])}", (126, y + 66), T_MINI,
                      max_w=195)
            if r["concurrence"]:
                texte(f"Concurrence ({len(r['concurrence'])})", (330, y + 66), T_MINI, CONCURRENCE, max_w=95)
            if r["pret"]:
                pr = r["pret"]
                texte(f"Prêt : {eur(pr['mensualite'])}/mois, reste {eur(pr['capital'])} ({pr['mois']} mois)",
                      (430, y + 66), T_MINI, OR_CLAIR, max_w=275)
            mini = 0 if r["proprio"] else 1
            bouton((720, y + 4, 240, 24), f"Embaucher (+{eur(jeu.cout_embauche(r))} ce mois)",
                   libre and nb < jeu.employes_max(r), lambda r=r: jeu.embaucher(r))
            bouton((970, y + 4, 160, 24), f"Licencier (paie {eur(jeu.cout_licenciement(r))})",
                   libre and nb > mini, lambda r=r: jeu.licencier(r), "onglet")
            if r["sieges"] + PLACES_PAR_TRAVAUX <= jeu.places_max(r):
                cout = jeu.cout_agrandissement(r)
                bouton((720, y + 30, 410, 24), f"Agrandir la salle : +{PLACES_PAR_TRAVAUX} places ({eur(cout)})",
                       libre and jeu.caisse >= cout, lambda r=r: jeu.agrandir(r))
            elif jeu.peut_vendre(r):
                arme = ui.get("vente") is r
                label = ("Cliquer encore pour confirmer la vente" if arme else
                         f"Vendre le local : +{eur(jeu.net_vente(r))} nets (puis niveau {r['niveau'] + 1})")
                bouton((720, y + 30, 410, 24), label, True, lambda r=r: demander_vente(r), "principal")
            else:
                bouton((720, y + 30, 410, 24), "Salle et niveau au maximum", False, lambda: None)
            if r["gestionnaire"]:
                bouton((720, y + 56, 410, 24),
                       f"Gestionnaire en poste : licencier (paie "
                       f"{eur(jeu.prorata_depart(jeu.salaire_gestionnaire(r), r['gestionnaire']['depuis']))})",
                       libre, lambda r=r: jeu.licencier_gestionnaire(r), "onglet")
            else:
                bouton((720, y + 56, 410, 24),
                       f"Gestionnaire de stock : +{eur(jeu.prorata_embauche(jeu.salaire_gestionnaire(r)))} ce mois, "
                       f"puis {eur(jeu.salaire_gestionnaire(r))}/mois",
                       libre, lambda r=r: jeu.embaucher_gestionnaire(r))
        else:
            niveau = jeu.niveau_a_acheter(lieu_)
            prix = jeu.prix_local(lieu_)
            depart, maxi = sieges_niveau(lieu_["sieges"], niveau)
            texte(f"Local niveau {niveau}  |  {depart} places (jusqu'à {maxi})", (126, y + 28), T_PETIT, CREME,
                  max_w=380)
            texte(f"Fonds de commerce {eur(prix)}  |  Loyer {eur(jeu.loyer_niveau(lieu_, niveau))}/mois", (126, y + 48),
                  T_PETIT, CREME_SOMBRE, max_w=380)
            texte(f"Salaires x{lieu_['salaire']:.2f}  |  Prix locaux x{lieu_['niveau']:.2f}", (126, y + 66), T_MINI,
                  CREME_SOMBRE, max_w=380)
            if niveau == 1:
                for j, (label, test) in enumerate(lieu_["reqs"]):
                    ok = test(jeu)
                    texte(("[x] " if ok else "[ ] ") + label, (520, y + 8 + j * 20), T_PETIT,
                          VERT if ok else CREME_SOMBRE, max_w=340)
            else:
                texte(f"Local de niveau {niveau - 1} vendu :", (520, y + 8), T_PETIT, OR_CLAIR, max_w=340)
                texte("rachetez-en un plus grand, équipe et stock repris.", (520, y + 28), T_PETIT, OR_CLAIR,
                      max_w=340)
            bouton((880, y + 6, 250, 34), f"Acheter : {eur(prix)}", jeu.peut_ouvrir(lieu_, False),
                   lambda l=lieu_: jeu.ouvrir(l, False))
            bouton((880, y + 44, 250, 34), f"Financer : apport {eur(jeu.apport(lieu_))}", jeu.peut_ouvrir(lieu_, True),
                   lambda l=lieu_: jeu.ouvrir(l, True), "principal")
    pager("resto", len(LIEUX), 5, 590, 602)


def onglet_pub():
    panneau((20, 116, 1140, 520), "Publicité et finances")
    for i, pub in enumerate(PUBS):
        cout = jeu.cout_pub(pub)
        label = f"{pub['nom']} : {eur(cout)}  (+{pub['bonus'] * 100:.0f} %, {pub['jours']} j)"
        bouton((40, 156 + i * 36, 560, 32), label, jeu.caisse >= cout, lambda p=pub: jeu.acheter_pub(p),
               "principal" if pub.get("tv") else "normal")
    if jeu.pubs:
        texte("Actives : " + ", ".join(f"{p['nom']} ({p['jours']} j)" for p in jeu.pubs), (40, 376), T_PETIT, VERT,
              max_w=560)
    else:
        texte("Aucune publicité active", (40, 376), T_PETIT, CREME_SOMBRE)
    libre = not jeu.en_service()

    carte((620, 156, 510, 206))
    texte("RESPONSABLE COMMERCIAL", (640, 166), T_TITRE, OR_CLAIR, max_w=470)
    texte(f"Négocie les campagnes : -{REMISE_COMMERCIAL * 100:.0f} % sur toutes les pubs.", (640, 198), T_PETIT,
          CREME, max_w=470)
    texte(f"Les fait mieux rendre : +{BONUS_COMMERCIAL * 100:.0f} % de clients attirés.", (640, 220), T_PETIT, CREME,
          max_w=470)
    texte(f"Salaire : {eur(SALAIRE_COMMERCIAL)}/mois, au prorata des jours.", (640, 246), T_PETIT, CREME_SOMBRE,
          max_w=470)
    if jeu.commercial:
        texte("En poste.", (640, 272), T_PETIT, VERT)
        bouton((640, 316, 470, 32),
               f"Licencier (paie {eur(jeu.prorata_depart(SALAIRE_COMMERCIAL, jeu.commercial['depuis']))})",
               libre, jeu.licencier_commercial, "onglet")
    else:
        texte("Poste vacant.", (640, 272), T_PETIT, CREME_SOMBRE)
        bouton((640, 316, 470, 32), f"Embaucher (+{eur(jeu.prorata_embauche(SALAIRE_COMMERCIAL))} ce mois)",
               libre, jeu.embaucher_commercial)

    carte((620, 372, 510, 252))
    texte("COMPTABLE", (640, 382), T_TITRE, OR_CLAIR)
    texte(f"Honoraires : {eur(HONORAIRES_BASE)} + {eur(HONORAIRES_PAR_BOUTIQUE)} par boutique, soit "
          f"{eur(jeu.honoraires())}/mois.", (640, 414), T_PETIT, CREME, max_w=470)
    texte("Il établit la TVA et l'impôt : vous voyez les montants à venir, le", (640, 440), T_PETIT, CREME, max_w=470)
    texte("résultat net et les comptes (onglet Tableau de bord).", (640, 460), T_PETIT, CREME, max_w=470)
    texte(f"Sans comptable : +{PENALITE_SANS_COMPTABLE:.0%} de pénalités sur la TVA et l'impôt payés,",
          (640, 490), T_PETIT, OR_CLAIR, max_w=470)
    texte("et aucune visibilité sur ce que vous devez à l'État.", (640, 510), T_PETIT, OR_CLAIR, max_w=470)
    if jeu.comptable:
        texte("En poste.", (640, 540), T_PETIT, VERT)
        bouton((640, 578, 470, 32),
               f"Se séparer du comptable (paie {eur(jeu.prorata_depart(jeu.honoraires(), jeu.comptable['depuis']))})",
               libre, jeu.licencier_comptable, "onglet")
    else:
        texte("Pas de comptable.", (640, 540), T_PETIT, CREME_SOMBRE)
        bouton((640, 578, 470, 32), f"Engager (+{eur(jeu.prorata_embauche(jeu.honoraires()))} ce mois)",
               libre, jeu.embaucher_comptable)

    e = premier_mois_suivant(jeu.date)
    salaires, loyers, prets = jeu.charges_mensuelles()
    m = jeu.mois
    texte("FINANCES", (40, 408), T_TITRE, OR_CLAIR)
    pygame.draw.line(screen, OR_SOMBRE, (40, 436), (560, 436), 1)
    texte(f"Prochaine échéance le {e.day} {MOIS[e.month - 1]} :", (40, 446), T_NORMAL, max_w=560)
    texte(f"salaires et honoraires {eur(salaires)}, loyers {eur(loyers)}, prêts {eur(prets)}", (40, 470), T_PETIT,
          max_w=560)
    texte(f"Ce mois : CA HT {eur(m['ca_ht'])}, achats HT {eur(m['achats_ht'])}, pertes {eur(m['pertes'])}", (40, 494),
          T_PETIT, max_w=560)
    h = jeu.historique[-1] if jeu.historique else None
    if jeu.comptable:
        tva = max(0.0, m["tva_coll"] - m["tva_deduc"] - jeu.tva_credit)
        texte(f"TVA estimée {eur(tva)}  |  impôts payés cette année {eur(sum(jeu.is_paye.values()))}", (40, 518),
              T_PETIT, max_w=560)
        if h:
            texte(f"{h['label']} : avant impôt {eur(h['avant_is'])}, TVA {eur(h['tva_payee'])}, impôts {eur(h['is'])}",
                  (40, 542), T_PETIT, max_w=560)
            texte(f"Résultat net : {eur(h['net'])}", (40, 572), T_TITRE_G, VERT if h["net"] >= 0 else ROUGE)
    else:
        texte("Sans comptable : TVA et impôts invisibles, +15 % de pénalités.", (40, 518), T_PETIT, OR_CLAIR, max_w=560)
        if h:
            texte(f"{h['label']} : CA HT {eur(h['mois']['ca_ht'])}, marge brute "
                  f"{eur(h['mois']['ca_ht'] - h['mois']['cogs'])}", (40, 542), T_PETIT, max_w=560)
            texte(f"Pénalités payées : {eur(h['penalites'])}", (40, 572), T_TITRE_G,
                  ROUGE if h["penalites"] > 0 else CREME_SOMBRE)
    texte("TVA et impôts : taux réels en France, ordres de grandeur ailleurs.", (40, 604), T_MINI, CREME_SOMBRE,
          max_w=560)


def pct(a, b):
    return f"{100 * a / b:.0f} %" if b else "-"


def evol(actuel, precedent):
    if not precedent:
        return "-"
    return f"{100 * (actuel - precedent) / abs(precedent):+.0f} %"


def dash_ensemble():
    m = jeu.mois
    partis = m["att"] + m["rup"] + m["salle"]
    h = jeu.historique[-1] if jeu.historique else None
    cartes1 = [
        ("CA HT (en cours)", eur(m["ca_ht"]), CREME, None),
        ("Marge brute", pct(m["ca_ht"] - m["cogs"], m["ca_ht"]), CREME, f"{eur(m['ca_ht'] - m['cogs'])}"),
        ("Clients servis", f"{m['servis']}", CREME, None),
        ("Ticket moyen TTC", eur(m["ca_ttc"] / m["servis"], 2) if m["servis"] else "-", CREME, None),
        ("Clients partis", pct(partis, m["servis"] + partis), ROUGE if partis > 0.1 * max(1, m["servis"]) else CREME,
         f"attente {m['att']}, rupture {m['rup']}"),
        ("Formules", pct(m["formules"], m["servis"]), CREME, f"{m['formules']} vendues"),
    ]
    tva = max(0.0, m["tva_coll"] - m["tva_deduc"] - jeu.tva_credit)
    cartes2 = [
        ("Résultat net (mois préc.)", eur(h["net"]) if h else "-", (VERT if h["net"] >= 0 else ROUGE) if h else CREME,
         h["label"] if h else "après un mois complet"),
        ("Trésorerie", eur(jeu.caisse), VERT if jeu.caisse >= 0 else ROUGE, None),
        ("Réputation", f"{jeu.rep:.0f}/100", CREME, None),
        ("TVA à reverser", eur(tva), CREME, "estimation du mois"),
        ("Pertes péremption", eur(m["pertes"]), ROUGE if m["pertes"] > 0 else CREME, "ce mois"),
        ("Boutiques", f"{len(jeu.restos)}", CREME, f"{sum(len(r['employes']) for r in jeu.restos)} employés"),
    ]
    if not jeu.comptable:
        cartes2[0] = ("Résultat net", "Comptable requis", CREME_SOMBRE, "onglet Finances")
        cartes2[3] = ("TVA à reverser", "Comptable requis", CREME_SOMBRE, "onglet Finances")
    cartes2[2] = ("Réputation marque", f"{jeu.rep:.0f}/100", CREME, "moyenne des boutiques")
    for i, (t, v, c, st) in enumerate(cartes1):
        carte_kpi(40 + i * 182, 190, 170, 72, t, v, c, st)
    for i, (t, v, c, st) in enumerate(cartes2):
        carte_kpi(40 + i * 182, 270, 170, 72, t, v, c, st)
    hist = jeu.historique[-11:]
    labels = [x["label"] for x in hist] + ["en cours"]
    ca = [x["mois"]["ca_ht"] for x in hist] + [m["ca_ht"]]
    marge = [x["mois"]["ca_ht"] - x["mois"]["cogs"] for x in hist] + [m["ca_ht"] - m["cogs"]]
    graphique((40, 348, 545, 280), "Chiffre d'affaires HT et marge brute par mois", labels, ca, marge, "CA HT",
              "Marge brute")
    if jeu.comptable:
        graphique((605, 348, 525, 280), "Résultat net par mois", [x["label"] for x in hist],
                  [x["net"] for x in hist], None, "Résultat net")
    else:
        cadre((605, 348, 525, 280), CARTE_FOND, OR_SOMBRE, 8, 1, False)
        texte("Résultat net par mois", (617, 356), T_PETIT, OR_CLAIR)
        texte("Engagez un comptable (onglet Finances)", (867, 480), T_NORMAL, CREME_SOMBRE, "c", max_w=480)
        texte("pour établir les comptes et l'impôt.", (867, 508), T_NORMAL, CREME_SOMBRE, "c", max_w=480)


def dash_sandwichs():
    m = jeu.mois_sand
    prec = jeu.historique[-1]["sand"] if jeu.historique else {}
    veille = jeu.date - datetime.timedelta(days=jeu.date.day)
    ech = (jeu.date.day - 1) / jours_du_mois(veille)           # part du mois précédent déjà écoulée ce mois-ci
    for titre, x in (("SANDWICH", 150), ("VENTES", 330), ("VS MÊME PÉRIODE", 410), ("CA HT", 530), ("COÛT PRODUITS", 620),
                     ("MARGE BRUTE", 760), ("MARGE %", 880), ("NOTE", 960), ("PREMIUM", 1030)):
        texte(titre, (x, 194), T_MINI, OR)
    pygame.draw.line(screen, OR_SOMBRE, (40, 212), (1120, 212), 1)
    total_v = sum(v["ventes"] for v in m.values())
    for i, mn in enumerate(jeu.menu):
        nom = mn["rec"]["nom"]
        y = 218 + i * 58
        carte((40, y, 1090, 54))
        if mn["etat"] == "verrouille":
            texte(f"{nom} : pas encore développé", (150, y + 17), T_PETIT, CREME_SOMBRE)
            continue
        img = image_sandwich(nom, 84)
        screen.blit(img, (46, y + 4))
        v = m.get(nom, {"ventes": 0, "ca_ht": 0.0, "cogs": 0.0})
        mb = v["ca_ht"] - v["cogs"]
        texte(nom, (150, y + 16), T_NORMAL, max_w=170)
        texte(f"{v['ventes']}", (330, y + 16), T_NORMAL)
        pygame.draw.rect(screen, OR_SOMBRE, (330, y + 42, 70, 5))
        if total_v:
            pygame.draw.rect(screen, OR_CLAIR, (330, y + 42, int(70 * v["ventes"] / total_v), 5))
        texte(evol(v["ventes"], prec.get(nom, {}).get("ventes", 0) * ech), (410, y + 17), T_PETIT, CREME_SOMBRE)
        texte(eur(v["ca_ht"]), (530, y + 17), T_PETIT)
        texte(eur(v["cogs"]), (620, y + 17), T_PETIT)
        texte(eur(mb), (760, y + 17), T_PETIT, VERT if mb >= 0 else ROUGE)
        texte(pct(mb, v["ca_ht"]), (880, y + 17), T_PETIT)
        texte(f"{jeu.note_recette(mn):.1f}/5" if mn["ventes"] >= 25 else "?", (960, y + 17), T_PETIT, OR_CLAIR)
        texte(f"{jeu.etoiles_recette(mn)}", (1030, y + 17), T_PETIT)
    mo = jeu.mois
    texte(f"Formules : {mo['formules']} vendues, {eur(mo['extras_ht'])} HT de boissons et desserts.", (44, 516),
          T_NORMAL, OR_CLAIR, max_w=1080)
    boissons = ", ".join(f"{n} {jeu.mois_extras.get(n, 0)}" for n, _ in BOISSONS)
    desserts = ", ".join(f"{n} {jeu.mois_extras.get(n, 0)}" for n, _ in DESSERTS)
    texte("Boissons : " + boissons, (44, 546), T_PETIT, CREME_SOMBRE, max_w=1080)
    texte("Desserts : " + desserts, (44, 570), T_PETIT, CREME_SOMBRE, max_w=1080)
    texte("Données du mois en cours, comparées à la même période du mois précédent.", (44, 598), T_MINI, CREME_SOMBRE)


def dash_boutiques():
    for titre, x in (("BOUTIQUE", 44), ("CA HT", 330), ("CLIENTS", 430), ("PARTIS", 520), ("MARGE BRUTE", 610),
                     ("MARGE %", 740), ("TICKET MOYEN", 830), ("PRIX LOC.", 935), ("CONCURRENCE", 1015)):
        texte(titre, (x, 194), T_MINI, OR, max_w=100)
    pygame.draw.line(screen, OR_SOMBRE, (40, 212), (1120, 212), 1)
    lignes = []
    for r in jeu.restos:
        f = jeu.mois_resto.get(cle_lieu(r["lieu"]), {"servis": 0, "partis": 0, "ca_ht": 0.0, "cogs": 0.0, "ttc": 0.0})
        lignes.append((r, f))
    lignes.sort(key=lambda x: -x[1]["ca_ht"])
    debut = page_debut("dash_b", len(lignes), 7)
    for i, (r, f) in enumerate(lignes[debut:debut + 7]):
        y = 220 + i * 48
        carte((40, y, 1090, 44))
        mb = f["ca_ht"] - f["cogs"]
        texte(f"{r['lieu']['nom']} ({r['lieu']['ville']})", (50, y + 12), T_NORMAL, max_w=270)
        texte(eur(f["ca_ht"]), (330, y + 12), T_PETIT)
        texte(f"{f['servis']}", (430, y + 12), T_PETIT)
        texte(pct(f["partis"], f["servis"] + f["partis"]), (520, y + 12), T_PETIT,
              ROUGE if f["partis"] > 0.15 * max(1, f["servis"]) else CREME)
        texte(eur(mb), (610, y + 12), T_PETIT, VERT if mb >= 0 else ROUGE)
        texte(pct(mb, f["ca_ht"]), (740, y + 12), T_PETIT)
        texte(eur(f["ttc"] / f["servis"], 2) if f["servis"] else "-", (830, y + 12), T_PETIT)
        texte(f"x{r['lieu']['niveau']:.2f}", (935, y + 12), T_PETIT, CREME_SOMBRE)
        texte(f"{len(r['concurrence'])} actif(s)" if r["concurrence"] else "-", (1015, y + 12), T_PETIT,
              CONCURRENCE if r["concurrence"] else CREME_SOMBRE)
    pager("dash_b", len(lignes), 7, 590, 582)


def dash_finances():
    if not jeu.comptable:
        texte("Il faut un comptable en poste pour établir les comptes et l'impôt.", (44, 230), T_TITRE, OR_CLAIR)
        texte("Engagez-en un dans l'onglet Finances : sans lui, la TVA et l'impôt sont majorés de 15 %.", (44, 270),
              T_NORMAL, CREME, max_w=1080)
        return
    hist = jeu.historique[-5:]
    colonnes = [(x["label"], x["mois"], x) for x in hist] + [("en cours", jeu.mois, None)]
    lignes = [
        ("Chiffre d'affaires HT", lambda c, h: c["ca_ht"], False),
        ("Coût des produits vendus", lambda c, h: -c["cogs"], False),
        ("Marge brute", lambda c, h: c["ca_ht"] - c["cogs"], True),
        ("Pertes (péremption)", lambda c, h: -c["pertes"], False),
        ("Salaires", lambda c, h: -c["salaires"], False),
        ("Loyers", lambda c, h: -c["loyers"], False),
        ("Intérêts des prêts", lambda c, h: -c["interets"], False),
        ("Pubs et recettes", lambda c, h: -c["autres"], False),
        ("Taxes locales", lambda c, h: -c["locales"], False),
        ("Honoraires du comptable", lambda c, h: -c["honoraires"], False),
        ("Résultat avant impôt", lambda c, h: h["avant_is"] if h else None, True),
        ("Impôt sur les bénéfices", lambda c, h: -h["is"] if h else None, False),
        ("Pénalités fiscales", lambda c, h: -h["penalites"] if h else None, False),
        ("Résultat net", lambda c, h: h["net"] if h else None, True),
        ("TVA reversée", lambda c, h: -h["tva_payee"] if h else None, False),
        ("Trésorerie fin de mois", lambda c, h: h["caisse"] if h else None, False),
    ]
    for k, (label, _c, _h) in enumerate(colonnes):
        texte(label.upper(), (300 + k * 140 + 130, 194), T_MINI, OR, "d")
    pygame.draw.line(screen, OR_SOMBRE, (40, 212), (1120, 212), 1)
    for i, (nom, fonction, gras) in enumerate(lignes):
        y = 216 + i * 22
        if gras:
            pygame.draw.rect(screen, (30, 42, 72), (36, y - 2, 1090, 21), border_radius=4)
        texte(nom, (46, y), T_PETIT, OR_CLAIR if gras else CREME)
        for k, (_label, c, h) in enumerate(colonnes):
            v = fonction(c, h)
            if v is None or (h is None and nom in ("Salaires", "Loyers", "Intérêts des prêts", "Taxes locales", "Honoraires du comptable")
                             and v == 0):
                txt, col = "-", CREME_SOMBRE
            else:
                txt, col = eur(v), (ROUGE if v < 0 and gras else CREME)
            texte(txt, (300 + k * 140 + 130, y), T_PETIT, col, "d")
    if jeu.is_paye:
        details = ", ".join(f"{p} {eur(v)}" for p, v in jeu.is_paye.items())
        texte("Impôt sur les bénéfices payé depuis janvier : " + details, (44, 580), T_PETIT, CREME_SOMBRE, max_w=1080)
    texte("Colonne « en cours » : salaires, loyers, prêts, TVA et impôts ne sont comptés qu'à la fin du mois.", (44, 604),
          T_MINI, CREME_SOMBRE, max_w=1080)


def ecran_developpeur(demande):
    if demande == "dev":
        texte("Un développeur freelance construit chaque tableau de bord sur commande, puis le livre.", (44, 192),
              T_NORMAL, CREME, max_w=1080)
    else:
        texte("Ce tableau de bord n'existe pas encore : faites appel à un développeur.", (44, 192), T_NORMAL,
              OR_CLAIR, max_w=1080)
    descriptions = {
        "ensemble": ("12 indicateurs du mois et des graphiques par mois :", "chiffre d'affaires, marge, clients, trésorerie."),
        "sandwichs": ("Ventes, marges, notes, étoiles premium et formules", "de chaque recette, avec évolution."),
        "boutiques": ("Clients, départs, marge et prix de chaque boutique,", "classés par chiffre d'affaires."),
        "finances": ("Compte de résultat mensuel, TVA, impôts et pénalités.", "Demande aussi un comptable en poste."),
    }
    for i, (cle, titre, cout, jours) in enumerate(MODULES_DASH):
        x = 40 + (i % 2) * 558
        y = 224 + (i // 2) * 200
        cadre((x, y, 540, 186), CARTE_FOND, OR_CLAIR if cle == demande else OR_SOMBRE, 8, 2 if cle == demande else 1, False)
        texte(titre.upper(), (x + 16, y + 10), T_TITRE, OR_CLAIR)
        texte(descriptions[cle][0], (x + 16, y + 46), T_PETIT, CREME, max_w=508)
        texte(descriptions[cle][1], (x + 16, y + 68), T_PETIT, CREME, max_w=508)
        texte(f"{eur(cout)}  |  livraison sous {jours} jours", (x + 16, y + 96), T_PETIT, CREME_SOMBRE, max_w=508)
        if jeu.module_ok(cle):
            texte("Livré : disponible dans l'onglet correspondant.", (x + 16, y + 124), T_PETIT, VERT, max_w=508)
        elif jeu.module_attente(cle):
            d = jeu.modules[cle]
            texte(f"En développement : livraison le {d.day} {MOIS[d.month - 1]}.", (x + 16, y + 124), T_PETIT,
                  OR_CLAIR, max_w=508)
        else:
            bouton((x + 16, y + 134, 508, 36), f"Commander : {eur(cout)}",
                   jeu.caisse >= cout and not jeu.en_service(), lambda c=cle: jeu.commander_module(c), "principal",
                   T_GRAS)


def onglet_dashboard():
    panneau((20, 116, 1140, 520), "Tableau de bord")
    vues = [("ensemble", "Vue d'ensemble"), ("sandwichs", "Sandwichs"), ("boutiques", "Boutiques"),
            ("finances", "Comptes et impôts"), ("dev", "Développeur")]
    for i, (cle, titre) in enumerate(vues):
        verrou = cle != "dev" and not jeu.module_ok(cle)
        bouton((40 + i * 212, 152, 206, 28), titre + (" (verrouillé)" if verrou else ""), True,
               lambda c=cle: ui.__setitem__("dash_vue", c), "onglet_actif" if ui["dash_vue"] == cle else "onglet")
    vue = ui["dash_vue"]
    if vue == "dev" or not jeu.module_ok(vue):
        ecran_developpeur(vue)
        return
    {"ensemble": dash_ensemble, "sandwichs": dash_sandwichs, "boutiques": dash_boutiques,
     "finances": dash_finances}[vue]()


def onglet_bilan():
    panneau((20, 116, 1140, 520), "Bilan de la journée")
    total = sum(r["jour"]["ca"] for r in jeu.restos)
    att = sum(r["jour"]["att"] for r in jeu.restos)
    rup = sum(r["jour"]["rup"] for r in jeu.restos)

    texte("VENTES PAR SANDWICH", (44, 160), T_TITRE, OR)
    pygame.draw.line(screen, OR_SOMBRE, (44, 188), (560, 188), 1)
    y = 196
    for mn in jeu.menu:
        if mn["etat"] != "verrouille":
            img = image_sandwich(mn["rec"]["nom"], 92)
            screen.blit(img, (50, y))
            texte(mn["rec"]["nom"], (160, y + 14), T_NORMAL, max_w=240)
            texte(f"{mn['ventes_jour']} vendus", (430, y + 14), T_GRAS, OR_CLAIR)
            y += 50
    texte(f"Chiffre d'affaires du jour : {eur(total)}", (44, 466), T_TITRE_G, OR_CLAIR, max_w=520)
    ty = 508
    if att > 5:
        texte("Trop de clients sont partis à cause de l'attente :", (44, ty), T_PETIT, OR_CLAIR, max_w=520)
        texte("embauche, ou ralentis la demande avec un prix plus haut.", (44, ty + 20), T_PETIT, OR_CLAIR, max_w=520)
        ty += 50
    if rup > 0:
        texte("Des clients sont partis faute de stock :", (44, ty), T_PETIT, OR_CLAIR, max_w=520)
        texte("commande plus, le matin, avant le premier service.", (44, ty + 20), T_PETIT, OR_CLAIR, max_w=520)

    texte("PAR BOUTIQUE", (600, 160), T_TITRE, OR)
    pygame.draw.line(screen, OR_SOMBRE, (600, 188), (1130, 188), 1)
    debut = page_debut("bilan", len(jeu.restos), 7)
    for i, r in enumerate(jeu.restos[debut:debut + 7]):
        yy = 198 + i * 48
        s = r["jour"]
        texte(f"{r['lieu']['nom']} : {s['servis']} servis  |  CA {eur(s['ca'])}", (600, yy), T_NORMAL, max_w=530)
        texte(f"partis : attente {s['att']}, rupture {s['rup']}, salle pleine {s['salle']}", (600, yy + 22),
              T_MINI, CREME_SOMBRE, max_w=530)
    pager("bilan", len(jeu.restos), 7, 865, 540)


ONGLETS = [("courses", "Courses", onglet_courses), ("menu", "Menu", onglet_menu),
           ("resto", "Restaurants", onglet_restos), ("pub", "Finances", onglet_pub),
           ("bilan", "Bilan", onglet_bilan), ("dash", "Tableau de bord", onglet_dashboard)]


def dessiner_preparation():
    for i, (cle, titre, _f) in enumerate(ONGLETS):
        bouton((20 + i * 146, 78, 140, 34), titre.upper(), True, lambda c=cle: setattr(jeu, "onglet", c),
               "onglet_actif" if jeu.onglet == cle else "onglet")
    libelles = {"prep_midi": "Ouvrir le service du midi", "prep_soir": "Ouvrir le service du soir",
                "bilan": "Jour suivant", "ferme": "Passer au lundi"}
    bouton((LARGEUR - 20 - 260, 76, 260, 38), libelles[jeu.phase] + " (Espace)", not jeu.fini,
           jeu.action_principale, "principal", T_GRAS)
    for cle, _t, fonction in ONGLETS:
        if jeu.onglet == cle:
            fonction()


def dessiner_journal():
    cadre((20, 644, 1140, 88), PANNEAU_FOND, OR_SOMBRE, 10, 1, False)
    n = len(jeu.journal)
    for i, ligne in enumerate(jeu.journal):
        texte(ligne, (36, 652 + i * 20), T_PETIT, CREME if i == n - 1 else CREME_SOMBRE, max_w=1100)


def dessiner():
    boutons.clear()
    if ui["ecran"] == "titre":
        dessiner_titre()
        return
    screen.blit(FOND_SURF, (0, 0))
    dessiner_entete()
    if jeu.en_service():
        dessiner_service()
    else:
        dessiner_preparation()
    dessiner_journal()
    if jeu.fini:
        poly_alpha(screen, (0, 0, 0, 170), [(0, 0), (LARGEUR, 0), (LARGEUR, HAUTEUR), (0, HAUTEUR)])
        texte("FAILLITE", (LARGEUR // 2, HAUTEUR // 2 - 30), T_GRAND, ROUGE, "c")
        texte("Appuie sur R pour recommencer", (LARGEUR // 2, HAUTEUR // 2 + 20), T_TITRE, CREME, "c")
    if ui["ecran"] == "menu":
        boutons.clear()
        dessiner_menu_pause()


# ---------------------------------------------------------------- BOUCLE

async def main():
    global jeu, AUTOSAVE
    init_ecran()
    jeu = Jeu()
    AUTOSAVE = True
    ui["ecran"] = "titre" if (lire_meta("partie") or lire_meta("auto")) else "jeu"
    accum = 0.0
    running = True
    while running:
        dt = clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if ui["ecran"] == "jeu":
                        ui["ecran"] = "menu"
                    elif ui["ecran"] == "menu":
                        action_ecran("jeu")
                elif ui["ecran"] == "jeu":
                    if event.key == pygame.K_SPACE:
                        jeu.espace()
                    elif event.key == pygame.K_r and jeu.fini:
                        jeu = Jeu()
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                        jeu.regler_vitesse(VITESSES[event.key - pygame.K_1])
            elif event.type == pygame.MOUSEWHEEL:
                if ui["ecran"] == "jeu":
                    molette(-event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, action, actif in boutons:
                    if actif and rect.collidepoint(event.pos):
                        action()
                        break
        if ui["quitter"]:
            running = False

        # 1 minute de jeu = 1 seconde réelle à vitesse x1
        if ui["ecran"] == "jeu" and jeu.en_service() and not jeu.pause and not jeu.fini:
            accum += dt
            pas = 1000 / jeu.vitesse
            n = 0
            while accum >= pas and n < 40 and jeu.en_service():
                accum -= pas
                jeu.tick()
                n += 1
        else:
            accum = 0.0

        dessiner()
        pygame.display.flip()
        # Indispensable pour laisser le navigateur traiter l'affichage et les interactions.
        await asyncio.sleep(0)

    if ui["ecran"] != "titre" and jeu.date > DATE_DEBUT and not jeu.en_service() and not jeu.fini:
        try:
            ecrire_sauvegarde(jeu, "auto")
        except Exception:
            pass
    # Ne pas appeler pygame.quit() ici : le runtime navigateur gère la fermeture.


if __name__ == "__main__":
    asyncio.run(main())
