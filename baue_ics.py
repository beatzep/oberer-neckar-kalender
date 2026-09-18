#!/usr/bin/env python3
"""Baut aus daten.json eine abonnierbare .ics fuer die Herren der HSG Oberer
Neckar. Faltung und VTIMEZONE folgen RFC 5545, wie im MuRu-Projekt
(handball-kalender/spielplan2ics.py) - dort ausfuehrlich getestet, hier
uebernommen statt neu erfunden."""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Berlin
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE""".split("\n")


def escape(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;")
                .replace(",", "\\,").replace("\n", "\\n"))


def falte(zeile: str) -> str:
    if len(zeile.encode("utf-8")) <= 75:
        return zeile
    stuecke: list[str] = []
    aktuell: list[str] = []
    laenge = 0
    for zeichen in zeile:
        breite = len(zeichen.encode("utf-8"))
        if laenge + breite > 75:
            stuecke.append("".join(aktuell))
            aktuell, laenge = [" "], 1
        aktuell.append(zeichen)
        laenge += breite
    stuecke.append("".join(aktuell))
    return "\r\n".join(stuecke)


def utc(zeitpunkt: datetime) -> str:
    return zeitpunkt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def baue(daten: dict) -> str:
    jetzt = datetime.now(timezone.utc)
    eigene = f"HSG Oberer Neckar {daten['mannschaft']}"
    zeilen = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//oberer-neckar-kalender//baue_ics//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape(eigene)}",
        "X-WR-TIMEZONE:Europe/Berlin",
        f"X-WR-CALDESC:{escape('Spielplan ' + eigene + ' - Quelle: handball4all')}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
        *VTIMEZONE,
    ]

    for spiel in daten["spiele"]:
        heim = spiel["heim"] == "HSG Ob. Neckar"
        gegner = spiel["gast"] if heim else spiel["heim"]
        marke = "\U0001F3E0 " if heim else "\U0001F697 "

        if spiel["tore_heim"] is not None and spiel["tore_gast"] is not None:
            trenner = f" {spiel['tore_heim']}:{spiel['tore_gast']} "
        else:
            trenner = " - "
        titel = (f"{marke}{eigene}{trenner}{gegner}" if heim
                 else f"{marke}{gegner}{trenner}{eigene}")

        beginn = datetime.fromisoformat(spiel["termin"])
        beschreibung = [f"{'Heimspiel' if heim else 'Auswaertsspiel'} gegen {gegner}"]
        if spiel["uhrzeit_bekannt"]:
            beschreibung.append(f"Anwurf: {beginn.strftime('%H:%M')} Uhr")
        else:
            beschreibung.append("Anwurf: noch nicht angesetzt")
        if spiel["tore_heim"] is not None and spiel["tore_gast"] is not None:
            eig, frd = ((spiel["tore_heim"], spiel["tore_gast"]) if heim
                        else (spiel["tore_gast"], spiel["tore_heim"]))
            ausgang = "Sieg" if eig > frd else "Niederlage" if eig < frd else "Unentschieden"
            beschreibung.insert(0, f"Endstand: {spiel['tore_heim']}:{spiel['tore_gast']} ({ausgang})")
        beschreibung.append(f"Liga: {daten['liga']}")
        if spiel["schiedsrichter"]:
            beschreibung.append(f"Schiedsrichter: {spiel['schiedsrichter']}")
        beschreibung.append(f"Spielnummer: {spiel['nummer']}")

        if spiel["uhrzeit_bekannt"]:
            ende = beginn + timedelta(hours=2)
            zeit_zeilen = [f"DTSTART;TZID=Europe/Berlin:{beginn:%Y%m%dT%H%M%S}",
                           f"DTEND;TZID=Europe/Berlin:{ende:%Y%m%dT%H%M%S}"]
        else:
            ende_tag = beginn + timedelta(days=1)
            zeit_zeilen = [f"DTSTART;VALUE=DATE:{beginn:%Y%m%d}",
                           f"DTEND;VALUE=DATE:{ende_tag:%Y%m%d}"]

        zeilen += [
            "BEGIN:VEVENT",
            f"UID:{spiel['id']}@oberer-neckar-kalender",
            f"DTSTAMP:{utc(jetzt)}",
            *zeit_zeilen,
            f"SUMMARY:{escape(titel)}",
            f"DESCRIPTION:{escape(chr(10).join(beschreibung))}",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            f"CATEGORIES:Handball,{'Heimspiel' if heim else 'Auswaertsspiel'}",
        ]
        if spiel["halle"]:
            zeilen.append(f"LOCATION:{escape(spiel['halle'])}")
        if spiel["uhrzeit_bekannt"]:
            for ausloeser, text in (("-P1D", "Morgen Spiel"), ("-PT3H", "Gleich Spiel")):
                zeilen += [
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    f"TRIGGER:{ausloeser}",
                    f"DESCRIPTION:{escape(text + ': ' + titel.strip())}",
                    "END:VALARM",
                ]
        zeilen.append("END:VEVENT")

    zeilen.append("END:VCALENDAR")
    return "\r\n".join(falte(z) for z in zeilen) + "\r\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--daten", default="daten.json")
    p.add_argument("--out", default="docs/oberer-neckar.ics")
    cfg = p.parse_args()

    daten = json.loads(Path(cfg.daten).read_text(encoding="utf-8"))
    Path(cfg.out).write_text(baue(daten), encoding="utf-8", newline="")
    print(f"-> {cfg.out}")


if __name__ == "__main__":
    main()
