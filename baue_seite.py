#!/usr/bin/env python3
"""Baut aus daten.json die statische Seite docs/index.html: naechstes Spiel
oben fest, darunter Reiter fuer Spielplan, Tabelle und Statistiken - wie im
MuRu-Projekt, nur fuer eine einzelne Mannschaft. Formensprache ebenfalls von
dort (dunkler Kopf, scharfe Kanten, duenne Linien statt Karten, automatisch
hell/dunkel), Farben sind die echten Vereinsfarben der HSG Oberer Neckar
(aus dem Logo auf hsg-oberer-neckar.de ausgelesen: Navy #0a2c73, Gold
#ffda06) statt frei erfunden."""

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


def baue_kalender_block(basis_url: str) -> str:
    """Drei Wege in den Kalender, wie im MuRu-Projekt (baue_seite.py,
    abo_block): Abo per webcal fuer Apple-Geraete, Abo per URL fuer Google
    Kalender (das Android-Handy kann Abos nicht selbst anlegen), einmaliger
    Download ohne Abo. Unsere .ics ist eine eigene, statische Datei auf
    GitHub Pages - anders als der kaputte Kalender-Export auf handball4all
    selbst haengt das an nichts, was bei denen ausfallen kann."""
    ics_url = f"{basis_url.rstrip('/')}/oberer-neckar.ics"
    webcal = ics_url.replace("https://", "webcal://").replace("http://", "webcal://")
    return f"""
    <div class="weg">
      <h3>iPhone, iPad und Mac</h3>
      <p>Antippen, „Abonnieren" bestätigen. Verlegungen und neue Ergebnisse ziehen
      sich danach automatisch nach, ohne dass du noch mal hier vorbeischauen musst.</p>
      <a class="knopf" href="{webcal}">HSG Oberer Neckar abonnieren</a>
      <p class="tipp"><b>Am Mac</b> fragt der Kalender vorher noch was: „Automatisch
      aktualisieren" auf <b>Jede Stunde</b> stellen, sonst kriegst du Verlegungen
      erst Tage später mit.</p>
      <p class="tipp"><b>Passiert nach dem Antippen nichts?</b> Dann hat der Browser
      die Erlaubnis dafür schon mal verweigert, meist ohne dass man es merkt - keine
      Fehlermeldung, die Seite bleibt einfach stehen. Dann so:</p>
      <button class="knopf stumm" type="button" data-kopiere="{ics_url}">Adresse kopieren</button>
      <ol class="schritte">
        <li>Kalender-App öffnen</li>
        <li>Menü <strong>Ablage → Neues Kalenderabo …</strong></li>
        <li>Adresse einfügen, „Abonnieren" bestätigen</li>
      </ol>
      <p class="tipp">Das geht immer, egal was der Browser gerade erlaubt oder nicht -
      die App fragt selbst bei der Adresse nach, ohne den Umweg über den Link.</p>
    </div>

    <div class="weg">
      <h3>Android und Google Kalender</h3>
      <p>Bei Google geht das Abonnieren nur am Computer, nicht in der Handy-App.
      Einmal am Rechner einrichten, danach ist es auf dem Handy auch da.</p>
      <button class="knopf stumm" type="button" data-kopiere="{ics_url}">Adresse kopieren</button>
      <ol class="schritte">
        <li>Am Computer <code>calendar.google.com</code> öffnen</li>
        <li>Links bei „Weitere Kalender" auf <strong>+</strong> klicken</li>
        <li>„Per URL" wählen, Adresse einfügen, hinzufügen</li>
      </ol>
    </div>

    <div class="weg">
      <h3>Einmalig importieren</h3>
      <p>Ohne Abo, ohne spätere Aktualisierung - für alle, die nur diesen Stand
      in ihren Kalender übernehmen wollen. Der Knopf lädt die Datei in deinen
      Downloads-Ordner, sie öffnet sich nicht von selbst: danach im Downloads-Ordner
      doppelklicken, dann übernimmt die Kalender-App die Termine.</p>
      <a class="knopf stumm" href="oberer-neckar.ics" download>Datei herunterladen</a>
    </div>"""


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
<meta name="theme-color" content="#0a2c73">
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<style>
:root {{
  --gold: #ffda06; --gold-tief: #d6b400; --gold-schwach: rgba(255,218,6,.14);
  --tinte: #14140f; --tinte-weich: #4a4a42; --leise: #7a776d;
  --linie: #dedbd3; --linie-zart: #ebe9e3;
  --grund: #ffffff; --marine: #0a2c73; --auf-marine: #f3f5fa;
  --sieg: #2f7d4f; --niederlage: #a4443a;
}}
/* Dunkle Farben an zwei Stellen: nach Systemeinstellung (solange niemand
   ausdruecklich hell gewaehlt hat) und bei ausdruecklicher Wahl. Wie im
   MuRu-Projekt (seite_stil.py). */
