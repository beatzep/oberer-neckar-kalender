#!/usr/bin/env python3
"""Holt Spielplan und Tabelle aller Mannschaften aus teams.json von
handball4all (Baden-Wuerttembergischer Handball-Verband) und schreibt sie
normalisiert nach daten.json.

Anders als handball.net hat handball4all keine dokumentierte API - das hier
ist der Endpunkt, den die offizielle Seite selbst benutzt
(https://www.handball4all.de/.../#/league?ogId=<og>&lId=<cl>&tId=<ct>).
Liga- und Team-IDs stehen in teams.json und wechseln vermutlich mit jeder
neuen Saison - dann auf der handball4all-Seite ueber "Kalender abonnieren"
neu nachsehen (Rechtsklick auf den iCal-Link, URL kopieren, cl/ct/og
rauslesen) und in teams.json eintragen.

Erkennt ausserdem Aenderungen gegenueber dem vorherigen Lauf (Verlegung,
neues Spiel, abgesetztes Spiel) - wie im MuRu-Projekt (spielplan2ics.py,
erkenne_aenderungen), nur pro Mannschaft statt global."""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://spo.handball4all.de/service/if_g_json.php"
TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def kurzdatum(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    return f"{TAGE[d.weekday()]} {d:%d.%m.%y}"


def mit_uhrzeit(iso: str, uhrzeit_bekannt: bool) -> str:
    """Fuer Aenderungstexte: reine Verlegungen der Anwurfzeit am selben Tag
    fallen unter kurzdatum() sonst unter den Tisch, weil das nur das Datum
    zeigt."""
    d = datetime.fromisoformat(iso)
    return f"{kurzdatum(iso)}, {d:%H:%M} Uhr" if uhrzeit_bekannt else kurzdatum(iso)


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


def normalisiere_spiele(games: list[dict], name_in_quelle: str, alt: dict) -> tuple[list[dict], list[dict]]:
    spiele = []
    aenderungen = []
    erstlauf = not alt

    for g in games:
        heim = g.get("gHomeTeam", "").strip() == name_in_quelle
        gegner = (g.get("gGuestTeam") if heim else g.get("gHomeTeam") or "").strip()
        termin, uhrzeit_bekannt = parse_termin(g)
        halle_teile = [g.get("gGymnasiumName", "").strip(),
                       g.get("gGymnasiumStreet", "").strip(),
                       f"{g.get('gGymnasiumPostal','').strip()} {g.get('gGymnasiumTown','').strip()}".strip()]
        halle = ", ".join(t for t in halle_teile if t)
        nummer = g.get("gNo", "") or g["gID"]
        vorher = alt.get(nummer)

        spiel = {
            "id": g["gID"],
            "nummer": nummer,
            "termin": termin,
            "uhrzeit_bekannt": uhrzeit_bekannt,
            "heim": heim,
            "gegner": gegner,
            "tore_eigene": None,
            "tore_gegner": None,
            "halle": halle,
            "schiedsrichter": (g.get("gReferee") or "").strip(),
            "sequence": (vorher or {}).get("sequence", 0),
        }
        th, tg = tor_wert(g.get("gHomeGoals")), tor_wert(g.get("gGuestGoals"))
        if th is not None and tg is not None:
            spiel["tore_eigene"], spiel["tore_gegner"] = (th, tg) if heim else (tg, th)

        if vorher is None:
            if not erstlauf:
                aenderungen.append(f"Neues Spiel gegen {gegner}: "
                                    f"{kurzdatum(termin)} in {halle or 'Halle noch offen'}")
        else:
            termin_neu = vorher.get("termin") != termin
            halle_neu = vorher.get("halle") != halle
            if termin_neu or halle_neu:
                spiel["sequence"] = vorher.get("sequence", 0) + 1
                teile = []
                if termin_neu:
                    teile.append(f"{mit_uhrzeit(vorher['termin'], vorher.get('uhrzeit_bekannt', True))} "
                                 f"→ {mit_uhrzeit(termin, uhrzeit_bekannt)}")
                if halle_neu:
                    teile.append(f"{vorher.get('halle') or '?'} → {halle or '?'}")
                aenderungen.append(f"Spiel gegen {gegner}: " + ", ".join(teile))

        spiele.append(spiel)

    neu_codes = {s["nummer"] for s in spiele}
    for nummer, vorher in alt.items():
        if nummer not in neu_codes:
            aenderungen.append(f"Spiel gegen {vorher.get('gegner','?')} am "
                                f"{mit_uhrzeit(vorher['termin'], vorher.get('uhrzeit_bekannt', True))} "
                                f"steht nicht mehr im Spielplan")

    spiele.sort(key=lambda s: s["termin"])
    return spiele, aenderungen


def normalisiere_tabelle(score: list[dict]) -> list[dict]:
    tabelle = []
    for s in score:
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
    p.add_argument("--teams", default="teams.json")
    p.add_argument("--out", default="daten.json")
    cfg = p.parse_args()

    konfig = json.loads(Path(cfg.teams).read_text(encoding="utf-8"))
    alt_gesamt = {}
    if Path(cfg.out).exists():
        alt_gesamt = json.loads(Path(cfg.out).read_text(encoding="utf-8")).get("teams", {})

    teams_neu = {}
    for team in konfig["teams"]:
        schluessel = team["schluessel"]
        d = hole(team["og"], team["cl"], team["ct"])
        if d.get("error"):
            sys.exit(f"handball4all meldet einen Fehler fuer {team['name']}: {d['error']}")

        inhalt = d.get("content", {})
        spiele_roh = (inhalt.get("futureGames") or {}).get("games") or []
        if not spiele_roh:
            sys.exit(f"Keine Spiele fuer {team['name']} - Liga- oder Team-ID in teams.json "
                     f"pruefen, moeglicherweise hat die neue Saison neue IDs.")

        alt_spiele = {s["nummer"]: s for s in
                      (alt_gesamt.get(schluessel) or {}).get("spiele", [])}
        spiele, aenderungen = normalisiere_spiele(spiele_roh, team["name_in_quelle"], alt_spiele)

        teams_neu[schluessel] = {
            "name": team["name"],
            "name_in_quelle": team["name_in_quelle"],
            "name_tabelle": team["name_tabelle"],
            "datei": team["datei"],
            "liga": d.get("head", {}).get("name", ""),
            "bereich": d.get("head", {}).get("headline1", ""),
            "quelle_stand": d.get("head", {}).get("actualized", ""),
            "spiele": spiele,
            "tabelle": normalisiere_tabelle(inhalt.get("score") or []),
            "aenderungen": aenderungen,
        }
        print(f"{team['name']}: {len(spiele)} Spiele"
              + (f", {len(aenderungen)} Aenderung(en)" if aenderungen else ""))

    daten = {
        "verein": konfig["verein"],
        "geholt_am": datetime.now().isoformat(timespec="seconds"),
        "teams": teams_neu,
    }
    Path(cfg.out).write_text(
        json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"-> {cfg.out}")


if __name__ == "__main__":
    main()
