#!/usr/bin/env python3
"""Baut docs/admin.html - die Nutzungsauswertung.

Die Seite selbst ist oeffentlich und zeigt nichts von sich aus; die Zahlen
liefert der Worker nur gegen Anmeldung (ADMIN_BENUTZER/ADMIN_PASSWORT als
Secrets). Struktur vom MuRu-Projekt uebernommen (baue_admin.py), aber ohne
Tipprunde - die gibt es hier nicht."""

import argparse

SKRIPT = """
(function () {
  var worker = document.body.getAttribute('data-worker');
  var form = document.getElementById('anmeldung');
  var feldBenutzer = document.getElementById('benutzer');
  var feldPasswort = document.getElementById('passwort');
  var meldung = document.getElementById('meldung');
  var bereich = document.getElementById('auswertung');
  var abmelden = document.getElementById('abmelden');

  function zahl(n) { return (n || 0).toLocaleString('de-DE'); }

  function kennzahl(titel, wert) {
    return '<div><dt>' + titel + '</dt><dd>' + wert + '</dd></div>';
  }

  function verlaufsbild(tage) {
    if (!tage.length) return '';
    var hoechst = Math.max.apply(null, tage.map(function (t) { return t.aufrufe; })) || 1;
    var B = 320, H = 110, unten = 22, links = 26;
    var breite = (B - links) / tage.length;
    var balken = tage.map(function (t, i) {
      var h = Math.round((H - unten - 8) * t.aufrufe / hoechst);
      return '<rect x="' + (links + i * breite + 1).toFixed(1) + '" y="' +
        (H - unten - h) + '" width="' + Math.max(breite - 2, 1).toFixed(1) +
        '" height="' + Math.max(h, t.aufrufe ? 1 : 0) + '" class="balken"><title>' +
        t.tag + ': ' + t.aufrufe + '</title></rect>';
    }).join('');
    var erster = tage[0].tag.slice(8) + '.' + tage[0].tag.slice(5, 7) + '.';
    var letzter = tage[tage.length - 1].tag.slice(8) + '.' +
                  tage[tage.length - 1].tag.slice(5, 7) + '.';
    return '<div class="verlauf"><div class="titel">Aufrufe je Tag</div>' +
      '<svg viewBox="0 0 ' + B + ' ' + H + '" role="img" aria-label="Aufrufe je Tag">' +
      '<line class="gitter" x1="' + links + '" y1="' + (H - unten) + '" x2="' + B +
      '" y2="' + (H - unten) + '"/>' +
      '<text x="0" y="14">' + hoechst + '</text>' +
      '<text x="0" y="' + (H - unten + 4) + '">0</text>' + balken +
      '<text x="' + links + '" y="' + (H - 4) + '">' + erster + '</text>' +
      '<text x="' + B + '" y="' + (H - 4) + '" text-anchor="end">' + letzter + '</text>' +
      '</svg></div>';
  }

  function aufschluesselung(titel, werte, namen) {
    var eintraege = Object.keys(werte || {});
    if (!eintraege.length) return '';
    var summe = eintraege.reduce(function (s, k) { return s + werte[k]; }, 0) || 1;
    var zeilen = eintraege.sort(function (a, b) { return werte[b] - werte[a]; })
      .map(function (k) {
        var anteil = Math.round(100 * werte[k] / summe);
        return '<tr><td>' + (namen[k] || k) + '</td><td class="anteil">' +
          '<span style="width:' + anteil + '%"></span></td>' +
          '<td class="pkt">' + zahl(werte[k]) + '</td></tr>';
      }).join('');
    return '<div class="rubrik">' + titel + '</div><table class="verteilung"><tbody>' +
      zeilen + '</tbody></table>';
  }

  function zeige(d) {
    var e = d.gesamt.ereignis || {};
    var heute = d.verlauf.length ? d.verlauf[d.verlauf.length - 1].aufrufe : 0;
    var woche = d.verlauf.slice(-7).reduce(function (s, t) { return s + t.aufrufe; }, 0);

    bereich.innerHTML =
      '<dl class="kennzahlen">' +
        kennzahl('Aufrufe heute', zahl(heute)) +
        kennzahl('Letzte 7 Tage', zahl(woche)) +
        kennzahl('Kalender abonniert', zahl(e.abo)) +
        kennzahl('Datei heruntergeladen', zahl(e.datei)) +
      '</dl>' +
      verlaufsbild(d.verlauf) +
      aufschluesselung('Nach Mannschaft', d.gesamt.mannschaft,
        { herren1: 'Herren', herren2: 'Herren II', damen: 'Damen' }) +
      aufschluesselung('Nach Reiter', d.gesamt.bereich,
        { spiele: 'Spiele', tabelle: 'Tabelle', statistiken: 'Statistiken',
          kalender: 'Kalender' }) +
      aufschluesselung('Aktionen', {
        abo: e.abo || 0, datei: e.datei || 0, kopiert: e.kopiert || 0, teilen: e.teilen || 0 },
        { abo: 'Kalender abonniert', datei: 'Datei geladen',
          kopiert: 'Adresse kopiert', teilen: 'Geteilt oder kopiert' }) +
      '<p class="statfuss">Gezählt werden Summen je Tag – ohne Kennung, ohne ' +
      'Adresse, ohne Wiedererkennung.</p>';
    bereich.hidden = false;
    form.hidden = true;
    abmelden.hidden = false;
  }

  function hole(benutzer, passwort) {
    meldung.textContent = 'Wird geladen …';
    meldung.className = 'meldung';
    fetch(worker + '/auswertung', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ benutzer: benutzer, passwort: passwort, tage: 30 })
    })
      .then(function (r) {
        return r.json().then(function (d) {
          return r.ok ? d : Promise.reject(d.fehler || 'Fehler ' + r.status);
        });
      })
      .then(function (d) {
        meldung.textContent = '';
        try { sessionStorage.setItem('oberer-neckar-admin', JSON.stringify([benutzer, passwort])); }
        catch (e) {}
        zeige(d);
      })
      .catch(function (f) {
        meldung.textContent = String(f);
        meldung.className = 'meldung schlecht';
      });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    hole(feldBenutzer.value.trim(), feldPasswort.value);
  });

  abmelden.addEventListener('click', function () {
    try { sessionStorage.removeItem('oberer-neckar-admin'); } catch (e) {}
    location.reload();
  });

  try {
    var gemerkt = JSON.parse(sessionStorage.getItem('oberer-neckar-admin') || 'null');
    if (gemerkt) hole(gemerkt[0], gemerkt[1]);
  } catch (e) {}
})();
"""