@media (prefers-color-scheme: dark) {{
  :root:not([data-ansicht="hell"]) {{
    --gold: #ffe14d; --gold-tief: #ffda06; --gold-schwach: rgba(255,225,77,.14);
    --tinte: #f2efe8; --tinte-weich: #b8b4a9; --leise: #8c877c;
    --linie: #2c3550; --linie-zart: #1c2440;
    --grund: #0b0e1c; --marine: #000000; --auf-marine: #f3f5fa;
    --sieg: #5cbf85; --niederlage: #e08076;
  }}
}}
:root[data-ansicht="dunkel"] {{
  --gold: #ffe14d; --gold-tief: #ffda06; --gold-schwach: rgba(255,225,77,.14);
  --tinte: #f2efe8; --tinte-weich: #b8b4a9; --leise: #8c877c;
  --linie: #2c3550; --linie-zart: #1c2440;
  --grund: #0b0e1c; --marine: #000000; --auf-marine: #f3f5fa;
  --sieg: #5cbf85; --niederlage: #e08076;
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
button {{ touch-action: manipulation; -webkit-tap-highlight-color: transparent; }}

.kopf {{ background: var(--marine); color: var(--auf-marine);
         border-bottom: 3px solid var(--gold); }}
.kopf .huelle {{ padding: 22px 22px 26px; position: relative; }}
#ansicht {{
  position: absolute; top: 0; right: 22px;
  width: 42px; height: 42px; padding: 0; cursor: pointer;
  background: transparent; border: 1px solid rgba(243,245,250,.28);
  color: rgba(243,245,250,.8); display: flex; align-items: center;
  justify-content: center;
}}
#ansicht:hover {{ color: var(--gold); border-color: var(--gold); }}
#ansicht:focus-visible {{ outline: 2px solid var(--gold); outline-offset: 2px; }}
#ansicht svg {{ width: 20px; height: 20px; display: block; }}
#ansicht .sonne {{ display: none; }}
@media (prefers-color-scheme: dark) {{
  :root:not([data-ansicht="hell"]) #ansicht .sonne {{ display: block; }}
  :root:not([data-ansicht="hell"]) #ansicht .mond {{ display: none; }}
}}
:root[data-ansicht="dunkel"] #ansicht .sonne {{ display: block; }}
:root[data-ansicht="dunkel"] #ansicht .mond {{ display: none; }}
:root[data-ansicht="hell"] #ansicht .sonne {{ display: none; }}
:root[data-ansicht="hell"] #ansicht .mond {{ display: block; }}
.marke {{ display: flex; align-items: center; gap: 14px; }}
.marke img {{ width: 48px; height: 48px; display: block; }}
.zeile1 {{ font-size: .82rem; font-weight: 600; letter-spacing: .04em; color: var(--gold); margin: 0; }}
.kopf h1 {{ margin: 2px 0 0; font-size: clamp(1.8rem, 8vw, 2.6rem); font-weight: 300;
            line-height: 1.06; letter-spacing: -.015em; }}
