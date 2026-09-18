import worker from "./index.js";

// KV nachbilden - Muster aus dem MuRu-Worker uebernommen (worker/test.mjs).
const speicher = new Map();
const env = {
  ZAEHLER: {
    get: async (k) => (speicher.has(k) ? speicher.get(k) : null),
    put: async (k, v) => void speicher.set(k, v),
  },
  ADMIN_BENUTZER: "edis",
  ADMIN_PASSWORT: "geheim",
};

const H = { Origin: "https://beatzep.github.io", "Content-Type": "application/json" };
const ruf = async (pfad, methode = "GET", koerper) => {
  const r = await worker.fetch(new Request("https://x.dev" + pfad, {
    method: methode, headers: H,
    body: koerper ? JSON.stringify(koerper) : undefined,
  }), env);
  return { status: r.status, cors: r.headers.get("Access-Control-Allow-Origin"), daten: await r.json() };
};

const pruefungen = [];
const pruefe = (name, ok, info = "") => pruefungen.push({ name, ok, info });

let r = await ruf("/zaehl", "POST", { ereignis: { aufruf: 1 }, mannschaft: { herren1: 1 }, bereich: { spiele: 1 } });
pruefe("Zaehlung angenommen", r.status === 200 && r.daten.gezaehlt === true, JSON.stringify(r));

r = await ruf("/zaehl", "POST", { ereignis: { aufruf: 1 }, mannschaft: { herren2: 1 }, bereich: { kalender: 1 } });
pruefe("Zweite Zaehlung angenommen", r.daten.gezaehlt === true);

r = await ruf("/zaehl", "POST", { ereignis: { unbekannt: 5 }, mannschaft: { boese: 99 } });
pruefe("Unbekannte Namen werden verworfen, kein Fehler", r.status === 200);

r = await ruf("/auswertung", "POST", { benutzer: "wer", passwort: "falsch", tage: 7 });
pruefe("Falsches Passwort abgewiesen", r.status === 401);

r = await ruf("/auswertung", "POST", { benutzer: "edis", passwort: "geheim", tage: 7 });
pruefe("Auswertung mit richtigem Passwort", r.status === 200, JSON.stringify(r.daten));
const heuteVerlauf = r.daten.verlauf[r.daten.verlauf.length - 1];
pruefe("Heutiger Tag zaehlt beide Aufrufe", heuteVerlauf.aufrufe === 2, JSON.stringify(heuteVerlauf));
pruefe("Mannschaften summiert", r.daten.gesamt.mannschaft.herren1 === 1 && r.daten.gesamt.mannschaft.herren2 === 1,
  JSON.stringify(r.daten.gesamt));
pruefe("Verworfene Mannschaft taucht nicht auf", r.daten.gesamt.mannschaft.boese === undefined);

const fremd = await worker.fetch(new Request("https://x.dev/auswertung",
  { method: "POST", headers: { Origin: "https://boese.example", "Content-Type": "application/json" },
    body: JSON.stringify({ benutzer: "edis", passwort: "geheim", tage: 7 }) }), env);
pruefe("Fremde Herkunft ohne CORS-Freigabe",
  fremd.headers.get("Access-Control-Allow-Origin") === "null");

r = await ruf("/unbekannt");
pruefe("Unbekannter Pfad 404", r.status === 404);

let fehler = 0;
for (const p of pruefungen) {
  if (!p.ok) fehler++;
  console.log(`${p.ok ? "  ok  " : "FEHLER"}  ${p.name}${p.ok ? "" : "   " + p.info}`);
}
console.log(fehler ? `\n${fehler} Prüfung(en) fehlgeschlagen` : `\nAlle ${pruefungen.length} Prüfungen bestanden`);
process.exit(fehler ? 1 : 0);
