import { useTranslation } from "react-i18next";
import mossPhotos from "../data/moss-credits.json";
import photos from "../data/surface-credits.json";
import templatePhotos from "../data/template-credits.json";

type Photo = { label: string; title: string; source: string; author: string; license: string };

/** Attributions. Not in the main navigation: reachable via the small "Credits" link in the footer. */
const ROWS: { part: { en: string; de: string }; who: string; href: string; note: string }[] = [
  { part: { en: "Surface gallery (parallax motion)", de: "Oberflächen-Galerie (Parallax-Bewegung)" }, who: "Skiper UI · Skiper30 by Gurvinder Singh, inspired by siena.film", href: "https://skiper-ui.com", note: "Free version, attribution required" },
  { part: { en: "Menu animation (text roll)", de: "Menü-Animation (Text-Roll)" }, who: "Skiper UI · Skiper58", href: "https://skiper-ui.com", note: "Free version, attribution required" },
  { part: { en: "Map", de: "Karte" }, who: "MapLibre GL · OpenFreeMap · © OpenStreetMap contributors", href: "https://openfreemap.org", note: "BSD-3 · ODbL" },
  { part: { en: "Place suggestions", de: "Ortsvorschläge" }, who: "Photon by komoot · © OpenStreetMap contributors", href: "https://photon.komoot.io", note: "ODbL" },
  { part: { en: "Hero video", de: "Video auf der Startseite" }, who: "Generated with Google Gemini (Veo) for BIOTILE", href: "https://gemini.google.com", note: "AI-generated" },
  { part: { en: "Text input with soft caret", de: "Texteingabe mit weichem Cursor" }, who: "Skiper UI · Skiper106", href: "https://skiper-ui.com", note: "Free version, attribution required" },
  { part: { en: "Loading orbs", de: "Lade-Orbs" }, who: "Thinking Orbs by Yogesh (yogesharc)", href: "https://thinkingorbs.com", note: "MIT" },
  { part: { en: "Layout and look", de: "Layout und Gestaltung" }, who: "Inspired by Book of Shapes (Nikolaj Sokolowski) and theodore.net (Teddy Warner)", href: "https://bookofshapes.com", note: "Inspiration" },
  { part: { en: "Typeface", de: "Schrift" }, who: "Geist and Geist Mono by Vercel", href: "https://vercel.com/font", note: "SIL OFL 1.1" },
  { part: { en: "3D models from photos", de: "3D-Modelle aus Fotos" }, who: "Tripo3D (VAST)", href: "https://www.tripo3d.ai", note: "API" },
  { part: { en: "3D view, motion, smooth scroll", de: "3D-Ansicht, Bewegung, weiches Scrollen" }, who: "three.js · Framer Motion · Lenis (darkroom.engineering)", href: "https://threejs.org", note: "MIT" },
  { part: { en: "Surface measurements", de: "Oberflächen-Messwerte" }, who: "surfalize (Schell, Zwahr, Lasagni 2024)", href: "https://github.com/fredericjs/surfalize", note: "GPL-3.0 (server side)" },
  { part: { en: "Hexagonal easter egg", de: "Sechseck-Easteregg" }, who: "After the Gaudí paving tile (Antoni Gaudí, 1904; reissued by Escofet, 1997)", href: "https://www.escofet.com", note: "Homage, own geometry" },
  { part: { en: "Science", de: "Wissenschaft" }, who: "Mustafa et al. 2021 · Jakubovskis 2025 · Larrieu et al. 2018", href: "/method", note: "See How it works" },
];

export default function Credits() {
  const { i18n } = useTranslation();
  const lang = i18n.resolvedLanguage === "de" ? "de" : "en";
  return (
    <div className="wrap">
      <div className="py-col">
        <h1 className="title-lg">Credits</h1>
      </div>
      <dl className="divide-y divide-line border-y border-line">
        {ROWS.map((r) => (
          <div key={r.part.en} className="grid gap-1 py-4 text-sm md:grid-cols-12 md:gap-6">
            <dt className="font-medium md:col-span-4">{r.part[lang]}</dt>
            <dd className="md:col-span-6"><a href={r.href} target={r.href.startsWith("/") ? undefined : "_blank"} rel="noreferrer" className="underline-offset-4 hover:underline">{r.who}</a></dd>
            <dd className="font-mono text-xs opacity-40 md:col-span-2 md:text-right">{r.note}</dd>
          </div>
        ))}
      </dl>
      {([
        [lang === "de" ? "Fotos: Oberflächen" : "Photos: surfaces", photos as (Photo & { file: string })[]],
        [lang === "de" ? "Fotos: Vorlagenkatalog" : "Photos: template catalogue",
          Object.entries(templatePhotos as Record<string, Photo>).map(([id, p]) => ({ ...p, label: id.replace(/_/g, " ") }))],
        [lang === "de" ? "Fotos: Moos-Starter" : "Photos: moss starter",
          Object.entries(mossPhotos as Record<string, Photo>).map(([id, p]) => ({ ...p, label: id.replace(/_/g, " ") }))],
      ] as [string, Photo[]][]).map(([heading, list]) => (
        <section key={heading}>
          <h2 className="title-md mt-col mb-4">{heading}</h2>
          <p className="mb-4 text-sm opacity-60">{lang === "de"
            ? "Alle Fotos stammen von Wikimedia Commons und sind gemeinfrei oder CC0."
            : "All photos come from Wikimedia Commons and are public domain or CC0."}</p>
          <dl className="divide-y divide-line border-y border-line">
            {list.map((p) => (
              <div key={p.title} className="grid gap-1 py-3 text-sm md:grid-cols-12 md:gap-6">
                <dt className="font-medium capitalize md:col-span-4">{p.label}</dt>
                <dd className="md:col-span-6"><a href={p.source} target="_blank" rel="noreferrer" className="underline-offset-4 hover:underline">{p.title}</a> · {p.author}</dd>
                <dd className="font-mono text-xs opacity-40 md:col-span-2 md:text-right">{p.license}</dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
    </div>
  );
}
