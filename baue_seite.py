#!/usr/bin/env python3
"""Baut aus daten.json die statische Seite docs/index.html: Mannschaftswahl
oben, darunter naechstes Spiel fest und Reiter fuer Spielplan, Tabelle,
Statistiken und Kalender - fuer alle Mannschaften aus teams.json auf einer
Seite, umgeschaltet per JavaScript wie im MuRu-Projekt (dort "verschraenkte
Ansicht" genannt). Formensprache ebenfalls von dort (dunkler Kopf, scharfe
Kanten, duenne Linien statt Karten, automatisch hell/dunkel, Countdown,
Aenderungserkennung), Farben sind die echten Vereinsfarben der HSG Oberer
Neckar (aus dem Logo auf hsg-oberer-neckar.de ausgelesen: Navy #0a2c73,
Gold #ffda06) statt frei erfunden."""

import argparse
import json
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote

import auswertung
from spielberichte import PDF_URL

MONATE = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]
TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def kurzdatum(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    return f"{TAGE[d.weekday()]} {d:%d.%m.%y}"


def kartenlink(halle: str) -> str:
    """Wie im MuRu-Projekt (baue_seite.py, kartenlink): Google-Maps-Suche aus
    dem Hallennamen samt Adresse, kein eigener Geokodierungs-Aufwand noetig."""
    return "https://www.google.com/maps/search/?api=1&query=" + quote(halle)


def relativ(termin: str, heute: datetime) -> str:
    """Wie im MuRu-Projekt (baue_seite.py, hero): der Marker ueber dem
    naechsten Spiel sagt, wie bald es losgeht, statt immer nur "Nächstes
    Spiel" zu wiederholen."""
    tage = (datetime.fromisoformat(termin).date() - heute.date()).days
    if tage == 0:
        return "Heute"
    if tage == 1:
        return "Morgen"
    if 1 < tage < 7:
        return f"In {tage} Tagen"
    return "Nächstes Spiel"


def naechstes_spiel(spiele: list[dict], heute: datetime) -> dict | None:
    kommende = [s for s in spiele
                if s["tore_eigene"] is None
                and datetime.fromisoformat(s["termin"]) >= heute.replace(hour=0, minute=0)]
    return kommende[0] if kommende else None


def baue_naechstes_spiel(team: dict, heute: datetime) -> str:
    spiel = naechstes_spiel(team["spiele"], heute)
    if spiel is None:
        return """
    <p class="marker">Nächstes Spiel</p>
    <p class="paarung">Keins angesetzt</p>
    <p class="hinweistext">Entweder ist die Saison vorbei, oder handball4all hat für die
    Mannschaft noch keine weiteren Termine veröffentlicht.</p>"""

    eigener_anzeigename = f"HSG Oberer Neckar {team['name']}"
    zeilen = [f'<dt>Datum</dt><dd>{kurzdatum(spiel["termin"])}</dd>']
    if spiel["uhrzeit_bekannt"]:
        zeit = datetime.fromisoformat(spiel["termin"]).strftime("%H:%M")
        zeilen.append(f'<dt>Anwurf</dt><dd>{zeit} Uhr</dd>')
    else:
        zeilen.append('<dt>Anwurf</dt><dd>Noch nicht angesetzt</dd>')
    zeilen.append(f'<dt>Ort</dt><dd>{"Heimspiel" if spiel["heim"] else "Auswärtsspiel"}</dd>')
    if spiel["halle"]:
        zeilen.append(f'<dt>Halle</dt><dd><a href="{kartenlink(spiel["halle"])}" '
                      f'target="_blank" rel="noopener">{spiel["halle"]}</a></dd>')

    paarung = (f'{eigener_anzeigename} <span class="gegen">–</span> {spiel["gegner"]}' if spiel["heim"]
               else f'{spiel["gegner"]} <span class="gegen">–</span> {eigener_anzeigename}')

    countdown = ""
    if spiel["uhrzeit_bekannt"]:
        countdown = f'<p class="countdown" data-countdown="{spiel["termin"]}"></p>'

    return f"""
    <p class="marker">{relativ(spiel['termin'], heute)} &middot; {'Heimspiel' if spiel['heim'] else 'Auswärtsspiel'}</p>
    <p class="paarung">{paarung}</p>
    {countdown}
    <dl class="fakten">{''.join(zeilen)}</dl>"""


def baue_aenderungen(team: dict) -> str:
    """Wie im MuRu-Projekt (baue_seite.py, aenderungsblock): Aenderungen
    verschwinden von selbst wieder, sobald der naechste Lauf keine neuen
    findet - kein eigener Dismiss-Mechanismus noetig."""
    aenderungen = team.get("aenderungen") or []
    if not aenderungen:
        return ""
    punkte = "".join(f"<li>{a}</li>" for a in aenderungen)
    text = (f"Spielplan {team['name']} – Änderung:\n"
            + "\n".join("• " + a for a in aenderungen))
    return f"""<div class="hinweis">
      <h3>Zuletzt geändert</h3>
      <ul>{punkte}</ul>
      <button type="button" data-teile="{text}">Änderung weitergeben</button>
    </div>"""


def baue_tabelle(team: dict) -> str:
    zeilen = []
    for row in team["tabelle"]:
        eigene = ' class="eigene"' if row["team"] == team["name_tabelle"] else ""
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
    return f"""<table>
      <thead>
        <tr><th></th><th>Mannschaft</th><th class="rechts">Sp.</th><th class="rechts">S:U:N</th><th class="rechts">Tore</th><th class="rechts">Punkte</th></tr>
      </thead>
      <tbody>{''.join(zeilen)}</tbody>
    </table>"""


def spielfilm(punkte: list[tuple[int, int, int]], kennung: str, beschreibung: str) -> str:
    """Der Spielverlauf als Kurve der Tordifferenz aus eigener Sicht, wie im
    MuRu-Projekt (baue_seite.py, spielfilm): ueber der Nulllinie Fuehrung,
    darunter Rueckstand. Liest sich auf dem Handy in einer Sekunde, zwei
    nebeneinanderlaufende Kurven muesste man erst vergleichen. Gezeichnet als
    Treppe, weil sich der Abstand nur mit einem Tor aendert."""
    reihe = [(s, e - g) for s, e, g in punkte]
    dauer = max(3600, reihe[-1][0])
    # Nicht symmetrisch skalieren: wer nie zurueckliegt, verschenkt sonst die
    # halbe Hoehe. Die Nulllinie bleibt trotzdem im Bild - sie traegt die Aussage.
    hoch = max(2, max(d for _, d in reihe))
    tief = min(-2, min(d for _, d in reihe))

    breite, hoehe = 320, 112
    links, rechts, oben, unten = 24, 6, 8, 18
    flaeche_b, flaeche_h = breite - links - rechts, hoehe - oben - unten

    def x(s: int) -> float:
        return links + flaeche_b * min(s, dauer) / dauer

    def y(d: int) -> float:
        return oben + flaeche_h * (hoch - d) / (hoch - tief)

    stufen = [(x(0), y(0))]
    for (_, vorher), (s, d) in zip(reihe, reihe[1:]):
        stufen += [(x(s), y(vorher)), (x(s), y(d))]
    stufen.append((x(dauer), y(reihe[-1][1])))
    linie = " ".join(f"{a:.1f},{b:.1f}" for a, b in stufen)
    null = y(0)
    flaeche = f"{x(0):.1f},{null:.1f} {linie} {x(dauer):.1f},{null:.1f}"
    unten_y = hoehe - unten
    # Beschriftung links; was naeher als eine Zeilenhoehe an der Null liegt,
    # entfaellt, sonst stehen bei einem klaren Spiel "0" und "-2" aufeinander.
    achse = f'<text x="{links - 4}" y="{null + 3:.1f}" text-anchor="end">0</text>'
    if null - y(hoch) >= 14:
        achse += f'<text x="{links - 4}" y="{y(hoch) + 7:.1f}" text-anchor="end">+{hoch}</text>'
    if y(tief) - null >= 14:
        achse += f'<text x="{links - 4}" y="{y(tief):.1f}" text-anchor="end">{tief}</text>'

    return f"""<svg class="spielfilm" viewBox="0 0 {breite} {hoehe}" role="img" aria-label="{escape(beschreibung)}">
  <defs>
    <clipPath id="vorn-{kennung}"><rect x="0" y="0" width="{breite}" height="{null:.1f}"/></clipPath>
    <clipPath id="hinten-{kennung}"><rect x="0" y="{null:.1f}" width="{breite}" height="{hoehe - null:.1f}"/></clipPath>
  </defs>
  <polygon class="vorn" points="{flaeche}" clip-path="url(#vorn-{kennung})"/>
  <polygon class="hinten" points="{flaeche}" clip-path="url(#hinten-{kennung})"/>
  <line class="gitter" x1="{x(1800):.1f}" y1="{oben}" x2="{x(1800):.1f}" y2="{unten_y}"/>
  <line class="null" x1="{links}" y1="{null:.1f}" x2="{breite - rechts}" y2="{null:.1f}"/>
  <polyline class="linie" points="{linie}"/>
  {achse}
  <text x="{x(1800):.1f}" y="{hoehe - 4}" text-anchor="middle">Halbzeit</text>
  <text x="{breite - rechts}" y="{hoehe - 4}" text-anchor="end">60'</text>
</svg>"""


def siebenmeter_text(tore: int, wuerfe: int) -> str:
    return f" ({tore}/{wuerfe} 7m)" if wuerfe else ""


def baue_spielbericht(spiel: dict, bericht: dict) -> str:
    """Was unter einem gespielten Spiel aufklappt: Eckdaten, Verlaufskurve,
    Laeufe, Torschuetzen, Strafen und der Weg zum Original."""
    a = auswertung.spiel_auswertung(spiel, bericht)
    eck = []
    if spiel.get("halbzeit_eigene") is not None:
        eck.append(f"Halbzeit {spiel['halbzeit_eigene']}:{spiel['halbzeit_gegner']}")
    if a["zuschauer"]:
        eck.append(f"{a['zuschauer']} Zuschauer")

    l = a["laeufe"]
    lauf = []
    if l["eigene"] >= auswertung.LAUF_AB:
        lauf.append(f"{l['eigene']} Tore in Folge ab der {l['eigene_ab']}. Minute.")
    if l["fremde"] >= auswertung.LAUF_AB:
        lauf.append(f"Der Gegner traf {l['fremde']}-mal in Folge ab der {l['fremde_ab']}. Minute.")
    lauftext = f'<p class="lauf">{" ".join(lauf)}</p>' if lauf else ""

    namen = ", ".join(f"{escape(s['name'])} {s['tore']}"
                      + siebenmeter_text(s["siebenmeter_tore"], s["siebenmeter_wuerfe"])
                      for s in a["schuetzen"])
    strafen = f"Zeitstrafen {a['zeitstrafen'][0]}, beim Gegner {a['zeitstrafen'][1]}"
    disq_eigen, disq_fremd = a["disqualifikationen"]
    if disq_eigen or disq_fremd:
        strafen += f". Rote Karten {disq_eigen}, beim Gegner {disq_fremd}"

    wann = datetime.fromisoformat(spiel["termin"]).strftime("%d.%m.")
    beschreibung = (f"Spielverlauf {wann} {'gegen' if spiel['heim'] else 'bei'} {spiel['gegner']}, "
                    f"Endstand {spiel['tore_eigene']}:{spiel['tore_gegner']}")
    return f"""<div class="bericht">
            {f'<p class="eck">{" · ".join(eck)}</p>' if eck else ""}
            {spielfilm(a["verlauf"], spiel["bericht_id"], beschreibung)}
            {lauftext}
            <p><span class="rubrikklein">Tore</span> {namen or "keine"}</p>
            <p><span class="rubrikklein">Strafen</span> {strafen}.</p>
            <p class="quelle"><a href="{PDF_URL.format(spiel['bericht_id'])}" target="_blank"
               rel="noopener">Original-Spielbericht (PDF)</a></p>
          </div>"""


def baue_spielplan(team: dict, berichte: dict | None = None) -> str:
    berichte = berichte or {}
    zeilen = []
    letzter_monat = None
    for spiel in team["spiele"]:
        beginn = datetime.fromisoformat(spiel["termin"])
        monat = (beginn.year, beginn.month)
        if monat != letzter_monat:
            zeilen.append(f'<p class="monat">{MONATE[beginn.month]} {beginn.year}</p>')
            letzter_monat = monat

        vorbei = spiel["tore_eigene"] is not None
        klassen = "spiel" + (" vorbei" if vorbei else "")
        bericht = auswertung.bericht_zu(spiel, berichte) if vorbei else None

        if vorbei:
            eig, frd = spiel["tore_eigene"], spiel["tore_gegner"]
            ausgang = "S" if eig > frd else "N" if eig < frd else "U"
            stand = f'<div class="stand {ausgang}">{eig}:{frd}</div>'
            if spiel.get("halbzeit_eigene") is not None:
                stand += f'<div class="hzstand">HZ {spiel["halbzeit_eigene"]}:{spiel["halbzeit_gegner"]}</div>'
            if bericht:
                stand += '<div class="aufklapp">Bericht</div>'
        else:
            zeit = (datetime.fromisoformat(spiel["termin"]).strftime("%H:%M") + " Uhr"
                    if spiel["uhrzeit_bekannt"] else "offen")
            stand = f'<div class="stand">{zeit}</div>'

        if not spiel["halle"]:
            halle = ""
        elif bericht:
            # In der aufklappbaren Zeile kein Kartenlink: auf schmalen Handys
            # (320 px) liegt die umbrochene Adresse mitten in der Zeile, und
            # wer den Bericht aufklappen will, landet sonst bei Google Maps.
            # Zum gespielten Spiel braucht ohnehin niemand mehr den Weg.
            halle = f'<div class="halle">{spiel["halle"]}</div>'
        else:
            halle = (f'<div class="halle"><a href="{kartenlink(spiel["halle"])}" '
                     f'target="_blank" rel="noopener">{spiel["halle"]}</a></div>')

        inhalt = f"""
          <div class="datum">{kurzdatum(spiel['termin'])}<span>{'Heim' if spiel['heim'] else 'Auswärts'}</span></div>
          <div>
            <div class="gegner">{spiel['gegner']}</div>
            {halle}
          </div>
          <div class="rechts">{stand}</div>"""
        if bericht:
            # Mit Bericht wird die Zeile aufklappbar. Die Klasse .spiel sitzt
            # auf dem summary, nicht auf dem <details>: sonst schluege die
            # Deckkraft von .vorbei auf den aufgeklappten Bericht durch (im
            # MuRu-Projekt schon einmal zugeschnappt, siehe CLAUDE.md dort).
            zeilen.append(f"""
        <details class="mitbericht">
          <summary class="{klassen}">{inhalt}
          </summary>
          {baue_spielbericht(spiel, bericht)}
        </details>""")
        else:
            zeilen.append(f"""
        <div class="{klassen}">{inhalt}
        </div>""")
    return "".join(zeilen)


def kennzahl(titel: str, wert: str, zusatz: str = "") -> str:
    return (f'<div><dt>{titel}</dt><dd><span class="wert">{wert}</span>'
            + (f'<span class="zusatz">{zusatz}</span>' if zusatz else "") + '</dd></div>')


def komma(wert: float) -> str:
    return f"{wert:.1f}".replace(".", ",")


def vorzeichen(n: int) -> str:
    return f"+{n}" if n > 0 else ("±0" if n == 0 else f"−{-n}")


def quellenhinweis(q: dict) -> str:
    """Wie im MuRu-Projekt: fehlt etwas, liegt es an der Quelle, und das
    gehoert auch so dagesagt - statt einer Luecke, die aussieht wie ein Fehler."""
    if not q["ohne_bericht"]:
        return (f'<p class="statfuss">Grundlage: die Spielberichte aller '
                f'{q["gespielt"]} bisherigen Spiele.</p>')
    fehlend = ", ".join(f'{kurzdatum(s["termin"])} {"gegen" if s["heim"] else "bei"} {escape(s["gegner"])}'
                        for s in q["ohne_bericht"])
    return (f'<p class="statfuss">Grundlage: {q["mit_bericht"]} von {q["gespielt"]} Spielen. '
            f'Zu {fehlend} hat der Verband noch keinen Spielbericht veröffentlicht '
            f'(oder er passt nicht zum gemeldeten Endstand und wurde deshalb nicht übernommen).</p>')


def baue_statistiken(team: dict, berichte: dict | None = None) -> str:
    s = auswertung.saison_auswertung(team, berichte or {})
    q = s["quelle"]
    if not q["gespielt"]:
        return """
      <p class="hinweistext">Noch kein Spiel gespielt. Sobald der Verband den ersten
      Spielbericht veröffentlicht, stehen hier Torschützen, Siebenmeter und Zeitstrafen.</p>"""

    zahlen = [kennzahl("Tore je Spiel", komma(s["tore"][0] / q["gespielt"]),
                       f'{komma(s["tore"][1] / q["gespielt"])} kassiert')]
    if s["halbzeiten"]:
        h = s["halbzeiten"]
        zahlen.append(kennzahl("Halbzeiten", f'{vorzeichen(h["erste"])} / {vorzeichen(h["zweite"])}',
                               "Tordifferenz in 1. und 2. Halbzeit"))
    if q["mit_bericht"]:
        tore, wuerfe = s["siebenmeter"]
        if wuerfe:
            zahlen.append(kennzahl("Siebenmeter", f"{round(100 * tore / wuerfe)} %",
                                   f"{tore} von {wuerfe} verwandelt"))
        zahlen.append(kennzahl("Zeitstrafen", str(s["zeitstrafen"][0]),
                               f'beim Gegner {s["zeitstrafen"][1]}'))
    kennzahlen = f'<dl class="kennzahlen">{"".join(zahlen)}</dl>'

    if not s["schuetzen"]:
        return kennzahlen + quellenhinweis(q)

    zeilen = []
    for i, sp in enumerate(s["schuetzen"], 1):
        # Siebenmeter und Strafen hinter dem Namen statt in eigenen Spalten:
        # die fielen auf dem Handy weg, und dort schaut die Mehrheit.
        beiwerk = [f'{sp["spiele"]} {"Spiel" if sp["spiele"] == 1 else "Spiele"}']
        if sp["siebenmeter_wuerfe"]:
            beiwerk.append(f'7m {sp["siebenmeter_tore"]}/{sp["siebenmeter_wuerfe"]}')
        if sp["zeitstrafen"]:
            beiwerk.append(f'{sp["zeitstrafen"]}× 2 Min')
        zeilen.append(f"""
        <tr>
          <td class="platz">{i}</td>
          <td>{escape(sp['name'])}<span class="klein"> · {' · '.join(beiwerk)}</span></td>
          <td class="rechts">{komma(sp['tore_je_spiel'])}</td>
          <td class="rechts stark">{sp['tore']}</td>
        </tr>""")
    return f"""
      {kennzahlen}
      <p class="rubrik">Torschützen</p>
      <table class="schuetzen">
        <thead><tr><th></th><th>Spieler</th><th class="rechts">/Sp.</th><th class="rechts">Tore</th></tr></thead>
        <tbody>{''.join(zeilen)}</tbody>
      </table>
      {quellenhinweis(q)}"""


def baue_kalender_block(verein: str, team: dict, basis_url: str) -> str:
    """Drei Wege in den Kalender, wie im MuRu-Projekt (abo_block): Abo per
    webcal fuer Apple-Geraete (mit Fallback ueber die Kalender-App selbst,
    falls der Link-Klick stillschweigend nichts tut), Abo per URL fuer
    Google Kalender, einmaliger Download ohne Abo."""
    ics_url = f"{basis_url.rstrip('/')}/{team['datei']}"
    webcal = ics_url.replace("https://", "webcal://").replace("http://", "webcal://")
    eigene = f"{verein} {team['name']}"
    return f"""
    <div class="weg">
      <h3>iPhone, iPad und Mac</h3>
      <p>Antippen, „Abonnieren" bestätigen. Verlegungen und neue Ergebnisse ziehen
      sich danach automatisch nach, ohne dass du noch mal hier vorbeischauen musst.</p>
      <a class="knopf" href="{webcal}">{eigene} abonnieren</a>
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
      <a class="knopf stumm" href="{team['datei']}" download>Datei herunterladen</a>
    </div>"""


def baue_team_block(schluessel: str, verein: str, team: dict, basis_url: str, heute: datetime,
                    erstes: bool, berichte: dict) -> str:
    versteckt = "" if erstes else " hidden"
    return f"""
  <div class="mannschaft" data-team="{schluessel}"{versteckt}>
    <div class="teil">
      {baue_aenderungen(team)}
      {baue_naechstes_spiel(team, heute)}
    </div>

    <div id="feld-spiele-{schluessel}" data-panel="spiele" role="tabpanel">
      <div class="teil">
        {baue_spielplan(team, berichte)}
      </div>
    </div>

    <div id="feld-tabelle-{schluessel}" data-panel="tabelle" role="tabpanel" hidden>
      <div class="teil">
        {baue_tabelle(team)}
      </div>
    </div>

    <div id="feld-statistiken-{schluessel}" data-panel="statistiken" role="tabpanel" hidden>
      <div class="teil statistiken">
        {baue_statistiken(team, berichte)}
      </div>
    </div>

    <div id="feld-kalender-{schluessel}" data-panel="kalender" role="tabpanel" hidden>
      <div class="teil">
        {baue_kalender_block(verein, team, basis_url)}
      </div>
    </div>
  </div>"""


def baue_saisonwahl(aktuelle_saison: str, archiv_manifest: list[dict]) -> str:
    """Nur sichtbar, sobald es ueberhaupt eine archivierte Saison gibt - vorher
    saehe eine Auswahl mit einem einzigen Eintrag nur nach ungenutzter
    Bedienung aus."""
    if not archiv_manifest:
        return ""
    optionen = [f'<option value="aktuell">{aktuelle_saison} (aktuell)</option>']
    for eintrag in sorted(archiv_manifest, key=lambda e: e["schluessel"], reverse=True):
        optionen.append(f'<option value="{eintrag["schluessel"]}">{eintrag["label"]}</option>')
    return f"""<div class="wahl saison">
      <label for="saisonwahl">Saison</label>
      <select id="saisonwahl">{''.join(optionen)}</select>
    </div>"""


def baue_saisonbanner(saison: str, saison_abgeschlossen: bool) -> str:
    if not saison_abgeschlossen:
        return ""
    return f"""<div class="saisonbanner">
      <p>Die Saison {saison} ist für alle drei Mannschaften beendet. Die neue Saison
      erscheint hier, sobald der Verband die Termine veröffentlicht.</p>
    </div>"""


def baue_archiv_team(team: dict, berichte: dict) -> str:
    return f"""<div class="archivteam">
      <h3>{team['name']}</h3>
      {baue_tabelle(team)}
      <div style="margin-top: 24px">{baue_spielplan(team, berichte)}</div>
    </div>"""


def baue_archivbloecke(archiv_manifest: list[dict], archiv_verzeichnis: Path, berichte: dict) -> str:
    """Vollstaendig vorgerendert beim Bauen, kein Nachladen im Browser noetig
    - die paar Kilobyte je vergangener Saison fallen bei einem Vereinskalender
    nicht ins Gewicht, dafuer bleiben Spielplan/Tabelle-Funktionen unveraendert
    wiederverwendbar."""
    bloecke = []
    for eintrag in archiv_manifest:
        pfad = archiv_verzeichnis / f"{eintrag['schluessel']}.json"
        if not pfad.exists():
            continue
        archiv_daten = json.loads(pfad.read_text(encoding="utf-8"))
        teams_html = "".join(baue_archiv_team(t, berichte) for t in archiv_daten["teams"].values())
        bloecke.append(f"""
  <div class="archiv" data-archivsaison="{eintrag['schluessel']}" hidden>
    <p class="rubrik">Saison {eintrag['label']} &ndash; archiviert, keine weitere Aktualisierung</p>
    {teams_html}
  </div>""")
    return "".join(bloecke)


SEITE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HSG Oberer Neckar – Spielplan</title>
<meta name="description" content="Spielplan, Tabelle und nächstes Spiel der Herren-, Herren-II- und Damen-Mannschaft der HSG Oberer Neckar.">
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
  --kurve: #0a2c73;
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
    --kurve: #ffe14d;
  }}
}}
:root[data-ansicht="dunkel"] {{
  --gold: #ffe14d; --gold-tief: #ffda06; --gold-schwach: rgba(255,225,77,.14);
  --tinte: #f2efe8; --tinte-weich: #b8b4a9; --leise: #8c877c;
  --linie: #2c3550; --linie-zart: #1c2440;
  --grund: #0b0e1c; --marine: #000000; --auf-marine: #f3f5fa;
  --sieg: #5cbf85; --niederlage: #e08076;
  --kurve: #ffe14d;
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
.kopf h1 {{ margin: 2px 0 0; font-size: clamp(1.6rem, 7vw, 2.3rem); font-weight: 300;
            line-height: 1.06; letter-spacing: -.015em; }}

.wahl {{ margin: 22px 0 0; }}
.wahl label {{ display: block; font-size: .74rem; font-weight: 600; letter-spacing: .08em;
               text-transform: uppercase; color: rgba(243,245,250,.5); margin-bottom: 8px; }}
.wahl select {{
  appearance: none; -webkit-appearance: none; width: 100%;
  font: inherit; font-size: 1.05rem; font-weight: 600;
  color: var(--auf-marine); background: transparent;
  border: 1px solid rgba(243,245,250,.28); padding: 13px 44px 13px 14px;
  background-image: linear-gradient(45deg, transparent 50%, var(--gold) 50%),
                    linear-gradient(135deg, var(--gold) 50%, transparent 50%);
  background-position: calc(100% - 21px) 22px, calc(100% - 15px) 22px;
  background-size: 6px 6px, 6px 6px; background-repeat: no-repeat;
}}
.wahl select:focus-visible {{ outline: 2px solid var(--gold); outline-offset: 2px; }}
.wahl select option {{ color: #14140f; background: #fff; }}
.wahl.saison {{ margin: 0 0 16px; }}
.kopf .liga {{ margin: 14px 0 0; font-size: .9rem; color: rgba(243,245,250,.65); }}

.saisonbanner {{ border-left: 2px solid var(--gold); padding: 12px 0 12px 18px; margin: 26px 0 0; }}
.saisonbanner p {{ margin: 0; font-size: .95rem; color: var(--tinte-weich); }}

.archiv {{ padding: 30px 0 0; }}
.archiv .archivteam {{ padding: 26px 0; border-top: 1px solid var(--linie); }}
.archiv .archivteam:first-child {{ border-top: 0; }}
.archiv .archivteam h3 {{ margin: 0 0 16px; font-size: 1.1rem; font-weight: 600; }}

.teil {{ padding: 30px 0 0; }}
.rubrik {{ border-top: 1px solid var(--linie); padding-top: 14px; margin-bottom: 22px;
           font-size: .95rem; font-weight: 600; color: var(--leise); }}

.marker {{ font-size: .82rem; font-weight: 600; color: var(--gold-tief);
           letter-spacing: .04em; margin: 0 0 10px; }}
.paarung {{ font-size: clamp(1.3rem, 5.5vw, 1.7rem); font-weight: 400; line-height: 1.22;
            letter-spacing: -.01em; margin: 0 0 6px; overflow-wrap: anywhere; }}
.paarung .gegen {{ color: var(--leise); font-weight: 300; }}
.countdown {{ font-size: 1.02rem; font-weight: 600; color: var(--tinte);
              margin: 10px 0 18px; font-variant-numeric: tabular-nums; }}
.countdown .einheit {{ color: var(--leise); font-weight: 400; font-size: .9rem; }}
.fakten {{ margin: 0; }}
.fakten dt {{ float: left; width: 78px; color: var(--leise); font-size: .95rem;
              clear: left; padding: 11px 0; border-top: 1px solid var(--linie-zart); }}
.fakten dd {{ margin: 0 0 0 96px; font-size: .95rem; padding: 11px 0;
              border-top: 1px solid var(--linie-zart); }}
.fakten a {{ color: inherit; text-decoration: none; box-shadow: inset 0 -1px 0 var(--gold); }}
.fakten a:hover {{ box-shadow: inset 0 -2px 0 var(--gold); }}
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

/* ---------- Änderungen ---------- */
.hinweis {{ border-left: 2px solid var(--gold); padding: 4px 0 4px 18px; margin: 0 0 26px; }}
.hinweis h3 {{ margin: 0 0 8px; font-size: .82rem; font-weight: 600;
              letter-spacing: .04em; color: var(--gold-tief); }}
.hinweis p {{ font-size: .95rem; color: var(--tinte-weich); }}
.hinweis ul {{ margin: 0 0 14px; padding-left: 18px; font-size: .95rem; }}
.hinweis li {{ margin: 5px 0; }}
.hinweis button {{ font: inherit; font-size: .88rem; font-weight: 600;
                  background: none; border: 1px solid var(--linie);
                  color: var(--tinte); padding: 9px 16px; cursor: pointer; }}
.hinweis button:hover {{ border-color: var(--gold); background: var(--gold-schwach); }}

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
.spiel .halle a {{ color: inherit; text-decoration: none; box-shadow: inset 0 -1px 0 var(--linie); }}
.spiel .halle a:hover {{ box-shadow: inset 0 -1px 0 var(--gold); }}
.spiel .stand {{ font-size: .92rem; font-weight: 700; white-space: nowrap; }}
.spiel .stand.S {{ color: var(--sieg); }}
.spiel .stand.N {{ color: var(--niederlage); }}
.spiel .stand.U {{ color: var(--leise); }}
.spiel.vorbei {{ opacity: .55; }}
.spiel.vorbei .gegner {{ font-weight: 400; }}
.spiel .hzstand {{ font-size: .78rem; color: var(--leise); white-space: nowrap; margin-top: 2px; }}

/* ---------- Spielbericht zum Aufklappen ---------- */
/* Die Deckkraft von .vorbei sitzt auf dem summary, damit sie nicht auf den
   aufgeklappten Bericht durchschlaegt. */
details.mitbericht > summary {{ list-style: none; cursor: pointer; }}
details.mitbericht > summary::-webkit-details-marker {{ display: none; }}
details.mitbericht > summary:hover {{ opacity: .8; }}
details.mitbericht[open] > summary {{ opacity: 1; }}
details.mitbericht > summary:focus-visible {{ outline: 2px solid var(--gold); outline-offset: 2px; }}
.spiel .aufklapp {{ font-size: .74rem; font-weight: 600; letter-spacing: .04em;
                    text-transform: uppercase; color: var(--gold-tief); margin-top: 4px;
                    white-space: nowrap; }}
.spiel .aufklapp::after {{ content: " ▾"; }}
details[open] .spiel .aufklapp::after {{ content: " ▴"; }}
.bericht {{ padding: 4px 0 18px 76px; font-size: .9rem; color: var(--tinte-weich); }}
.bericht p {{ margin: 8px 0 0; }}
.bericht .eck {{ margin: 0 0 6px; color: var(--leise); }}
.bericht .lauf {{ color: var(--tinte); }}
.bericht .quelle a {{ color: inherit; text-decoration: none; box-shadow: inset 0 -1px 0 var(--gold); }}
.rubrikklein {{ font-size: .74rem; font-weight: 600; letter-spacing: .06em;
                text-transform: uppercase; color: var(--leise); margin-right: 6px; }}
@media (max-width: 520px) {{ .bericht {{ padding-left: 0; }} }}

svg.spielfilm {{ display: block; width: 100%; max-width: 480px; height: auto; margin: 4px 0 2px; }}
svg.spielfilm .linie {{ fill: none; stroke: var(--kurve); stroke-width: 1.6; stroke-linejoin: round; }}
svg.spielfilm .vorn {{ fill: var(--sieg); opacity: .18; }}
svg.spielfilm .hinten {{ fill: var(--niederlage); opacity: .18; }}
svg.spielfilm .null {{ stroke: var(--leise); stroke-width: .8; }}
svg.spielfilm .gitter {{ stroke: var(--linie); stroke-width: .8; stroke-dasharray: 2 3; }}
svg.spielfilm text {{ fill: var(--leise); font-size: 9px; }}

/* ---------- Statistiken ---------- */
.kennzahlen {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
               gap: 0 22px; margin: 0 0 30px; }}
.kennzahlen > div {{ border-top: 1px solid var(--linie); padding: 12px 0 14px; }}
.kennzahlen dt {{ font-size: .78rem; font-weight: 600; letter-spacing: .04em;
                  text-transform: uppercase; color: var(--leise); }}
.kennzahlen dd {{ margin: 4px 0 0; }}
.kennzahlen .wert {{ display: block; font-size: 1.6rem; font-weight: 300; line-height: 1.2; }}
.kennzahlen .zusatz {{ display: block; font-size: .84rem; color: var(--leise); }}
table.schuetzen .klein {{ color: var(--leise); font-size: .82rem; }}
.statfuss {{ font-size: .86rem; color: var(--leise); margin: 18px 0 0; }}

.fuss {{ padding: 30px 0 40px; border-top: 1px solid var(--linie); margin-top: 34px;
         font-size: .86rem; color: var(--leise); }}
.fuss p {{ margin: 0 0 10px; }}
</style>
</head>
<body data-worker="{worker_url}">
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
        <h1>Spielplan</h1>
      </div>
    </div>
    {saisonwahl}
    <div id="aktuelle-mannschaftswahl">
      <div class="wahl">
        <label for="teamwahl">Mannschaft</label>
        <select id="teamwahl">{teamoptionen}</select>
      </div>
      <p class="liga" id="ligazeile"></p>
    </div>
  </div>
</div>
<div class="huelle">

  {saisonbanner}

  <div id="inhalt-aktuell">
  <nav class="reiter" role="tablist">
    <button type="button" role="tab" aria-selected="true" data-panel="spiele" data-ziel="spiele" id="reiter-spiele">Spiele</button>
    <button type="button" role="tab" aria-selected="false" data-panel="tabelle" data-ziel="tabelle" id="reiter-tabelle">Tabelle</button>
    <button type="button" role="tab" aria-selected="false" data-panel="statistiken" data-ziel="statistiken" id="reiter-statistiken">Statistiken</button>
    <button type="button" role="tab" aria-selected="false" data-panel="kalender" data-ziel="kalender" id="reiter-kalender">Kalender</button>
  </nav>

  {mannschaften}
  </div>

  {archivbloecke}

  <div class="fuss">
    <p>Inoffizielle Seite eines Vereinsmitglieds, kein offizielles Angebot der HSG Oberer Neckar.</p>
    <p>Daten von handball4all (Baden-W&uuml;rttembergischer Handball-Verband).</p>
    <p>Zuletzt geholt: {geholt_am}.</p>
  </div>

</div>
<script>
var LIGEN = {ligen_json};

(function () {{
  var wahl = document.getElementById('teamwahl');
  var ligazeile = document.getElementById('ligazeile');
  var SCHLUESSEL = 'oberer-neckar-team';

  function zeige(schluessel) {{
    document.querySelectorAll('[data-team]').forEach(function (el) {{
      el.hidden = el.getAttribute('data-team') !== schluessel;
    }});
    var info = LIGEN[schluessel];
    if (info && ligazeile) ligazeile.textContent = info.liga + ' · ' + info.bereich;
    try {{ localStorage.setItem(SCHLUESSEL, schluessel); }} catch (e) {{}}
  }}

  if (wahl) {{
    var gespeichert = '';
    try {{ gespeichert = localStorage.getItem(SCHLUESSEL) || ''; }} catch (e) {{}}
    if (gespeichert && LIGEN[gespeichert]) wahl.value = gespeichert;
    zeige(wahl.value);
    wahl.addEventListener('change', function () {{ zeige(wahl.value); }});
  }}
}})();

(function () {{
  var wahl = document.getElementById('saisonwahl');
  if (!wahl) return;
  var aktuell = document.getElementById('inhalt-aktuell');
  var mannschaftswahl = document.getElementById('aktuelle-mannschaftswahl');

  function zeige(schluessel) {{
    var istAktuell = schluessel === 'aktuell';
    aktuell.hidden = !istAktuell;
    mannschaftswahl.hidden = !istAktuell;
    document.querySelectorAll('[data-archivsaison]').forEach(function (el) {{
      el.hidden = el.getAttribute('data-archivsaison') !== schluessel;
    }});
  }}

  zeige(wahl.value);
  wahl.addEventListener('change', function () {{ zeige(wahl.value); }});
}})();

(function () {{
  var reiter = document.querySelectorAll('.reiter button');
  reiter.forEach(function (knopf) {{
    knopf.addEventListener('click', function () {{
      var panel = knopf.getAttribute('data-panel');
      reiter.forEach(function (r) {{
        r.setAttribute('aria-selected', r === knopf ? 'true' : 'false');
      }});
      document.querySelectorAll('[data-panel="' + panel + '"][role="tabpanel"]').forEach(function (p) {{
        p.hidden = false;
      }});
      document.querySelectorAll('[role="tabpanel"]:not([data-panel="' + panel + '"])').forEach(function (p) {{
        p.hidden = true;
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

(function () {{
  document.querySelectorAll('[data-teile]').forEach(function (k) {{
    k.addEventListener('click', function () {{
      var text = k.getAttribute('data-teile');
      if (navigator.share) {{
        navigator.share({{ text: text }}).catch(function () {{}});
        return;
      }}
      navigator.clipboard.writeText(text).then(function () {{
        var alt = k.textContent;
        k.textContent = 'In Zwischenablage kopiert';
        setTimeout(function () {{ k.textContent = alt; }}, 1800);
      }});
    }});
  }});
}})();

(function () {{
  var felder = [].slice.call(document.querySelectorAll('[data-countdown]'));
  if (!felder.length) return;

  function zweistellig(n) {{ return (n < 10 ? '0' : '') + n; }}

  function schreibe() {{
    var jetzt = Date.now();
    felder.forEach(function (el) {{
      var ziel = new Date(el.getAttribute('data-countdown')).getTime();
      if (isNaN(ziel)) return;
      var rest = Math.floor((ziel - jetzt) / 1000);

      if (rest <= 0) {{
        el.textContent = rest > -7200 ? 'Läuft gerade' : 'Angepfiffen';
        return;
      }}
      var tage = Math.floor(rest / 86400);
      var std = Math.floor((rest % 86400) / 3600);
      var min = Math.floor((rest % 3600) / 60);
      var sek = rest % 60;

      if (tage > 0) {{
        el.innerHTML = 'noch <span>' + tage + '</span> <span class="einheit">' +
          (tage === 1 ? 'Tag' : 'Tage') + '</span> <span>' + std +
          '</span> <span class="einheit">Std</span> <span>' + min +
          '</span> <span class="einheit">Min</span>';
      }} else {{
        el.innerHTML = 'noch <span>' + zweistellig(std) + ':' + zweistellig(min) +
          ':' + zweistellig(sek) + '</span> <span class="einheit">Std</span>';
      }}
    }});
  }}

  schreibe();
  setInterval(schreibe, 1000);
}})();

(function () {{
  var huelle = document.querySelector('[data-worker]');
  var worker = huelle && huelle.getAttribute('data-worker');
  if (!worker) return;

  var offen = {{ ereignis: {{}}, mannschaft: {{}}, bereich: {{}} }};
  var etwasOffen = false;

  function merke(gruppe, name) {{
    if (!name) return;
    offen[gruppe][name] = (offen[gruppe][name] || 0) + 1;
    etwasOffen = true;
  }}

  function sende(beimVerlassen) {{
    if (!etwasOffen) return;
    var last = JSON.stringify(offen);
    offen = {{ ereignis: {{}}, mannschaft: {{}}, bereich: {{}} }};
    etwasOffen = false;
    // application/json wuerde eine OPTIONS-Vorfrage ausloesen, die beim
    // Schliessen der Seite die einzige noch zugesagte Zustellung verbraucht
    // - wie im MuRu-Projekt (seite_zaehlung.py) erst muehsam herausgefunden.
    if (beimVerlassen && navigator.sendBeacon) {{
      var zugestellt = navigator.sendBeacon(worker + '/zaehl',
        new Blob([last], {{ type: 'text/plain' }}));
      if (zugestellt) return;
    }}
    fetch(worker + '/zaehl', {{
      method: 'POST', headers: {{ 'Content-Type': 'text/plain' }}, body: last,
      keepalive: !!beimVerlassen
    }}).catch(function () {{}});
  }}

  merke('ereignis', 'aufruf');
  var wahl = document.getElementById('teamwahl');
  if (wahl) merke('mannschaft', wahl.value);

  document.addEventListener('click', function (e) {{
    var ziel = e.target.closest('button, a');
    if (!ziel) return;
    if (ziel.hasAttribute('data-ziel')) merke('bereich', ziel.getAttribute('data-ziel'));
    else if (ziel.classList.contains('knopf') && ziel.getAttribute('href'))
      merke('ereignis', ziel.getAttribute('href').indexOf('webcal') === 0 ? 'abo' : 'datei');
    else if (ziel.hasAttribute('data-kopiere')) merke('ereignis', 'kopiert');
    else if (ziel.hasAttribute('data-teile')) merke('ereignis', 'teilen');
  }}, true);

  if (wahl) wahl.addEventListener('change', function () {{ merke('mannschaft', wahl.value); }});

  window.addEventListener('pagehide', function () {{ sende(true); }});
  document.addEventListener('visibilitychange', function () {{
    if (document.visibilityState === 'hidden') sende(true);
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
    p.add_argument("--worker-url", default="",
                    help="Ohne Angabe wird nichts gezaehlt - die Zaehlung schaltet sich "
                         "im Browser selbst ab (seite_zaehlung.py-Aequivalent unten).")
    p.add_argument("--archiv", default="docs/archiv")
    p.add_argument("--berichte", default="berichte.json",
                   help="Spielberichte aus spielberichte.py; fehlt die Datei, bleibt der "
                        "Spielplan ohne aufklappbare Berichte")
    cfg = p.parse_args()

    daten = json.loads(Path(cfg.daten).read_text(encoding="utf-8"))
    berichte_pfad = Path(cfg.berichte)
    berichte = (json.loads(berichte_pfad.read_text(encoding="utf-8"))
                if berichte_pfad.exists() else {})
    heute = datetime.now()
    verein = daten["verein"]

    schluessel_liste = list(daten["teams"].keys())
    teamoptionen = "".join(
        f'<option value="{s}">{daten["teams"][s]["name"]}</option>' for s in schluessel_liste)
    mannschaften = "".join(
        baue_team_block(s, verein, daten["teams"][s], cfg.basis_url, heute, i == 0, berichte)
        for i, s in enumerate(schluessel_liste))
    ligen_json = json.dumps(
        {s: {"liga": t["liga"], "bereich": t["bereich"]} for s, t in daten["teams"].items()},
        ensure_ascii=False)

    archiv_verzeichnis = Path(cfg.archiv)
    manifest_pfad = archiv_verzeichnis / "manifest.json"
    archiv_manifest = (json.loads(manifest_pfad.read_text(encoding="utf-8"))
                        if manifest_pfad.exists() else [])

    seite = SEITE.format(
        teamoptionen=teamoptionen,
        mannschaften=mannschaften,
        ligen_json=ligen_json,
        worker_url=cfg.worker_url,
        saisonwahl=baue_saisonwahl(daten.get("saison", ""), archiv_manifest),
        saisonbanner=baue_saisonbanner(daten.get("saison", ""), daten.get("saison_abgeschlossen", False)),
        archivbloecke=baue_archivbloecke(archiv_manifest, archiv_verzeichnis, berichte),
        geholt_am=datetime.fromisoformat(daten["geholt_am"]).strftime("%d.%m.%Y %H:%M"),
    )
    Path(cfg.out).write_text(seite, encoding="utf-8")
    print(f"-> {cfg.out}")


if __name__ == "__main__":
    main()
