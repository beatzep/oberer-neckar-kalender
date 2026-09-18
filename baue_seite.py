#!/usr/bin/env python3
"""Baut aus daten.json die statische Seite docs/index.html: naechstes Spiel,
Tabelle, kompletter Spielplan. Kein Vergleich zu baue_seite.py im
MuRu-Projekt beabsichtigt - hier reicht eine Mannschaft auf einer Seite.
Die Formensprache (dunkler Kopf, scharfe Kanten, duenne Linien statt Karten,
hell/dunkel automatisch) ist von dort uebernommen, nur die Akzentfarbe ist
eine andere - sonst waeren beide Seiten auf den ersten Blick verwechselbar."""

import argparse
import json
from datetime import datetime
from pathlib import Path

EIGENER_NAME = "HSG Ob. Neckar"
MONATE = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]
TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def ist_heimspiel(spiel: dict) -> bool:
    return spiel["heim"] == EIGENER_NAME


def gegner(spiel: dict) -> str:
    return spiel["gast"] if ist_heimspiel(spiel) else spiel["heim"]


def kurzdatum(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    return f"{TAGE[d.weekday()]} {d:%d.%m.%y}"


def naechstes_spiel(spiele: list[dict]) -> dict | None:
    heute = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    kommende = [s for s in spiele
                if s["tore_heim"] is None and datetime.fromisoformat(s["termin"]) >= heute]
    return kommende[0] if kommende else None


def baue_naechstes_spiel(spiel: dict | None) -> str:
    if spiel is None:
        return """
        <p class="marker">Nächstes Spiel</p>
        <p class="paarung">Keins angesetzt</p>
        <p class="hinweistext">Entweder ist die Saison vorbei, oder handball4all hat für die
        Mannschaft noch keine weiteren Termine veröffentlicht.</p>"""

    heim = ist_heimspiel(spiel)
    eigener_anzeigename = "HSG Oberer Neckar"
    zeilen = [f'<dt>Datum</dt><dd>{kurzdatum(spiel["termin"])}</dd>']
    if spiel["uhrzeit_bekannt"]:
        zeit = datetime.fromisoformat(spiel["termin"]).strftime("%H:%M")
        zeilen.append(f'<dt>Anwurf</dt><dd>{zeit} Uhr</dd>')
    else:
        zeilen.append('<dt>Anwurf</dt><dd>Noch nicht angesetzt</dd>')
    zeilen.append(f'<dt>Ort</dt><dd>{"Heimspiel" if heim else "Auswärtsspiel"}</dd>')
    if spiel["halle"]:
        zeilen.append(f'<dt>Halle</dt><dd>{spiel["halle"]}</dd>')

    paarung = (f'{eigener_anzeigename} <span class="gegen">–</span> {gegner(spiel)}' if heim
               else f'{gegner(spiel)} <span class="gegen">–</span> {eigener_anzeigename}')

    return f"""
    <p class="marker">Nächstes Spiel</p>
    <p class="paarung">{paarung}</p>
    <dl class="fakten">{''.join(zeilen)}</dl>"""


def baue_tabelle(tabelle: list[dict]) -> str:
    zeilen = []
    for row in tabelle:
        eigene = ' class="eigene"' if row["team"] in (EIGENER_NAME, "HSG Oberer Neckar") else ""
        platz = row["platz"] or "&nbsp;"
        zeilen.append(f"""
        <tr{eigene}>
          <td class="platz">{platz}</td>
          <td>{row['team']}</td>
          <td class="rechts">{row['spiele']}</td>
          <td class="rechts">{row['siege']}:{row['unentschieden']}:{row['niederlagen']}</td>
          <td class="rechts">{row['tore_geschossen']}:{row['tore_erhalten']}</td>
          <td class="rechts stark">{row['punkte_plus']}:{row['punkte_minus']}</td>
        </tr>""")
    return "".join(zeilen)


def baue_spielplan(spiele: list[dict]) -> str:
    heute = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    zeilen = []
    letzter_monat = None
    for spiel in spiele:
        beginn = datetime.fromisoformat(spiel["termin"])
        monat = (beginn.year, beginn.month)
        if monat != letzter_monat:
            zeilen.append(f'<p class="monat">{MONATE[beginn.month]} {beginn.year}</p>')
            letzter_monat = monat

        heim = ist_heimspiel(spiel)
        vorbei = spiel["tore_heim"] is not None
        klassen = "spiel" + (" vorbei" if vorbei else "")

        if vorbei:
            eig, frd = ((spiel["tore_heim"], spiel["tore_gast"]) if heim
                        else (spiel["tore_gast"], spiel["tore_heim"]))
            ausgang = "S" if eig > frd else "N" if eig < frd else "U"
            stand = f'<div class="stand {ausgang}">{spiel["tore_heim"]}:{spiel["tore_gast"]}</div>'
        else:
            zeit = (datetime.fromisoformat(spiel["termin"]).strftime("%H:%M") + " Uhr"
                    if spiel["uhrzeit_bekannt"] else "offen")
            stand = f'<div class="stand">{zeit}</div>'

        halle = f'<div class="halle">{spiel["halle"]}</div>' if spiel["halle"] else ""

        zeilen.append(f"""
        <div class="{klassen}">
          <div class="datum">{kurzdatum(spiel['termin'])}<span>{'Heim' if heim else 'Auswärts'}</span></div>
          <div>
            <div class="gegner">{gegner(spiel)}</div>
            {halle}
          </div>
          <div class="rechts">{stand}</div>
        </div>""")
    return "".join(zeilen)


SEITE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HSG Oberer Neckar – Herren</title>
<meta name="description" content="Spielplan, Tabelle und nächstes Spiel der Herren-Bezirksoberliga-Mannschaft der HSG Oberer Neckar.">
<style>
:root {{
  --akzent: #2f8f74; --akzent-tief: #226b57; --akzent-schwach: rgba(47,143,116,.12);
  --tinte: #14140f; --tinte-weich: #4a4a42; --leise: #7a776d;
  --linie: #dedbd3; --linie-zart: #ebe9e3;
  --grund: #ffffff; --schwarz: #14140f; --auf-schwarz: #f7f5f0;
  --sieg: #2f7d4f; --niederlage: #a4443a;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --akzent: #4fbfa0; --akzent-tief: #2f8f74; --akzent-schwach: rgba(79,191,160,.14);
    --tinte: #f2efe8; --tinte-weich: #b8b4a9; --leise: #8c877c;
    --linie: #33312b; --linie-zart: #24221e;
    --grund: #0d0d0b; --schwarz: #000000; --auf-schwarz: #f2efe8;
    --sieg: #5cbf85; --niederlage: #e08076;
  }}
}}
*, *::before, *::after {{ box-sizing: border-box; border-radius: 0; }}
html {{ -webkit-text-size-adjust: 100%; }}
body {{
  margin: 0; background: var(--grund); color: var(--tinte);
  font: 400 17px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
  font-variant-numeric: tabular-nums; -webkit-font-smoothing: antialiased;
}}
.huelle {{ max-width: 720px; margin: 0 auto; padding: 0 22px; }}
a {{ color: inherit; }}