STIL = """
:root {
  --gold: #ffda06; --gold-tief: #d6b400;
  --tinte: #14140f; --tinte-weich: #4a4a42; --leise: #7a776d;
  --linie: #dedbd3; --linie-zart: #ebe9e3;
  --grund: #ffffff; --marine: #0a2c73; --auf-marine: #f3f5fa;
  --niederlage: #a4443a;
}
@media (prefers-color-scheme: dark) {
  :root {
    --gold: #ffe14d; --gold-tief: #ffda06;
    --tinte: #f2efe8; --tinte-weich: #b8b4a9; --leise: #8c877c;
    --linie: #2c3550; --linie-zart: #1c2440;
    --grund: #0b0e1c; --marine: #000000; --auf-marine: #f3f5fa;
    --niederlage: #e08076;
  }
}
*, *::before, *::after { box-sizing: border-box; border-radius: 0; }
body { margin: 0; background: var(--grund); color: var(--tinte);
  font: 400 17px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.huelle { max-width: 560px; margin: 0 auto; padding: 0 22px; }
.kopf { background: var(--marine); color: var(--auf-marine); border-bottom: 3px solid var(--gold); }
.kopf .huelle { padding: 26px 22px 30px; }
.kopf h1 { margin: 4px 0 0; font-size: 1.8rem; font-weight: 300; }
.kopf p { margin: 10px 0 0; font-size: .9rem; color: rgba(243,245,250,.65); }
.teil { padding: 30px 0; }
.anmeldung label { display: block; font-size: .82rem; color: var(--leise); margin: 0 0 6px; }
.anmeldung input { font: inherit; width: 100%; padding: 13px 14px; margin-bottom: 16px;
  background: transparent; color: var(--tinte); border: 1px solid var(--linie); }
.anmeldung button { font: inherit; font-size: .95rem; font-weight: 600; padding: 14px 22px;
  border: 1px solid var(--gold); background: var(--gold); color: #14140f; cursor: pointer; }
.anmeldung button:hover { background: var(--gold-tief); border-color: var(--gold-tief); }
.kennzahlen { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin: 0; }
.kennzahlen dt { font-size: .78rem; color: var(--leise); margin: 0 0 4px; }
.kennzahlen dd { margin: 0; font-size: 1.5rem; font-weight: 600; }
.verlauf { margin-top: 30px; }
.verlauf .titel { font-size: .78rem; color: var(--leise); margin-bottom: 8px; }
.verlauf svg { width: 100%; height: auto; }
.verlauf .balken { fill: var(--gold); }
.verlauf .gitter { stroke: var(--linie); stroke-width: 1; }
.verlauf text { font-size: 7px; fill: var(--leise); }
.rubrik { border-top: 1px solid var(--linie); padding-top: 14px; margin: 30px 0 14px;
  font-size: .95rem; font-weight: 600; color: var(--leise); }
table.verteilung { width: 100%; border-collapse: collapse; font-size: .92rem; }
table.verteilung td { padding: 10px 0; border-bottom: 1px solid var(--linie-zart); }
table.verteilung td.anteil { width: 45%; padding: 10px 14px; }
table.verteilung td.anteil span { display: block; height: 8px; background: var(--gold); min-width: 1px; }
table.verteilung td.pkt { text-align: right; font-weight: 600; white-space: nowrap; }
.statfuss { margin: 18px 0 0; font-size: .8rem; color: var(--leise); line-height: 1.45; }
.meldung { font-size: .9rem; color: var(--tinte-weich); }
.meldung.schlecht { color: var(--niederlage); }
#abmelden { font: inherit; font-size: .84rem; background: none; border: 0; padding: 0;
  color: var(--leise); text-decoration: underline; cursor: pointer; margin-top: 30px; }
[hidden] { display: none !important; }
"""


