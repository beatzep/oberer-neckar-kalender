#!/usr/bin/env python3
"""Holt Spielplan und Tabelle der Herren-Bezirksoberliga-Mannschaft der HSG
Oberer Neckar von handball4all (Baden-Wuerttembergischer Handball-Verband)
und schreibt sie normalisiert nach daten.json.

Anders als handball.net hat handball4all keine dokumentierte API - das hier
ist der Endpunkt, den die offizielle Seite selbst benutzt
(https://www.handball4all.de/.../#/league?ogId=216&lId=167291&tId=1503051).
Liga- und Team-ID stehen fest, weil eine Bezirksoberliga-Staffel nicht mitten
in der Saison die ID wechselt - zur naechsten Saison muessen sie neu gesucht
werden (ueber den Link "Kalender abonnieren" auf der handball4all-Seite).
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://spo.handball4all.de/service/if_g_json.php"
ORG_ID = 216       # Baden-Wuerttembergischer HV
LIGA_ID = 167291   # Maenner Bezirksoberliga Stuttgart-Rems-Murr, Saison 26/27
TEAM_ID = 1503051  # HSG Oberer Neckar


def hole(og: int, cl: int, ct: int) -> dict:
    url = f"{API}?ca=0&cl={cl}&cmd=ps&ct={ct}&do={date.today():%Y-%m-%d}&og={og}"
    anfrage = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(anfrage, timeout=20) as antwort:
        rohdaten = json.load(antwort)
    if not rohdaten or not isinstance(rohdaten, list):
        raise RuntimeError("handball4all hat eine leere oder unerwartete Antwort geliefert")
    return rohdaten[0]


def parse_termin(g: dict) -> tuple[str, bool]:
    """Gibt (ISO-Datum/-Zeit, ob_uhrzeit_bekannt) zurueck.
    handball4all traegt fuer noch nicht angesetzte Spiele eine Leerzeit ein -
    dann wird daraus ein ganztaegiger Termin statt Mitternacht."""
    tag = datetime.strptime(g["gDate"], "%d.%m.%y").date()
    zeit = (g.get("gTime") or "").strip()
    if not zeit or zeit == "offen":
        return tag.isoformat(), False
    stunde, minute = zeit.split(":")
    beginn = datetime(tag.year, tag.month, tag.day, int(stunde), int(minute))
    return beginn.isoformat(), True


def tor_wert(text: str) -> int | None:
    text = (text or "").strip()
    return int(text) if text.isdigit() else None


def normalisiere_spiele(games: list[dict]) -> list[dict]:
    spiele = []
    for g in games:
        termin, uhrzeit_bekannt = parse_termin(g)
        halle_teile = [g.get("gGymnasiumName", "").strip(),
                       g.get("gGymnasiumStreet", "").strip(),
                       f"{g.get('gGymnasiumPostal','').strip()} {g.get('gGymnasiumTown','').strip()}".strip()]
        spiele.append({
            "id": g["gID"],
            "nummer": g.get("gNo", ""),
            "termin": termin,
            "uhrzeit_bekannt": uhrzeit_bekannt,
            "heim": g.get("gHomeTeam", "").strip(),
            "gast": g.get("gGuestTeam", "").strip(),
            "tore_heim": tor_wert(g.get("gHomeGoals")),
            "tore_gast": tor_wert(g.get("gGuestGoals")),
            "halle": ", ".join(t for t in halle_teile if t),
            "schiedsrichter": (g.get("gReferee") or "").strip(),
        })
    spiele.sort(key=lambda s: s["termin"])
    return spiele


def normalisiere_tabelle(score: list[dict]) -> list[dict]:
    tabelle = []
    for i, s in enumerate(score, start=1):
        tabelle.append({
            "platz": s.get("tabScore") or None,
            "team": s.get("tabTeamname", "").strip(),
            "spiele": s.get("numPlayedGames", 0),
            "siege": s.get("numWonGames", 0),
            "unentschieden": s.get("numEqualGames", 0),
            "niederlagen": s.get("numLostGames", 0),
            "tore_geschossen": s.get("numGoalsShot", 0),
            "tore_erhalten": s.get("numGoalsGot", 0),
            "punkte_plus": s.get("pointsPlus", 0),
            "punkte_minus": s.get("pointsMinus", 0),
        })
    return tabelle


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default="daten.json")
    cfg = p.parse_args()

    d = hole(ORG_ID, LIGA_ID, TEAM_ID)
    if d.get("error"):
        sys.exit(f"handball4all meldet einen Fehler: {d['error']}")

    inhalt = d.get("content", {})
    spiele_roh = (inhalt.get("futureGames") or {}).get("games") or []
    if not spiele_roh:
        sys.exit("Keine Spiele in der Antwort von handball4all - Liga- oder "
                 "Team-ID pruefen, moeglicherweise hat die neue Saison neue IDs.")

    daten = {
        "verein": "HSG Oberer Neckar",
        "mannschaft": "Herren",
        "liga": d.get("head", {}).get("name", ""),
        "bereich": d.get("head", {}).get("headline1", ""),
        "quelle_stand": d.get("head", {}).get("actualized", ""),
        "geholt_am": datetime.now().isoformat(timespec="seconds"),
        "spiele": normalisiere_spiele(spiele_roh),
        "tabelle": normalisiere_tabelle(inhalt.get("score") or []),
    }

    Path(cfg.out).write_text(
        json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(daten['spiele'])} Spiele, {len(daten['tabelle'])} Tabellenplaetze -> {cfg.out}")


if __name__ == "__main__":
    main()
