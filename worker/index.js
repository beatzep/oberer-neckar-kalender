/**
 * Aufrufzaehler fuer oberer-neckar-kalender.
 *
 * Bewusst kleiner als der MuRu-Worker (muru-zaehler): keine Tipprunde, kein
 * Hype-/Anwesenheits-Zaehler, kein GitHub-Sicherheitsnetz - nur, wie oft die
 * Seite aufgerufen wird, aufgeschluesselt nach Mannschaft und Reiter. Eigener
 * KV-Namespace, eigener Worker-Name: zaehlt unabhaengig vom MuRu-Zaehler,
 * auch wenn beide im selben Cloudflare-Account laufen.
 *
 * Ablage in KV: stat:<datum>:<teil> - JSON-Zwischenstand, ueber STAT_TEILE
 * Schluessel verteilt, damit gleichzeitige Aufrufe sich nicht gegenseitig
 * ueberschreiben (KV kennt kein atomares Erhoehen). Beim Auswerten wieder
 * zusammengezaehlt. Muster 1:1 aus dem MuRu-Worker uebernommen.
 */

const ERLAUBTE_HERKUNFT = [
  "https://beatzep.github.io",
  "http://localhost:8931",
];

const STAT_TEILE = 10;

const STAT_EREIGNISSE = ["aufruf", "abo", "datei", "kopiert", "teilen"];
const STAT_MANNSCHAFTEN = ["herren1", "herren2", "damen"];
const STAT_BEREICHE = ["spiele", "tabelle", "statistiken", "kalender"];

function kopf(request) {
  const herkunft = request.headers.get("Origin") || "";
  return {
    "Access-Control-Allow-Origin": ERLAUBTE_HERKUNFT.includes(herkunft) ? herkunft : "null",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Cache-Control": "no-store",
    "Content-Type": "application/json; charset=utf-8",
  };
}

function antwort(daten, request, status = 200) {
  return new Response(JSON.stringify(daten), { status, headers: kopf(request) });
}

function heute() {
  return new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Berlin" });
}

function leererStand() {
  return { ereignis: {}, mannschaft: {}, bereich: {} };
}

function addiere(ziel, quelle) {
  for (const gruppe of ["ereignis", "mannschaft", "bereich"]) {
    for (const [name, zahl] of Object.entries(quelle[gruppe] || {})) {
      ziel[gruppe][name] = (ziel[gruppe][name] || 0) + zahl;
    }
  }
  return ziel;
}

/** Nur bekannte Namen und ganze Zahlen uebernehmen - alles andere wird verworfen. */
function saeubere(roh) {
  const rein = leererStand();
  const uebernimm = (gruppe, erlaubt) => {
    for (const [name, wert] of Object.entries((roh || {})[gruppe] || {})) {
      if (!erlaubt.includes(name)) continue;
      const n = parseInt(wert, 10);
      if (Number.isFinite(n) && n > 0) rein[gruppe][name] = Math.min(n, 500);
    }
  };
  uebernimm("ereignis", STAT_EREIGNISSE);
  uebernimm("mannschaft", STAT_MANNSCHAFTEN);
  uebernimm("bereich", STAT_BEREICHE);
  return rein;
}

async function tagLesen(env, datum) {
  const teile = await Promise.all(
    Array.from({ length: STAT_TEILE }, (_, i) =>
      env.ZAEHLER.get(`stat:${datum}:${i}`).catch(() => null)));
  const gesamt = leererStand();
  for (const roh of teile) {
    if (!roh) continue;
    try { addiere(gesamt, JSON.parse(roh)); } catch { /* unbrauchbar */ }
  }
  return gesamt;
}

function angemeldet(env, benutzer, passwort) {
  const sollBenutzer = env.ADMIN_BENUTZER || "";
  const sollPasswort = env.ADMIN_PASSWORT || "";
  if (!sollPasswort) return false;
  const gleich = (a, b) => {
    if (a.length !== b.length) return false;
    let abweichung = 0;
    for (let i = 0; i < a.length; i++) abweichung |= a.charCodeAt(i) ^ b.charCodeAt(i);
    return abweichung === 0;
  };
  return gleich(String(benutzer || ""), sollBenutzer) && gleich(String(passwort || ""), sollPasswort);
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: kopf(request) });
    }

    const url = new URL(request.url);
    const pfad = url.pathname.replace(/\/+$/, "") || "/";

    try {
      if (pfad === "/zaehl" && request.method === "POST") {
        const rein = saeubere(await request.json());
        const datum = heute();
        // Zufaelliger Teil verteilt gleichzeitige Zugriffe - sonst geht bei
        // mehr als einem Schreibvorgang je Sekunde eine Zaehlung verloren.
        const teil = Math.floor(Math.random() * STAT_TEILE);
        const schluessel = `stat:${datum}:${teil}`;
        let stand = leererStand();
        try {
          const roh = await env.ZAEHLER.get(schluessel);
          if (roh) stand = addiere(leererStand(), JSON.parse(roh));
        } catch { /* neu anfangen */ }
        await env.ZAEHLER.put(schluessel, JSON.stringify(addiere(stand, rein)));
        return antwort({ gezaehlt: true }, request);
      }

      if (pfad === "/auswertung" && request.method === "POST") {
        const { benutzer, passwort, tage } = await request.json();
        if (!angemeldet(env, benutzer, passwort)) {
          return antwort({ fehler: "Anmeldung fehlgeschlagen" }, request, 401);
        }
        const anzahl = Math.min(Math.max(parseInt(tage, 10) || 30, 1), 90);
        const jetzt = new Date();
        const tageListe = Array.from({ length: anzahl }, (_, i) =>
          new Date(jetzt.getTime() - (anzahl - 1 - i) * 86400000)
            .toLocaleDateString("sv-SE", { timeZone: "Europe/Berlin" }));
        const staende = await Promise.all(tageListe.map((t) => tagLesen(env, t)));

        const verlauf = [];
        const gesamt = leererStand();
        tageListe.forEach((tag, i) => {
          verlauf.push({ tag, aufrufe: staende[i].ereignis.aufruf || 0 });
          addiere(gesamt, staende[i]);
        });
        return antwort({ verlauf, gesamt }, request);
      }

      return antwort({ fehler: "unbekannter Pfad" }, request, 404);
    } catch (fehler) {
      return antwort({ fehler: String((fehler && fehler.message) || fehler) }, request, 500);
    }
  },
};