.kopf .liga {{ margin: 14px 0 0; font-size: .9rem; color: rgba(243,245,250,.65); }}

.teil {{ padding: 30px 0 0; }}
.rubrik {{ border-top: 1px solid var(--linie); padding-top: 14px; margin-bottom: 22px;
           font-size: .95rem; font-weight: 600; color: var(--leise); }}

.marker {{ font-size: .82rem; font-weight: 600; color: var(--gold-tief);
           letter-spacing: .04em; margin: 0 0 10px; }}
.paarung {{ font-size: clamp(1.35rem, 6vw, 1.8rem); font-weight: 400; line-height: 1.22;
            letter-spacing: -.01em; margin: 0 0 18px; overflow-wrap: anywhere; }}
.paarung .gegen {{ color: var(--leise); font-weight: 300; }}
.fakten {{ margin: 0; }}
.fakten dt {{ float: left; width: 78px; color: var(--leise); font-size: .95rem;
              clear: left; padding: 11px 0; border-top: 1px solid var(--linie-zart); }}
.fakten dd {{ margin: 0 0 0 96px; font-size: .95rem; padding: 11px 0;
              border-top: 1px solid var(--linie-zart); }}
.hinweistext {{ color: var(--tinte-weich); font-size: .95rem; }}

.knopf {{
  display: inline-block; margin-top: 20px; text-align: center; text-decoration: none;
  font: inherit; font-size: .95rem; font-weight: 600; padding: 14px 22px;
  border: 1px solid var(--gold); background: var(--gold); color: #14140f;
}}
.knopf:hover {{ background: var(--gold-tief); border-color: var(--gold-tief); }}
.knopf.stumm {{ background: transparent; color: var(--tinte); border-color: var(--tinte); }}
.knopf.stumm:hover {{ background: var(--gold-schwach); border-color: var(--gold); }}

.weg {{ padding: 26px 0; border-top: 1px solid var(--linie-zart); }}
.weg:first-child {{ padding-top: 0; border-top: 0; }}
.weg h3 {{ margin: 0 0 6px; font-size: 1.08rem; font-weight: 600; }}
.weg p {{ margin: 0 0 16px; font-size: .95rem; color: var(--tinte-weich); }}
.weg .tipp {{ margin: 12px 0 0; font-size: .86rem; color: var(--leise); }}
.schritte {{ margin: 16px 0 0; padding: 0; list-style: none; font-size: .92rem;
             color: var(--tinte-weich); counter-reset: schritt; }}
.schritte li {{ counter-increment: schritt; position: relative;
                padding: 8px 0 8px 34px; border-top: 1px solid var(--linie-zart); }}
.schritte li::before {{ content: counter(schritt); position: absolute; left: 0; top: 8px;
                        font-size: .82rem; font-weight: 600; color: var(--gold-tief); }}
code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .88em; }}

/* ---------- Reiter ---------- */
.reiter {{ position: sticky; top: 0; z-index: 5; background: var(--grund);
           border-bottom: 1px solid var(--linie); display: flex;
           overflow-x: auto; scrollbar-width: none; margin-top: 34px; }}
.reiter::-webkit-scrollbar {{ display: none; }}
.reiter button {{
  flex: 0 0 auto; font: inherit; font-size: .92rem; font-weight: 500;
  background: none; border: 0; border-bottom: 2px solid transparent;
  color: var(--leise); padding: 15px 18px 13px; margin-bottom: -1px;
  white-space: nowrap; cursor: pointer;
}}
.reiter button:first-child {{ padding-left: 0; }}
.reiter button[aria-selected="true"] {{ color: var(--tinte); border-bottom-color: var(--gold); }}
[hidden] {{ display: none !important; }}

table {{ width: 100%; border-collapse: collapse; font-size: .92rem; }}
th, td {{ text-align: left; padding: 10px 8px; border-top: 1px solid var(--linie-zart); }}
thead th {{ border-top: none; border-bottom: 1px solid var(--linie);
            color: var(--leise); font-size: .78rem; font-weight: 600;
            letter-spacing: .04em; text-transform: uppercase; padding-bottom: 8px; }}