.kopf {{ background: var(--schwarz); color: var(--auf-schwarz);
         border-bottom: 2px solid var(--akzent); }}
.kopf .huelle {{ padding: 26px 22px 30px; }}
.zeile1 {{ font-size: .82rem; font-weight: 600; letter-spacing: .04em; color: var(--akzent); }}
.kopf h1 {{ margin: 6px 0 0; font-size: clamp(2rem, 10vw, 2.9rem); font-weight: 300;
            line-height: 1.06; letter-spacing: -.015em; }}
.kopf .liga {{ margin: 12px 0 0; font-size: .92rem; color: rgba(247,245,240,.62); }}

.teil {{ padding: 34px 0 0; }}
.rubrik {{ border-top: 1px solid var(--linie); padding-top: 14px; margin-bottom: 22px;
           font-size: .95rem; font-weight: 600; color: var(--leise); }}

.marker {{ font-size: .82rem; font-weight: 600; color: var(--akzent-tief);
           letter-spacing: .04em; margin: 0 0 10px; }}
.paarung {{ font-size: clamp(1.4rem, 6.5vw, 1.9rem); font-weight: 400; line-height: 1.2;
            letter-spacing: -.01em; margin: 0 0 20px; overflow-wrap: anywhere; }}
.paarung .gegen {{ color: var(--leise); font-weight: 300; }}
.fakten {{ margin: 0; }}
.fakten dt {{ float: left; width: 78px; color: var(--leise); font-size: .95rem;
              clear: left; padding: 11px 0; border-top: 1px solid var(--linie-zart); }}
.fakten dd {{ margin: 0 0 0 96px; font-size: .95rem; padding: 11px 0;
              border-top: 1px solid var(--linie-zart); }}
.hinweistext {{ color: var(--tinte-weich); font-size: .95rem; }}

