import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ArrowRight } from "../components/ui";

/**
 * Moss starter guide. The research summary follows Jakubovskis 2025 (Buildings 15:3646, field
 * tests of "Layered Living Concrete" panels with a biological booster); the recipe is the same
 * as on the Method page, step photos are public domain / CC0 (see Credits).
 */
const PAPER = "https://www.mdpi.com/2075-5309/15/20/3646";

type Step = { img: string; t: string; d: string };
type Content = {
  eyebrow: string; title: string; lead: string;
  studyTitle: string; study: string[]; source: string;
  needTitle: string; need: string[];
  stepsTitle: string; steps: Step[];
  expectTitle: string; expect: [string, string][];
  note: string; ctaMake: string; ctaHang: string;
};

const CONTENT: Record<"en" | "de", Content> = {
  en: {
    eyebrow: "Guide",
    title: "Moss starter",
    lead: "A paste of paper pulp and local soil. Pressed into the moss nests of a tile, it brings green within months instead of years.",
    studyTitle: "What the research shows",
    study: [
      "Bare concrete stays bare for a long time. In field tests, a rough, porous concrete surface showed no growth after two years; on its own it can take years to decades.",
      "With a starter of recycled paper pulp and local soil, the first mosses and fungi appeared after about three months. After a year and a half the moss was well established.",
      "At least half of the starter should be soil. It carries bacteria and spores of mosses, fungi and lichens from the area, which are already used to the local climate.",
      "Water decides. Where the starter dried out, nothing grew. Continuous diagonal channels held the water best.",
      "Mosses grow mostly in autumn and pause in winter. In the long run they won out over planted grasses and sedums.",
      "Shady, damp, north-facing walls are colonised fastest; smooth, sunny walls can stay bare for decades.",
    ],
    source: "Jakubovskis, R. (2025). Biophilic Façades: The Potentiality of Bioreceptive Concrete. Buildings 15(20), 3646. Field tests in Vilnius since 2021.",
    needTitle: "You need",
    need: ["Egg cartons or unprinted paper", "Water and a bucket", "A hand blender", "A sieve", "A spoon or spatula", "A spray bottle"],
    stepsTitle: "Step by step",
    steps: [
      { img: "paper", t: "Make paper pulp", d: "Tear egg cartons or unprinted paper into small pieces, soak them in water overnight and blend into a pulp. Squeeze out well." },
      { img: "collect", t: "Collect local soil", d: "Look for a spot where moss already grows: a wall joint, the edge of a pavement, a shady corner. Take the top one to two centimetres with bits of moss and sieve roughly." },
      { img: "mix", t: "Mix", d: "Use at least as much soil as pulp, more is better. Add water until you get a soft paste that spreads like thick yoghurt." },
      { img: "press", t: "Fill the moss nests", d: "Press the paste firmly into the moss nests or channels of the tile and set small moss cushions into it." },
      { img: "water", t: "Keep it moist", d: "Mist with water during dry spells, above all in the first months. A shady or north-facing spot helps a lot." },
    ],
    expectTitle: "What to expect",
    expect: [["about 3 months", "first green: tiny moss shoots and fungi"], ["6 to 18 months", "the moss spreads from the nests"], ["winter", "growth pauses, it picks up again in spring and autumn"]],
    note: "Collect only small amounts, only on your own grounds, from paving joints or walls, never in protected areas. Peat mosses and cushion moss are protected.",
    ctaMake: "Make a pattern",
    ctaHang: "Hang a tile",
  },
  de: {
    eyebrow: "Anleitung",
    title: "Moos-Starter",
    lead: "Ein Brei aus Papier und Erde aus der Nachbarschaft. In die Moosnester einer Kachel gedrückt, bringt er das erste Grün nach Monaten statt nach Jahren.",
    studyTitle: "Was die Forschung zeigt",
    study: [
      "Nackter Beton bleibt lange nackt. In Freilandversuchen war auf einer rauen, porösen Betonfläche nach zwei Jahren noch nichts gewachsen. Von allein kann es Jahre bis Jahrzehnte dauern.",
      "Mit einem Starter aus Altpapierbrei und Erde aus der Umgebung zeigten sich die ersten Moose und Pilze nach etwa drei Monaten. Nach anderthalb Jahren war das Moos gut angewachsen.",
      "Mindestens die Hälfte des Starters sollte Erde sein. Sie bringt Bakterien und Sporen von Moosen, Pilzen und Flechten aus der Gegend mit, die das örtliche Klima schon kennen.",
      "Wasser entscheidet. Wo der Starter austrocknete, wuchs nichts. Durchgehende schräge Rinnen hielten das Wasser am besten.",
      "Moose wachsen vor allem im Herbst und machen im Winter Pause. Auf Dauer setzten sie sich gegen gepflanzte Gräser und Fetthennen durch.",
      "Schattige, feuchte, nach Norden zeigende Wände werden am schnellsten besiedelt. Glatte, sonnige Wände können jahrzehntelang kahl bleiben.",
    ],
    source: "Jakubovskis, R. (2025). Biophilic Façades: The Potentiality of Bioreceptive Concrete. Buildings 15(20), 3646. Freilandversuche in Vilnius seit 2021.",
    needTitle: "Das brauchst du",
    need: ["Eierkartons oder unbedrucktes Papier", "Wasser und einen Eimer", "Einen Pürierstab", "Ein Sieb", "Einen Löffel oder Spachtel", "Eine Sprühflasche"],
    stepsTitle: "Schritt für Schritt",
    steps: [
      { img: "paper", t: "Papierbrei machen", d: "Eierkartons oder unbedrucktes Papier in kleine Stücke reißen, über Nacht in Wasser einweichen und mit dem Pürierstab zu Brei mixen. Gut ausdrücken." },
      { img: "collect", t: "Erde aus der Nachbarschaft holen", d: "Eine Stelle suchen, an der schon Moos wächst: eine Mauerfuge, ein Pflasterrand, eine schattige Ecke. Die obersten ein bis zwei Zentimeter mit Moosresten abnehmen und grob sieben." },
      { img: "mix", t: "Mischen", d: "Mindestens gleich viel Erde wie Papierbrei nehmen, mehr ist besser. So viel Wasser zugeben, dass ein weicher Brei entsteht, etwa wie dicker Joghurt." },
      { img: "press", t: "Moosnester füllen", d: "Den Brei fest in die Moosnester oder Rinnen der Kachel drücken und kleine Moospolster hineinsetzen." },
      { img: "water", t: "Feucht halten", d: "Bei Trockenheit mit Wasser besprühen, vor allem in den ersten Monaten. Ein schattiger oder nach Norden zeigender Platz hilft sehr." },
    ],
    expectTitle: "Was dich erwartet",
    expect: [["nach etwa 3 Monaten", "das erste Grün: winzige Moostriebe und Pilze"], ["nach 6 bis 18 Monaten", "das Moos breitet sich aus den Nestern aus"], ["im Winter", "Pause, im Frühling und Herbst geht es weiter"]],
    note: "Nur kleine Mengen sammeln, nur auf dem eigenen Gelände, in Pflasterfugen oder an Mauern, nie in Schutzgebieten. Torfmoose und Weißmoos sind geschützt.",
    ctaMake: "Muster gestalten",
    ctaHang: "Kachel aufhängen",
  },
};