.rechts {{ text-align: right; }}
.stark {{ font-weight: 700; }}
tr.eigene td {{ font-weight: 600; color: var(--gold-tief); }}
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

.statistiken p {{ font-size: .95rem; color: var(--tinte-weich); }}
.statistiken .hinweis {{ border-left: 2px solid var(--gold); padding: 2px 0 2px 18px; margin-top: 18px; }}

.fuss {{ padding: 30px 0 40px; border-top: 1px solid var(--linie); margin-top: 34px;
         font-size: .86rem; color: var(--leise); }}
.fuss p {{ margin: 0 0 10px; }}
</style>
</head>
<body>
<div class="kopf">
  <div class="huelle">
    <button id="ansicht" type="button" aria-label="Ansicht umschalten">
      <svg class="mond" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"
           aria-hidden="true">
        <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/>
      </svg>
      <svg class="sonne" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"
           aria-hidden="true">
        <circle cx="12" cy="12" r="4.2"/>
        <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.2 5.2l1.4 1.4M17.4 17.4l1.4 1.4M18.8 5.2l-1.4 1.4M6.6 17.4l-1.4 1.4"/>
      </svg>
    </button>
    <div class="marke">
      <img src="logo.png" alt="Wappen der HSG Oberer Neckar" width="48" height="48">
      <div>
        <p class="zeile1">HSG Oberer Neckar</p>
        <h1>Herren</h1>
      </div>
    </div>
    <p class="liga">{liga} &middot; {bereich}</p>
  </div>
</div>
<div class="huelle">

  <div class="teil">
    {naechstes_spiel}
  </div>

  <nav class="reiter" role="tablist">
    <button type="button" role="tab" aria-selected="true" aria-controls="feld-spiele" id="reiter-spiele">Spiele</button>
    <button type="button" role="tab" aria-selected="false" aria-controls="feld-tabelle" id="reiter-tabelle">Tabelle</button>
    <button type="button" role="tab" aria-selected="false" aria-controls="feld-statistiken" id="reiter-statistiken">Statistiken</button>
    <button type="button" role="tab" aria-selected="false" aria-controls="feld-kalender" id="reiter-kalender">Kalender</button>
  </nav>

  <div id="feld-spiele" role="tabpanel" aria-labelledby="reiter-spiele">
    <div class="teil">
      {spielplan}
    </div>
  </div>

  <div id="feld-tabelle" role="tabpanel" aria-labelledby="reiter-tabelle" hidden>
    <div class="teil">
      <table>
        <thead>
          <tr><th></th><th>Mannschaft</th><th class="rechts">Sp.</th><th class="rechts">S:U:N</th><th class="rechts">Tore</th><th class="rechts">Punkte</th></tr>
        </thead>
        <tbody>{tabelle}</tbody>
      </table>
    </div>
  </div>

  <div id="feld-statistiken" role="tabpanel" aria-labelledby="reiter-statistiken" hidden>
    <div class="teil statistiken">
      <p>Der Verband führt auf Ebene der Bezirksoberliga keine Spielberichte mit Torschützen,
      Torverlauf oder Zeitstrafen &ndash; anders als in höheren Ligen (Landesliga, Oberliga,
      Regionalliga), wo handball4all das anbietet.</p>
      <div class="hinweis">
        <p>Das ist keine Lücke auf dieser Seite, sondern eine Grenze der Quelle: handball4all
        markiert das selbst (<code>scoreShowDataPerGame: false</code> für diese Liga). Sollte die
        Mannschaft einmal in eine Liga mit Spielberichten aufsteigen, kommt dieser Reiter mit
        echten Inhalten.</p>
      </div>
    </div>
  </div>

  <div id="feld-kalender" role="tabpanel" aria-labelledby="reiter-kalender" hidden>
    <div class="teil">
      {kalender}
    </div>
  </div>

  <div class="fuss">
    <p>Inoffizielle Seite eines Vereinsmitglieds, kein offizielles Angebot der HSG Oberer Neckar.</p>
    <p>Daten von handball4all (Baden-W&uuml;rttembergischer Handball-Verband), Stand: {quelle_stand}.</p>
    <p>Zuletzt geholt: {geholt_am}.</p>
  </div>

