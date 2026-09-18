#!/usr/bin/env python3
"""Baut aus daten.json die statische Seite docs/index.html: naechstes Spiel,
Tabelle, kompletter Spielplan. Kein Vergleich zu baue_seite.py im
MuRu-Projekt beabsichtigt - hier reicht eine Mannschaft auf einer Seite."""

import argparse
import json
from datetime import datetime
from pathlib import Path

EIGENER_NAME = "HSG Ob. Neckar"


def ist_heimspiel(spiel: dict) -> bool:
    return spiel["heim"] == EIGENER_NAME


def gegner(spiel: dict) -> str:
    return spiel["gast"] if ist_heimspiel(spiel) else spiel["heim"]


def kurzdatum(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    tage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    return f"{tage[d.weekday()]} {d:%d.%m.%y}"


def naechstes_spiel(spiele: list[dict]) -> dict | None:
    jetzt = datetime.now()
    kommende = [s for s in spiele
                if s["tore_heim"] is None and datetime.fromisoformat(s["termin"]) >= jetzt.replace(hour=0, minute=0)]
    return kommende[0] if kommende else None


def baue_naechstes_spiel_block(spiel: dict | None) -> str:
    if spiel is None:
        return "<p>Kein weiteres Spiel angesetzt - die Saison ist entweder vorbei oder handball4all hat noch keine Termine veroeffentlicht.</p>"
    heim = ist_heimspiel(spiel)
    zeit = (datetime.fromisoformat(spiel["termin"]).strftime("%H:%M") + " Uhr"
            if spiel["uhrzeit_bekannt"] else "Uhrzeit noch nicht angesetzt")
    ort = "Heimspiel" if heim else "Auswaertsspiel"
    halle = f"<p class=\"halle\">{spiel['halle']}</p>" if spiel["halle"] else ""
    return f"""
    <p class="wer">{'HSG Oberer Neckar' if heim else gegner(spiel)} vs. {gegner(spiel) if heim else 'HSG Oberer Neckar'}</p>
    <p class="wann">{kurzdatum(spiel['termin'])}, {zeit} &middot; {ort}</p>
    {halle}
    """


def baue_tabelle(tabelle: list[dict]) -> str:
    zeilen = []
    for platz_nr, row in enumerate(tabelle, start=1):
        hervorhebung = ' class="eigene"' if row["team"] in (EIGENER_NAME, "HSG Oberer Neckar") else ""
        platz = row["platz"] or ""
        zeilen.append(f"""
        <tr{hervorhebung}>
          <td>{platz}</td>
          <td>{row['team']}</td>
          <td>{row['spiele']}</td>
          <td>{row['siege']}:{row['unentschieden']}:{row['niederlagen']}</td>
          <td>{row['tore_geschossen']}:{row['tore_erhalten']}</td>
          <td>{row['punkte_plus']}:{row['punkte_minus']}</td>
        </tr>""")
    return "".join(zeilen)


def baue_spielplan(spiele: list[dict]) -> str:
    zeilen = []
    for spiel in spiele:
        heim = ist_heimspiel(spiel)
        ergebnis = (f"{spiel['tore_heim']}:{spiel['tore_gast']}"
                    if spiel["tore_heim"] is not None else "-")
        zeit = (datetime.fromisoformat(spiel["termin"]).strftime("%H:%M")
                if spiel["uhrzeit_bekannt"] else "offen")
        marke = "H" if heim else "A"
        zeilen.append(f"""
        <tr>
          <td>{kurzdatum(spiel['termin'])}</td>
          <td>{zeit}</td>
          <td class="marke">{marke}</td>
          <td>{gegner(spiel)}</td>
          <td>{ergebnis}</td>
        </tr>""")
    return "".join(zeilen)


SEITE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HSG Oberer Neckar - Herren Spielplan</title>
<meta name="description" content="Spielplan, Tabelle und naechstes Spiel der Herren-Bezirksoberliga-Mannschaft der HSG Oberer Neckar.">
<style>
  :root {{
    --blau: #1c3f6e;
    --hell: #f4f6f9;
    --rand: #dfe4ea;
    --text: #202730;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 0 1rem 3rem;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: var(--text); background: #fff;
  }}
  .kopf {{
    background: var(--blau); color: #fff; margin: 0 -1rem 1.5rem; padding: 1.5rem 1rem;
  }}
  .kopf h1 {{ margin: 0 0 0.25rem; font-size: 1.4rem; }}
  .kopf p {{ margin: 0; opacity: 0.85; font-size: 0.95rem; }}
  main {{ max-width: 720px; margin: 0 auto; }}
  section {{ margin-bottom: 2rem; }}
  h2 {{ font-size: 1.1rem; border-bottom: 2px solid var(--rand); padding-bottom: 0.4rem; }}
  .naechstes {{
    background: var(--hell); border: 1px solid var(--rand); border-radius: 10px;
    padding: 1rem 1.2rem;
  }}
  .naechstes .wer {{ font-weight: 600; font-size: 1.15rem; margin: 0 0 0.3rem; }}
  .naechstes .wann {{ margin: 0; color: #4a5568; }}
  .naechstes .halle {{ margin: 0.3rem 0 0; color: #4a5568; font-size: 0.9rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
  th, td {{ text-align: left; padding: 0.45rem 0.5rem; border-bottom: 1px solid var(--rand); }}
  th {{ color: #4a5568; font-weight: 600; font-size: 0.85rem; }}
  tr.eigene {{ background: #eaf1fb; font-weight: 600; }}
  td.marke {{ color: #4a5568; }}
  .abo {{
    display: inline-block; margin-top: 0.6rem; padding: 0.5rem 0.9rem;
    background: var(--blau); color: #fff; text-decoration: none; border-radius: 6px; font-size: 0.9rem;
  }}
  footer {{ max-width: 720px; margin: 2rem auto 0; color: #718096; font-size: 0.85rem; }}
</style>
</head>
<body>
<div class="kopf">
  <h1>HSG Oberer Neckar &ndash; Herren</h1>
  <p>{liga}, {bereich}</p>
</div>
<main>
  <section>
    <h2>N&auml;chstes Spiel</h2>
    <div class="naechstes">
      {naechstes_spiel}
    </div>
    <a class="abo" href="oberer-neckar.ics">Kalender abonnieren (.ics)</a>
  </section>

  <section>
    <h2>Tabelle</h2>
    <table>
      <thead>
        <tr><th>Platz</th><th>Mannschaft</th><th>Sp.</th><th>S:U:N</th><th>Tore</th><th>Punkte</th></tr>
      </thead>
      <tbody>{tabelle}</tbody>
    </table>
  </section>

  <section>
    <h2>Spielplan</h2>
    <table>
      <thead>
        <tr><th>Datum</th><th>Zeit</th><th></th><th>Gegner</th><th>Ergebnis</th></tr>
      </thead>
      <tbody>{spielplan}</tbody>
    </table>
  </section>
</main>
<footer>
  <p>Daten von handball4all (Baden-W&uuml;rttembergischer Handball-Verband), Stand: {quelle_stand}.
  Torverl&auml;ufe und Spielberichte f&uuml;hrt der Verband auf dieser Ebene nicht &ndash; deshalb stehen hier nur Termine und Endst&auml;nde.
  Zuletzt geholt: {geholt_am}.</p>
</footer>
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
        naechstes_spiel=baue_naechstes_spiel_block(naechstes_spiel(daten["spiele"])),
        tabelle=baue_tabelle(daten["tabelle"]),
        spielplan=baue_spielplan(daten["spiele"]),
        quelle_stand=daten["quelle_stand"],
        geholt_am=datetime.fromisoformat(daten["geholt_am"]).strftime("%d.%m.%Y %H:%M"),
    )
    Path(cfg.out).write_text(seite, encoding="utf-8")
    print(f"-> {cfg.out}")


if __name__ == "__main__":
    main()
