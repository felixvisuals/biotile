import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import HexRelief from "../components/HexRelief";
import { ArrowRight } from "../components/ui";

/** The Senyera, kept small and quiet: nine stripes, four of them red. */
export function Senyera({ className = "h-3 w-[18px]" }: { className?: string }) {
  return (
    <svg viewBox="0 0 9 6" className={className} aria-label="Senyera" role="img" preserveAspectRatio="none">
      <rect width="9" height="6" fill="#FCDD09" />
      {[1, 3, 5, 7].map((i) => <rect key={i} y={(i * 6) / 9} width="9" height={6 / 9} fill="#DA121A" />)}
    </svg>
  );
}

const TEXT = {
  en: {
    eyebrow: "Barcelona · 1904",
    title: "The Gaudí tile",
    lead: "In 1904 Antoni Gaudí designed a hexagonal floor tile together with the Escofet company. Its relief shows three sea creatures: a brittle star, an ammonite and a sargassum seaweed. No single tile shows them complete: the figures only come together when the tiles lie side by side.",
    points: [
      ["Learning from nature", "Gaudí called nature his teacher. The hexagon recalls a honeycomb, the relief a seabed."],
      ["From the house to the street", "The tile was meant for Casa Batlló and was finally laid in Casa Milà, La Pedrera. Since 1997 a version for outdoor use paves the sidewalks of Passeig de Gràcia, with the relief reversed so it wears less."],
      ["Why it is here", "BIOTILE follows the same idea: bringing shapes from nature onto the surfaces of the city. We present in Barcelona, so this is our small greeting."],
    ],
    math: "Our homage is calculated, not copied: the figures sit on the points of a hexagonal grid, so every tile is the same and the joints disappear by themselves.",
    one: "One tile",
    many: "Seven tiles",
    back: "Back to the collection",
  },
  de: {
    eyebrow: "Barcelona · 1904",
    title: "Die Gaudí-Fliese",
    lead: "1904 entwarf Antoni Gaudí zusammen mit der Firma Escofet eine sechseckige Bodenfliese. Ihr Relief zeigt drei Bewohner des Meeres: einen Schlangenstern, einen Ammoniten und eine Sargassum-Alge. Keine Fliese zeigt sie vollständig: Erst wenn die Fliesen nebeneinanderliegen, fügen sich die Figuren zusammen.",
    points: [
      ["Von der Natur gelernt", "Gaudí nannte die Natur seine Lehrmeisterin. Das Sechseck erinnert an Bienenwaben, das Relief an einen Meeresgrund."],
      ["Vom Wohnhaus auf die Straße", "Gedacht war die Fliese für die Casa Batlló, verlegt wurde sie schließlich in der Casa Milà, La Pedrera. Seit 1997 liegt eine Ausführung für draußen auf den Gehwegen des Passeig de Gràcia. Ihr Relief ist dort umgekehrt, damit es sich weniger abläuft."],
      ["Warum sie hier ist", "BIOTILE folgt derselben Idee: Formen aus der Natur auf die Oberflächen der Stadt zu bringen. Wir stellen das Projekt in Barcelona vor, deshalb dieser kleine Gruß."],
    ],
    math: "Unsere Hommage ist berechnet, nicht kopiert: Die Figuren sitzen auf den Punkten eines Sechseck-Gitters. Deshalb ist jede Fliese gleich, und die Fugen verschwinden von selbst.",
    one: "Eine Fliese",
    many: "Sieben Fliesen",
    back: "Zurück zur Sammlung",
  },
};

export default function Gaudi() {
  const { i18n } = useTranslation();
  const c = TEXT[i18n.resolvedLanguage === "de" ? "de" : "en"];
  const [cluster, setCluster] = useState(false);
  return (
    <div className="wrap">
      <div className="flex flex-wrap items-center gap-x-8 gap-y-3 py-10 md:py-14">
        <h1 className="title-md flex items-center gap-3">{c.title} <Senyera /></h1>
        <div className="ml-auto flex gap-2">
          <button className="pill" aria-pressed={!cluster} onClick={() => setCluster(false)}>{c.one}</button>
          <button className="pill" aria-pressed={cluster} onClick={() => setCluster(true)}>{c.many}</button>
        </div>
      </div>
      <div className="grid gap-x-[calc(var(--col)/1.5)] gap-y-10 md:grid-cols-12">
        <div className="border-t border-line pt-6 md:col-span-6">
          <HexRelief cluster={cluster} sway />
          <p className="mt-2 font-mono text-[10px] uppercase tracking-widest opacity-40">{c.math}</p>
        </div>
        <div className="border-t border-line pt-6 md:col-span-6">
          <div className="eyebrow">{c.eyebrow}</div>
          <p className="mt-4 text-[22px] leading-snug tracking-tight">{c.lead}</p>
          <dl className="mt-10 divide-y divide-line border-y border-line">
            {c.points.map(([k, v]) => (
              <div key={k} className="grid gap-2 py-4 md:grid-cols-[12rem_1fr]">
                <dt className="text-sm font-medium">{k}</dt>
                <dd className="text-sm opacity-70">{v}</dd>
              </div>
            ))}
          </dl>
          <Link to="/" className="row-link group mt-10">
            <span className="text-[20px] font-medium tracking-tight">{c.back}</span>
            <ArrowRight />
          </Link>
        </div>
      </div>
    </div>
  );
}