export default function MossStarter() {
  const { i18n } = useTranslation();
  const c = CONTENT[i18n.resolvedLanguage === "de" ? "de" : "en"];
  return (
    <article className="wrap">
      <header className="grid gap-6 py-col md:grid-cols-12">
        <div className="eyebrow md:col-span-12">{c.eyebrow}</div>
        <h1 className="title-xl md:col-span-12">{c.title}</h1>
        <p className="lead max-w-[48ch] md:col-span-8">{c.lead}</p>
      </header>

      <section className="grid gap-6 border-t border-line py-12 md:grid-cols-12">
        <h2 className="title-md md:col-span-4">{c.studyTitle}</h2>
        <div className="md:col-span-7 md:col-start-6">
          <ul className="space-y-4">
            {c.study.map((p) => (
              <li key={p} className="grid grid-cols-[1.5rem_1fr] text-[17px] leading-snug">
                <span aria-hidden className="opacity-40">—</span><span>{p}</span>
              </li>
            ))}
          </ul>
          <p className="mt-6 font-mono text-[11px] leading-relaxed opacity-50">
            <a href={PAPER} target="_blank" rel="noreferrer" className="underline-offset-4 hover:underline">{c.source}</a>
          </p>
        </div>
      </section>

      <section className="grid gap-6 border-t border-line py-12 md:grid-cols-12">
        <h2 className="title-md md:col-span-4">{c.needTitle}</h2>
        <ul className="flex flex-wrap gap-2 md:col-span-7 md:col-start-6">
          {c.need.map((n) => <li key={n} className="rounded-full border border-line px-4 py-2 text-sm">{n}</li>)}
        </ul>
      </section>

      <section className="border-t border-line py-12">
        <h2 className="title-md mb-10">{c.stepsTitle}</h2>
        <ol className="grid gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-5">
          {c.steps.map((s, i) => (
            <li key={s.t}>
              <img src={`/images/moss/${s.img}.jpg`} alt="" loading="lazy" className="aspect-square w-full rounded-[18px] object-cover" />
              <div className="mt-4 font-mono text-xs opacity-40">{String(i + 1).padStart(2, "0")}</div>
              <h3 className="mt-1 !text-[19px] !leading-tight font-semibold tracking-tight hyphens-auto">{s.t}</h3>
              <p className="mt-2 text-sm leading-relaxed opacity-75">{s.d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="grid gap-6 border-t border-line py-12 md:grid-cols-12">
        <h2 className="title-md md:col-span-4">{c.expectTitle}</h2>
        <dl className="divide-y divide-line border-y border-line md:col-span-7 md:col-start-6">
          {c.expect.map(([when, what]) => (
            <div key={when} className="grid grid-cols-[10rem_1fr] gap-4 py-4 text-sm">
              <dt className="font-mono text-xs uppercase tracking-widest opacity-60">{when}</dt>
              <dd>{what}</dd>
            </div>
          ))}
        </dl>
        <p className="text-sm opacity-60 md:col-span-7 md:col-start-6">{c.note}</p>
      </section>

      <div className="flex flex-wrap gap-3 border-t border-line py-12">
        <Link to="/create" className="btn">{c.ctaMake} <ArrowRight size={18} /></Link>
        <Link to="/register" className="btn-ghost">{c.ctaHang} <ArrowRight size={18} /></Link>
      </div>
    </article>
  );
}
