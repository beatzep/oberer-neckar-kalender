"""Rechnet aus den Spielberichten (berichte.json, siehe spielberichte.py)
das, was die Seite zeigt: Spielverlauf, Torschuetzen, Siebenmeter,
Zeitstrafen, Laeufe - je Spiel und ueber die Saison. Kein Netzzugriff,
nur vorhandene Daten; Gegenstueck zu spielerstatistik.py im MuRu-Projekt.

Nichts schaetzen: wo Berichte fehlen, steht das in `quelle`, damit die
Seite es benennen kann, statt Zahlen aus halben Daten zu zeigen.
"""

from __future__ import annotations

HALBZEIT_SEKUNDE = 30 * 60
# Ab dieser Serie ohne Gegentor lohnt es, von einem Lauf zu sprechen.
LAUF_AB = 4


def bericht_zu(spiel: dict, berichte: dict) -> dict | None:
    """Der gepruefte Bericht zu einem Spiel, sonst None."""
    bid = spiel.get("bericht_id")
    bericht = berichte.get(bid) if bid else None
    return bericht if bericht and bericht.get("ereignisse") else None


def ist_tor(e: dict) -> bool:
    return e["art"] in ("tor", "siebenmeter")


def verlauf(bericht: dict, heim: bool) -> list[tuple[int, int, int]]:
    """Der Spielstand als (Sekunde, eigene, Gegner), beginnend bei 0:0."""
    punkte = [(0, 0, 0)]
    for e in bericht["ereignisse"]:
        if ist_tor(e):
            h, g = e["stand"]
            punkte.append((e["s"], h, g) if heim else (e["s"], g, h))
    return punkte


def laeufe(bericht: dict) -> dict:
    """Die laengste Serie ohne Gegentor auf beiden Seiten, samt Startminute."""
    bester = {"eigene": 0, "eigene_ab": None, "fremde": 0, "fremde_ab": None}
    reihe, start, wer = 0, None, None
    for e in bericht["ereignisse"]:
        if not ist_tor(e):
            continue
        if e["eigen"] == wer:
            reihe += 1
        else:
            wer, reihe, start = e["eigen"], 1, e["s"]
        feld = "eigene" if wer else "fremde"
        if reihe > bester[feld]:
            bester[feld], bester[feld + "_ab"] = reihe, start // 60 + 1
    return bester


def schuetzen(berichte: list[dict]) -> list[dict]:
    """Eigene Torschuetzen ueber einen oder mehrere Berichte.

    `spiele` zaehlt, in wie vielen Berichten der Spieler im Kader steht -
    nicht, in wie vielen er getroffen hat. Wer nur verteidigt hat, hat
    trotzdem gespielt.
    """
    gesammelt: dict[str, dict] = {}

    def eintrag(name: str) -> dict:
        return gesammelt.setdefault(name, {
            "name": name, "tore": 0, "siebenmeter_tore": 0, "siebenmeter_wuerfe": 0,
            "zeitstrafen": 0, "spiele": 0})

    for bericht in berichte:
        dabei = {k["name"] for k in bericht.get("kader") or []}
        for e in bericht["ereignisse"]:
            if not e["eigen"] or "name" not in e:
                continue
            dabei.add(e["name"])
            s = eintrag(e["name"])
            if ist_tor(e):
                s["tore"] += 1
            if e["art"] == "siebenmeter":
                s["siebenmeter_tore"] += 1
                s["siebenmeter_wuerfe"] += 1
            elif e["art"] == "siebenmeter_fehl":
                s["siebenmeter_wuerfe"] += 1
            elif e["art"] == "zeitstrafe":
                s["zeitstrafen"] += 1
        for name in dabei:
            eintrag(name)["spiele"] += 1

    liste = [s for s in gesammelt.values() if s["tore"] > 0]
    for s in liste:
        s["tore_je_spiel"] = round(s["tore"] / s["spiele"], 1) if s["spiele"] else 0.0
    liste.sort(key=lambda s: (-s["tore"], -s["tore_je_spiel"], s["name"]))
    return liste


def zaehle(berichte: list[dict], art: str, eigen: bool) -> int:
    return sum(1 for b in berichte for e in b["ereignisse"]
               if e["art"] == art and e["eigen"] == eigen)


def spiel_auswertung(spiel: dict, bericht: dict) -> dict:
    return {
        "verlauf": verlauf(bericht, spiel["heim"]),
        "laeufe": laeufe(bericht),
        "schuetzen": schuetzen([bericht]),
        "zeitstrafen": [zaehle([bericht], "zeitstrafe", True), zaehle([bericht], "zeitstrafe", False)],
        "disqualifikationen": [zaehle([bericht], "disqualifikation", True),
                               zaehle([bericht], "disqualifikation", False)],
        "siebenmeter": [zaehle([bericht], "siebenmeter", True),
                        zaehle([bericht], "siebenmeter", True) + zaehle([bericht], "siebenmeter_fehl", True)],
        "zuschauer": bericht.get("zuschauer"),
    }


def saison_auswertung(team: dict, berichte: dict) -> dict:
    gespielt = [s for s in team["spiele"] if s["tore_eigene"] is not None]
    mit = [(s, b) for s in gespielt if (b := bericht_zu(s, berichte))]
    liste = [b for _, b in mit]

    tore = [sum(s["tore_eigene"] for s in gespielt), sum(s["tore_gegner"] for s in gespielt)]
    mit_hz = [s for s in gespielt if s.get("halbzeit_eigene") is not None]
    halbzeiten = None
    if mit_hz:
        erste = sum(s["halbzeit_eigene"] - s["halbzeit_gegner"] for s in mit_hz)
        gesamt = sum(s["tore_eigene"] - s["tore_gegner"] for s in mit_hz)
        halbzeiten = {"spiele": len(mit_hz), "erste": erste, "zweite": gesamt - erste}

    sm_tore = zaehle(liste, "siebenmeter", True)
    sm_wuerfe = sm_tore + zaehle(liste, "siebenmeter_fehl", True)
    return {
        "quelle": {
            "gespielt": len(gespielt),
            "mit_bericht": len(mit),
            "ohne_bericht": [s for s in gespielt if not bericht_zu(s, berichte)],
        },
        "tore": tore,
        "halbzeiten": halbzeiten,
        "schuetzen": schuetzen(liste),
        "siebenmeter": [sm_tore, sm_wuerfe],
        "zeitstrafen": [zaehle(liste, "zeitstrafe", True), zaehle(liste, "zeitstrafe", False)],
    }