def main() -> None:
    p = argparse.ArgumentParser(description="Auswertungsseite bauen")
    p.add_argument("--worker-url", required=True)
    p.add_argument("--out", default="docs/admin.html")
    cfg = p.parse_args()

    seite = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auswertung – HSG Oberer Neckar</title>
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#0a2c73">
<style>{STIL}</style>
</head>
<body data-worker="{cfg.worker_url}">

<div class="kopf">
  <div class="huelle">
    <h1>Nutzung</h1>
    <p>HSG Oberer Neckar &middot; letzte 30 Tage</p>
  </div>
</div>

<main class="huelle">
  <form id="anmeldung" class="anmeldung teil">
    <label for="benutzer">Benutzer</label>
    <input id="benutzer" type="text" autocomplete="username" required>
    <label for="passwort">Passwort</label>
    <input id="passwort" type="password" autocomplete="current-password" required>
    <button type="submit">Anmelden</button>
    <p id="meldung" class="meldung"></p>
  </form>

  <div id="auswertung" class="teil" hidden></div>
  <button id="abmelden" type="button" hidden>Abmelden</button>
</main>

<script>{SKRIPT}</script>
</body>
</html>
"""
    with open(cfg.out, "w", encoding="utf-8") as f:
        f.write(seite)
    print(f"-> {cfg.out}")


if __name__ == "__main__":
    main()
