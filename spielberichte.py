#!/usr/bin/env python3
"""Holt zu jedem gespielten Spiel den Spielbericht (PDF) von handball4all,
liest den Spielverlauf aus und bewahrt ihn in berichte.json auf.

handball4all liefert zu jedem Spiel mit hochgeladenem Bericht eine Kennung
(`sGID`, in daten.json als `bericht_id`). Darunter liegt ein PDF
("Presseinformation - lang") mit Mannschaftslisten und dem kompletten
Spielverlauf: jedes Tor mit Spielzeit, Schuetze und Zwischenstand, dazu
Siebenmeter, Verwarnungen, Zeitstrafen, Disqualifikationen und Auszeiten.
Das Gegenstueck zu `/matches/<id>/events` im MuRu-Projekt
(spielberichte.py) - nur eben als PDF statt als JSON.

Ausgelesen wird nur der Spielverlauf, nicht die Spalten der
Mannschaftsliste: der Verlauf steht zeilenweise und vollstaendig da, die
Spalten dagegen haengen an der Seitengeometrie. Aus der Mannschaftsliste
kommen nur die Namen des eigenen Kaders (fuer "wie viele Spiele").

**Nichts Halbes weitergeben.** Jeder Bericht wird gegen den Endstand aus
daten.json geprueft: jedes Tor muss den Stand um genau eins erhoehen, und
der letzte Stand muss der Endstand sein. Passt das nicht, wird der Bericht
verworfen und bei spaeteren Laeufen erneut versucht (hoechstens
VERSUCHE_HOECHSTENS-mal) - lieber kein Spielverlauf als ein falscher.

**Namen nur von den eigenen Leuten.** Gespeichert werden Spielernamen nur
fuer die eigene Mannschaft; beim Gegner reicht die Rueckennummer.

Ein Bericht aendert sich nach dem Spiel nicht mehr, wird also genau einmal
geholt. Das haelt die Last beim Verband bei einer Abfrage je Spiel.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PDF_URL = "https://spo.handball4all.de/misc/sboPublicReports.php?sGID={}"

PAUSE_SEKUNDEN = 1.0
VERSUCHE_HOECHSTENS = 5

ZEILE = re.compile(r"^(\d{2}:\d{2}:\d{2})\s+(\d{2,3}):(\d{2})(?:\s+(\d+):(\d+))?\s+(.+?)\s*$")
TOR = re.compile(r"^(7m-Tor|Tor) durch (.+) \(([^,()]+), ([^()]+)\)$")
FEHLWURF = re.compile(r"^7m, KEIN Tor durch (.+) \(([^,()]+), ([^()]+)\)$")
STRAFE = re.compile(r"^(Verwarnung|2-min Strafe|Disqualifikation) für (.+) \(([^,()]+), ([^()]+)\)$")
AUSZEIT = re.compile(r"^Auszeit (.+)$")
ZUSCHAUER = re.compile(r"Zuschauer:\s*(\d+)")
MANNSCHAFT = re.compile(r"^(Heim|Gast): (.+?)\s*$")
KADERZEILE = re.compile(r"^(\d{1,3})\s+(.+?)\s*$")

STRAFARTEN = {"Verwarnung": "verwarnung", "2-min Strafe": "zeitstrafe",
              "Disqualifikation": "disqualifikation"}


class BerichtFehler(Exception):
    """Der Bericht passt nicht zum Endstand oder laesst sich nicht lesen."""


def lade(pfad: Path) -> dict:
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def speichere(pfad: Path, berichte: dict) -> None:
    pfad.write_text(json.dumps(berichte, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")


def hole_pdf(bericht_id: str) -> bytes | None:
    anfrage = Request(PDF_URL.format(bericht_id), headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(anfrage, timeout=30) as antwort:
            inhalt = antwort.read()
    except (HTTPError, URLError, TimeoutError) as fehler:
        print(f"Spielbericht {bericht_id} nicht abrufbar: {fehler}", file=sys.stderr)
        return None
    if not inhalt.startswith(b"%PDF"):
        print(f"Spielbericht {bericht_id}: Antwort ist kein PDF", file=sys.stderr)
        return None
    return inhalt


def pdf_zeilen(inhalt: bytes) -> list[str]:
    # Erst hier importiert: wer nur die Seite baut, braucht pypdf nicht.
    from pypdf import PdfReader
    leser = PdfReader(io.BytesIO(inhalt))
    zeilen = []
    for seite in leser.pages:
        zeilen.extend(z.strip() for z in (seite.extract_text() or "").splitlines())
    return [z for z in zeilen if z]


def kader(zeilen: list[str], seite: str) -> list[dict]:
    """Rueckennummer und Name aus der Mannschaftsliste einer Seite.

    Hinter dem Namen folgen Tore, 7m und Strafzeiten - alles Ziffern. Der
    Name endet darum vor dem ersten Wort, das mit einer Ziffer beginnt.
    Offizielle (A bis E) beginnen mit einem Buchstaben und fallen so heraus.
    """
    liste, aktiv = [], False
    for z in zeilen:
        m = MANNSCHAFT.match(z)
        if m:
            aktiv = m.group(1).lower() == seite
            continue
        if not aktiv:
            continue
        if z.startswith("Handball4all") or z == "Spielverlauf":
            aktiv = False
            continue
        k = KADERZEILE.match(z)
        if not k:
            continue
        worte = []
        for wort in k.group(2).split():
            if wort[0].isdigit():
                break
            worte.append(wort)
        if worte:
            liste.append({"nr": k.group(1), "name": " ".join(worte)})
    return liste


def lies_bericht(zeilen: list[str], heim_tore: int, gast_tore: int, eigene_seite: str) -> dict:
    """Aus den Textzeilen des PDFs den Spielverlauf machen und pruefen.

    Welche Mannschaft hinter einem Kuerzel in Klammern steckt, ergibt sich
    aus den Toren selbst: steigt beim Tor der Heimstand, ist es die
    Heimmannschaft. Das macht den Abgleich unabhaengig davon, wie der
    Verband die Namen abkuerzt (siehe README, "Falle, die schon
    zugeschnappt ist"). Nur die Auszeit nennt den langen Namen - der steht
    im Kopf der Mannschaftslisten ("Heim: ...").
    """
    lange_namen = {}
    for z in zeilen:
        m = MANNSCHAFT.match(z)
        if m:
            lange_namen[m.group(2)] = m.group(1).lower()

    roh, unbekannt = [], []
    for z in zeilen:
        m = ZEILE.match(z)
        if not m:
            continue
        sekunde = int(m.group(2)) * 60 + int(m.group(3))
        stand = [int(m.group(4)), int(m.group(5))] if m.group(4) else None
        aktion = m.group(6)
        if t := TOR.match(aktion):
            roh.append({"s": sekunde, "art": "siebenmeter" if t.group(1) == "7m-Tor" else "tor",
                        "stand": stand, "name": t.group(2), "nr": t.group(3), "kuerzel": t.group(4)})
        elif f := FEHLWURF.match(aktion):
            roh.append({"s": sekunde, "art": "siebenmeter_fehl", "name": f.group(1),
                        "nr": f.group(2), "kuerzel": f.group(3)})
        elif st := STRAFE.match(aktion):
            roh.append({"s": sekunde, "art": STRAFARTEN[st.group(1)], "name": st.group(2),
                        "nr": st.group(3), "kuerzel": st.group(4)})
        elif a := AUSZEIT.match(aktion):
            roh.append({"s": sekunde, "art": "auszeit", "langname": a.group(1)})
        else:
            unbekannt.append(aktion)

    tore = [e for e in roh if e["art"] in ("tor", "siebenmeter")]
    if not tore:
        raise BerichtFehler("kein Spielverlauf im Bericht")

    kuerzel_seite: dict[str, str] = {}
    vorher = [0, 0]
    for e in tore:
        if e["stand"] is None:
            raise BerichtFehler(f"Tor ohne Spielstand bei {e['s']} s")
        if e["stand"] == [vorher[0] + 1, vorher[1]]:
            seite = "heim"
        elif e["stand"] == [vorher[0], vorher[1] + 1]:
            seite = "gast"
        else:
            raise BerichtFehler(f"Spielstand springt von {vorher} auf {e['stand']}")
        if kuerzel_seite.setdefault(e["kuerzel"], seite) != seite:
            raise BerichtFehler(f"{e['kuerzel']} trifft fuer beide Seiten")
        vorher = e["stand"]
    if vorher != [heim_tore, gast_tore]:
        raise BerichtFehler(f"Bericht endet {vorher[0]}:{vorher[1]}, "
                            f"Endstand ist {heim_tore}:{gast_tore}")
    # Eine Mannschaft ohne eigenes Tor taucht oben nicht auf - dann ist sie
    # das jeweils andere Kuerzel.
    if len(set(kuerzel_seite.values())) == 1:
        andere = "gast" if next(iter(kuerzel_seite.values())) == "heim" else "heim"
        for e in roh:
            if "kuerzel" in e and e["kuerzel"] not in kuerzel_seite:
                kuerzel_seite[e["kuerzel"]] = andere

    ereignisse = []
    for e in roh:
        if e["art"] == "auszeit":
            seite = lange_namen.get(e["langname"])
        else:
            seite = kuerzel_seite.get(e["kuerzel"])
        if seite is None:
            raise BerichtFehler(f"Mannschaft nicht zuzuordnen: {e.get('kuerzel') or e.get('langname')}")
        eintrag = {"s": e["s"], "art": e["art"], "eigen": seite == eigene_seite}
        if e.get("stand"):
            eintrag["stand"] = e["stand"]
        if "nr" in e:
            eintrag["nr"] = e["nr"]
            if eintrag["eigen"]:
                eintrag["name"] = e["name"]
        ereignisse.append(eintrag)

    if unbekannt:
        print(f"  unbekannte Aktionen uebergangen: {sorted(set(unbekannt))}", file=sys.stderr)

    zuschauer = next((int(m.group(1)) for z in zeilen if (m := ZUSCHAUER.search(z))), None)
    return {
        "zuschauer": zuschauer,
        "kader": kader(zeilen, eigene_seite),
        "ereignisse": ereignisse,
    }


def aktualisiere(daten: dict, berichte: dict, hoechstens: int) -> int:
    """Fehlende Berichte nachholen. Gibt zurueck, wie viele abgefragt wurden."""
    abgefragt = 0
    for team in daten["teams"].values():
        for spiel in team["spiele"]:
            bid = spiel.get("bericht_id")
            if not bid or spiel["tore_eigene"] is None:
                continue
            vorhanden = berichte.get(bid) or {}
            if vorhanden.get("ereignisse"):
                continue
            if vorhanden.get("versuche", 0) >= VERSUCHE_HOECHSTENS:
                continue
            if abgefragt >= hoechstens:
                print(f"Grenze von {hoechstens} Berichten erreicht - der Rest folgt "
                      f"beim naechsten Lauf.", file=sys.stderr)
                return abgefragt

            abgefragt += 1
            inhalt = hole_pdf(bid)
            time.sleep(PAUSE_SEKUNDEN)
            if inhalt is None:
                continue                # Netzfehler: naechstes Mal erneut, ohne Versuch zu zaehlen
            heim_tore, gast_tore = ((spiel["tore_eigene"], spiel["tore_gegner"]) if spiel["heim"]
                                    else (spiel["tore_gegner"], spiel["tore_eigene"]))
            try:
                bericht = lies_bericht(pdf_zeilen(inhalt), heim_tore, gast_tore,
                                       "heim" if spiel["heim"] else "gast")
            except Exception as fehler:     # ein kaputter Bericht darf den Lauf nicht abbrechen
                versuche = vorhanden.get("versuche", 0) + 1
                berichte[bid] = {"versuche": versuche, "fehler": str(fehler)}
                print(f"{team['name']} gegen {spiel['gegner']}: Bericht {bid} verworfen "
                      f"({fehler}), Versuch {versuche}/{VERSUCHE_HOECHSTENS}", file=sys.stderr)
                continue
            berichte[bid] = bericht
            print(f"{team['name']} gegen {spiel['gegner']}: Bericht {bid} gelesen, "
                  f"{len(bericht['ereignisse'])} Ereignisse")
    return abgefragt


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--daten", default="daten.json")
    p.add_argument("--out", default="berichte.json")
    p.add_argument("--hoechstens", type=int, default=40,
                   help="wie viele Berichte dieser Lauf hoechstens abfragt")
    cfg = p.parse_args()

    daten = json.loads(Path(cfg.daten).read_text(encoding="utf-8"))
    pfad = Path(cfg.out)
    berichte = lade(pfad)
    abgefragt = aktualisiere(daten, berichte, cfg.hoechstens)
    if abgefragt or not pfad.exists():
        speichere(pfad, berichte)
    gelesen = sum(1 for b in berichte.values() if b.get("ereignisse"))
    print(f"-> {cfg.out} ({gelesen} Berichte, {abgefragt} abgefragt)")


if __name__ == "__main__":
    main()
