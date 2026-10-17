#!/usr/bin/env python3
"""Prueft Parser (spielberichte.py) und Auswertung (auswertung.py) an einem
kleinen, nachgebauten Bericht - so wie pypdf die echten PDFs als Zeilen
liefert. Kein Netzzugriff.

    python3 test_spielberichte.py
"""

import auswertung
from spielberichte import BerichtFehler, lies_bericht

ZEILEN = """Presseinformation - lang
Endstand 3:2 (1:1) , Sieger HSG Oberer Neckar   Zuschauer: 42
Mannschaftslisten
Heim: HSG Oberer Neckar
Nr. Name Jahrgang M R Tore
1. 2. 3. Disq. Ber. zus.
7 Anna Beispiel 2 3/1 12:00
9 Berta Muster 1
12 Clara Ohnetor
A N.N. N.N.
Gast: TV Gegner
4 Doris Fremd 2
Handball4all AG Seite 2/4 Stand vom 17.10.2026, 13:48:20h
Spielverlauf
Zeit Spielzeit Spielstand Aktion
18:02:30 01:41 1:0 7m-Tor durch Anna Beispiel (7, HSG Ob. Neckar)
18:04:45 03:57 Verwarnung für Doris Fremd (4, TV Gegner)
18:05:18 12:00 2-min Strafe für Anna Beispiel (7, HSG Ob. Neckar)
18:06:00 20:10 1:1 Tor durch Doris Fremd (4, TV Gegner)
18:14:01 25:56 Auszeit TV Gegner
18:40:00 35:00 7m, KEIN Tor durch Anna Beispiel (7, HSG Ob. Neckar)
18:41:00 36:00 1:2 Tor durch Doris Fremd (4, TV Gegner)
18:50:00 45:00 2:2 Tor durch Anna Beispiel (7, HSG Ob. Neckar)
19:00:00 58:30 3:2 Tor durch Berta Muster (9, HSG Ob. Neckar)
19:01:00 59:00 Blaue Karte für Doris Fremd (4, TV Gegner)
""".splitlines()


def test_lesen():
    b = lies_bericht(ZEILEN, 3, 2, "heim")
    assert b["zuschauer"] == 42
    assert [k["name"] for k in b["kader"]] == ["Anna Beispiel", "Berta Muster", "Clara Ohnetor"]
    arten = [e["art"] for e in b["ereignisse"]]
    assert arten == ["siebenmeter", "verwarnung", "zeitstrafe", "tor", "auszeit",
                     "siebenmeter_fehl", "tor", "tor", "tor"], arten   # Blaue Karte uebergangen
    auszeit = b["ereignisse"][4]
    assert auszeit["eigen"] is False
    # Namen nur von den eigenen Leuten
    assert all("name" not in e for e in b["ereignisse"] if not e["eigen"])
    assert b["ereignisse"][0]["name"] == "Anna Beispiel"


def test_als_gast():
    b = lies_bericht(ZEILEN, 3, 2, "gast")
    assert [k["name"] for k in b["kader"]] == ["Doris Fremd"]
    assert all(not e["eigen"] for e in b["ereignisse"] if e.get("nr") == "7")


def test_falscher_endstand():
    try:
        lies_bericht(ZEILEN, 3, 3, "heim")
    except BerichtFehler as f:
        assert "Endstand" in str(f)
    else:
        raise AssertionError("falscher Endstand nicht erkannt")


def test_springender_stand():
    kaputt = [z.replace(" 2:2 ", " 3:2 ") for z in ZEILEN]
    try:
        lies_bericht(kaputt, 3, 2, "heim")
    except BerichtFehler as f:
        assert "springt" in str(f)
    else:
        raise AssertionError("springender Spielstand nicht erkannt")


def test_auswertung():
    b = lies_bericht(ZEILEN, 3, 2, "heim")
    spiel = {"heim": True, "bericht_id": "1", "tore_eigene": 3, "tore_gegner": 2,
             "halbzeit_eigene": 1, "halbzeit_gegner": 1, "termin": "2026-09-19T18:00:00",
             "gegner": "TV Gegner"}
    a = auswertung.spiel_auswertung(spiel, b)
    assert a["verlauf"] == [(0, 0, 0), (101, 1, 0), (1210, 1, 1), (2160, 1, 2),
                            (2700, 2, 2), (3510, 3, 2)]
    assert a["siebenmeter"] == [1, 2]
    assert a["zeitstrafen"] == [1, 0]
    assert a["laeufe"]["eigene"] == 2 and a["laeufe"]["eigene_ab"] == 46
    assert a["laeufe"]["fremde"] == 2 and a["laeufe"]["fremde_ab"] == 21
    anna, berta = a["schuetzen"]
    assert (anna["name"], anna["tore"], anna["siebenmeter_tore"], anna["siebenmeter_wuerfe"],
            anna["zeitstrafen"]) == ("Anna Beispiel", 2, 1, 2, 1)
    assert berta["tore"] == 1

    # Saison: zwei Spiele mit demselben Bericht, eins ohne
    team = {"spiele": [spiel, dict(spiel, bericht_id="2"), dict(spiel, bericht_id=None)]}
    s = auswertung.saison_auswertung(team, {"1": b, "2": b})
    assert s["quelle"]["gespielt"] == 3 and s["quelle"]["mit_bericht"] == 2
    assert s["schuetzen"][0]["spiele"] == 2 and s["schuetzen"][0]["tore"] == 4
    assert s["halbzeiten"] == {"spiele": 3, "erste": 0, "zweite": 3}


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"ok  {name}")