.knopf {{
  display: inline-block; margin-top: 22px; text-align: center; text-decoration: none;
  font: inherit; font-size: .95rem; font-weight: 600; padding: 14px 22px;
  border: 1px solid var(--akzent); background: var(--akzent); color: #0d0d0b;
}}
.knopf:hover {{ background: var(--akzent-tief); border-color: var(--akzent-tief); color: #fff; }}

table {{ width: 100%; border-collapse: collapse; font-size: .92rem; }}
th, td {{ text-align: left; padding: 10px 8px; border-top: 1px solid var(--linie-zart); }}
thead th {{ border-top: none; border-bottom: 1px solid var(--linie);
            color: var(--leise); font-size: .78rem; font-weight: 600;
            letter-spacing: .04em; text-transform: uppercase; padding-bottom: 8px; }}
td.rechts, th.rechts {{ text-align: right; }}
.rechts {{ text-align: right; }}
.stark {{ font-weight: 700; }}
tr.eigene td {{ font-weight: 600; color: var(--akzent-tief); }}
td.platz {{ color: var(--leise); width: 2em; }}

.monat {{ font-size: .8rem; font-weight: 600; letter-spacing: .06em;
          text-transform: uppercase; color: var(--leise); padding: 26px 0 8px; }}
.monat:first-of-type {{ padding-top: 4px; }}
.spiel {{ display: grid; grid-template-columns: 62px 1fr auto; gap: 0 14px;
          align-items: start; padding: 14px 0; border-top: 1px solid var(--linie); }}
.spiel .datum {{ font-size: .86rem; font-weight: 600; line-height: 1.3; }}
.spiel .datum span {{ display: block; font-weight: 400; color: var(--leise); }}
.spiel .gegner {{ font-size: 1rem; font-weight: 500; line-height: 1.3; overflow-wrap: anywhere; }}
.spiel .halle {{ font-size: .86rem; color: var(--leise); margin-top: 3px; }}
.spiel .stand {{ font-size: .92rem; font-weight: 700; white-space: nowrap; }}
.spiel .stand.S {{ color: var(--sieg); }}
.spiel .stand.N {{ color: var(--niederlage); }}
.spiel .stand.U {{ color: var(--leise); }}
.spiel.vorbei {{ opacity: .55; }}
.spiel.vorbei .gegner {{ font-weight: 400; }}

.fuss {{ padding: 30px 0 40px; border-top: 1px solid var(--linie); margin-top: 30px;
         font-size: .86rem; color: var(--leise); }}
.fuss p {{ margin: 0 0 10px; }}
</style>
</head>
<body>
<div class="kopf">
  <div class="huelle">
    <p class="zeile1">HSG Oberer Neckar</p>
    <h1>Herren</h1>
    <p class="liga">{liga} &middot; {bereich}</p>
  </div>
</div>
<div class="huelle">

  <div class="teil">
    {naechstes_spiel}
    <a class="knopf" href="oberer-neckar.ics">Kalender abonnieren</a>
  </div>

  <div class="teil">
    <p class="rubrik">Tabelle</p>
    <table>
      <thead>
        <tr><th></th><th>Mannschaft</th><th class="rechts">Sp.</th><th class="rechts">S:U:N</th><th class="rechts">Tore</th><th class="rechts">Punkte</th></tr>
      </thead>
      <tbody>{tabelle}</tbody>
    </table>
  </div>

  <div class="teil">
    <p class="rubrik">Spielplan</p>
    {spielplan}
  </div>

  <div class="fuss">
    <p>Daten von handball4all (Baden-W&uuml;rttembergischer Handball-Verband), Stand: {quelle_stand}.</p>
    <p>Torverl&auml;ufe und Spielberichte f&uuml;hrt der Verband auf dieser Liga-Ebene nicht &ndash;
    deshalb stehen hier nur Termine, Hallen und Endst&auml;nde, keine Statistiken.</p>
    <p>Zuletzt geholt: {geholt_am}.</p>
  </div>

</div>
</body>
</html>
"""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--daten", default="daten.json")
    p.add_argument("--out", default="docs/index.html")
    cfg = p.parse_args()

    daten = json.loads(Path(cfg.daten).read_text(encoding="utf-8"))
    seite = SEITE.format(
        liga=daten["liga"],
        bereich=daten["bereich"],
        naechstes_spiel=baue_naechstes_spiel(naechstes_spiel(daten["spiele"])),
        tabelle=baue_tabelle(daten["tabelle"]),
        spielplan=baue_spielplan(daten["spiele"]),
        quelle_stand=daten["quelle_stand"],
        geholt_am=datetime.fromisoformat(daten["geholt_am"]).strftime("%d.%m.%Y %H:%M"),
    )
    Path(cfg.out).write_text(seite, encoding="utf-8")
    print(f"-> {cfg.out}")


if __name__ == "__main__":
    main()