</div>
<script>
(function () {{
  var reiter = document.querySelectorAll('.reiter button');
  reiter.forEach(function (knopf) {{
    knopf.addEventListener('click', function () {{
      reiter.forEach(function (r) {{
        r.setAttribute('aria-selected', r === knopf ? 'true' : 'false');
        document.getElementById(r.getAttribute('aria-controls')).hidden = r !== knopf;
      }});
    }});
  }});
}})();
(function () {{
  var SCHLUESSEL = 'oberer-neckar-ansicht';
  var wurzel = document.documentElement;
  var knopf = document.getElementById('ansicht');

  function gespeichert() {{
    try {{ return localStorage.getItem(SCHLUESSEL) || ''; }} catch (e) {{ return ''; }}
  }}
  function istDunkel() {{
    var wahl = wurzel.getAttribute('data-ansicht');
    if (wahl) return wahl === 'dunkel';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }}
  function beschrifte() {{
    if (!knopf) return;
    knopf.setAttribute('aria-label',
      istDunkel() ? 'Zu heller Ansicht wechseln' : 'Zu dunkler Ansicht wechseln');
  }}

  var wahl = gespeichert();
  if (wahl === 'hell' || wahl === 'dunkel') wurzel.setAttribute('data-ansicht', wahl);
  beschrifte();

  if (knopf) {{
    knopf.addEventListener('click', function () {{
      var neu = istDunkel() ? 'hell' : 'dunkel';
      wurzel.setAttribute('data-ansicht', neu);
      try {{ localStorage.setItem(SCHLUESSEL, neu); }} catch (e) {{}}
      var meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute('content', neu === 'dunkel' ? '#000000' : '#0a2c73');
      beschrifte();
    }});
  }}

  var beobachter = window.matchMedia('(prefers-color-scheme: dark)');
  if (beobachter.addEventListener) {{
    beobachter.addEventListener('change', function () {{
      if (!gespeichert()) beschrifte();
    }});
  }}
}})();
(function () {{
  document.querySelectorAll('[data-kopiere]').forEach(function (k) {{
    k.addEventListener('click', function () {{
      var text = k.getAttribute('data-kopiere');
      navigator.clipboard.writeText(text).then(function () {{
        var alt = k.textContent;
        k.textContent = 'Adresse kopiert';
        setTimeout(function () {{ k.textContent = alt; }}, 1800);
      }});
    }});
  }});
}})();
</script>
</body>
</html>
"""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--daten", default="daten.json")
    p.add_argument("--out", default="docs/index.html")
    p.add_argument("--basis-url", default="https://beatzep.github.io/oberer-neckar-kalender")
    cfg = p.parse_args()

    daten = json.loads(Path(cfg.daten).read_text(encoding="utf-8"))
    seite = SEITE.format(
        liga=daten["liga"],
        bereich=daten["bereich"],
        naechstes_spiel=baue_naechstes_spiel(naechstes_spiel(daten["spiele"])),
        tabelle=baue_tabelle(daten["tabelle"]),
        spielplan=baue_spielplan(daten["spiele"]),
        kalender=baue_kalender_block(cfg.basis_url),
        quelle_stand=daten["quelle_stand"],
        geholt_am=datetime.fromisoformat(daten["geholt_am"]).strftime("%d.%m.%Y %H:%M"),
    )
    Path(cfg.out).write_text(seite, encoding="utf-8")
    print(f"-> {cfg.out}")


if __name__ == "__main__":
    main()
