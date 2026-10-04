import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ArrowRight } from "../components/ui";

type Block = { title: string; lead: string; steps?: string[]; points?: string[]; note?: string };

const CONTENT: Record<"en" | "de", { title: string; lead: string; blocks: Block[]; sources: string }> = {
  de: {
    title: "So geht's",
    lead: "Städte sind glatt, trocken und hart. Moose, Flechten und viele kleine Tiere brauchen das Gegenteil: raue, feuchte, geschützte Flächen. BIOTILE schaut sich solche Oberflächen in der Natur ab und macht daraus Kacheln, die jede und jeder herstellen kann.",
    blocks: [
      {
        title: "Gemeinsam forschen",
        lead: "BIOTILE ist ein Mitmach-Projekt. Schulklassen, Nachbarschaften und Forschende hängen Kacheln auf und fotografieren sie regelmäßig. Jede Kachel ist ein kleiner Versuch, zusammen ergibt sich ein offener Datensatz.",
        points: [
          "Ziel ist herauszufinden, welche von der Natur abgeschauten Oberflächen am besten besiedelt werden.",
          "Jede Kachel bekommt eine Nummer. So lässt sich verfolgen, was wo wie schnell wächst.",
          "Kunststoff ist nur das Werkzeug. Nach draußen kommt nur gebrannter Ton oder Beton.",
        ],
      },
      {
        title: "Wer hier einzieht",
        lead: "Zuerst kommen Algen und Flechten, dann Moose. Mit ihnen siedeln sich sehr kleine Tiere an, die in Spalten und Moospolstern Schutz und Feuchtigkeit finden.",
        points: [
          "Feine Ritzen von 1 bis 3 mm: Springschwänze und Milben.",
          "Breitere Spalten von 5 bis 8 mm: kleine Spinnen, Asseln und Ohrwürmer.",
          "In Moospolstern: Bärtierchen, Rädertierchen und Fadenwürmer, winzig, aber zahlreich.",
          "Breite, flache Mulden halten Wasser. Mulden und Rillen sollten mit dem Wasser von oben nach unten laufen.",
        ],
        note: "Welche Tiere welche Spaltbreite bevorzugen, ist bisher nur grob bekannt. Genau das wollen wir mit den Kacheln herausfinden.",
      },
      {
        title: "Vom Foto zur Kachel",
        lead: "Aus deinem Foto erzeugt Tripo AI ein 3D-Modell. Dafür nutzt BIOTILE die Tripo-API: eine Schnittstelle, über die unser Server das Foto an Tripo schickt und das fertige Modell zurückbekommt. Du brauchst dafür kein eigenes Konto bei Tripo.",
        points: [
          "Vom 3D-Modell behalten wir nur die Oberseite und machen sie nahtlos, damit Kacheln ohne sichtbare Fuge aneinanderpassen.",
          "Dazu kommen Moosnester: kleine Taschen in den natürlichen Mulden, in die der Moos-Starter kommt. Feine Rinnsale leiten Regenwasser hinein.",
          "Vor dem Druck prüft BIOTILE, ob sich die Kachel aus der Form löst, ob sie stabil genug ist und ob die Teile auf einen üblichen 3D-Drucker passen.",
          "Ton schrumpft beim Brennen, deshalb wird die Form etwas größer gedruckt.",
        ],
      },
      {
        title: "Den Moos-Starter herstellen",
        lead: "Der Moos-Starter bringt Leben aus der Nachbarschaft auf die Kachel: Papierbrei hält Wasser, die Erde enthält Sporen von Moosen, Algen und Flechten, die an das örtliche Klima gewöhnt sind.",
        steps: [
          "Eierkartons oder unbedrucktes Papier in kleine Stücke reißen, über Nacht in Wasser einweichen und mit einem Pürierstab zu Brei mixen. Gut ausdrücken.",
          "Eine Stelle suchen, an der schon Moos wächst, etwa eine Mauerfuge, einen Pflasterrand oder eine schattige Ecke. Dort die oberste Erdschicht mit Moosresten abnehmen, ein bis zwei Zentimeter genügen, und grob durchsieben.",
          "Mindestens gleich viel Erde wie Papierbrei nehmen, gern mehr. Mischen und so viel Wasser zugeben, dass eine weiche, streichfähige Masse entsteht.",
          "Die Masse in die Moosnester drücken und kleine Moospolster hineinsetzen.",
          "In den ersten Wochen bei Trockenheit mit Wasser besprühen.",
        ],
        note: "Nur kleine Mengen sammeln, nur auf dem eigenen Gelände, in Pflasterfugen oder an Mauern, nie in Schutzgebieten. Torfmoose und Weißmoos sind geschützt.",
      },
      {
        title: "Der richtige Platz",
        lead: "Es kommt vor allem auf die Ausrichtung an. Eine Kachel, deren Vorderseite nach Norden zeigt, bekommt kaum direkte Sonne und bleibt länger feucht. Dort wächst es am schnellsten.",
        points: [
          "Leichter Schatten, etwa unter Bäumen oder an einer Mauer, hilft zusätzlich.",
          "Südseiten trocknen schnell aus und werden im Sommer heiß.",
          "Kacheln mit Abstand aufhängen (seitlich 2 cm, nach unten 5 cm), damit sich das Wasser der einen nicht auf die nächste ergießt.",
        ],
      },
      {
        title: "Ton: Sorte und Brennen",
        lead: "Für Schulen ist Ton am einfachsten: Die Kachel wird von Hand in die Form gedrückt und im Brennofen gebrannt, den viele Schulen in der Kunstabteilung haben.",
        points: [
          "Sorte: frostfester Ton mit Schamotte (feine Körnung), wie er für Gartenkeramik verwendet wird. Erhältlich im Keramik- und Töpfereibedarf.",
          "Schwindung: Jeder Ton schrumpft beim Trocknen und Brennen, meist um 8 bis 12 Prozent. Einmal an einem Probestab messen und den Wert in BIOTILE eintragen.",
          "Trocknen: langsam, ein bis zwei Wochen unter einem Tuch, damit nichts reißt.",
          "Brennen: so hoch, wie der Hersteller für Frostfestigkeit angibt, bei Gartenkeramik meist um 1000 bis 1150 °C. Nicht glasieren, sonst hält sich nichts auf der Oberfläche.",
        ],
      },
      {
        title: "Beton: Mischung und Vorgehen",
        lead: "Beton ist robuster, braucht aber mehr Vorsicht. Gut geeignet ist Hochofenzement (CEM III), der in Studien zu bewachsenen Betonwänden verwendet wurde. Es gibt ihn im Baustoffhandel.",
        points: [
          "Vorsatzschicht: Zement mit feinem Sand (0 bis 2 mm), damit die feine Struktur der Form abgebildet wird. Dahinter eine gröbere Mischung mit Kies (bis 8 mm).",
          "Mischung: etwa 1 Teil Zement auf 3 bis 4 Teile Sand und Kies, mit so wenig Wasser, dass der Beton gerade noch formbar ist.",
          "Trennmittel: Rapsöl. Kein Silikonspray, das macht die Oberfläche wasserabweisend.",
          "Oberflächenverzögerer (wie für Waschbeton, aus dem Baustoffhandel) auf die Form streichen. Nach dem Entformen die oberste Zementschicht abbürsten: Die raue, offene Oberfläche nimmt Wasser und Sporen besser auf.",
          "Einige Tage feucht und schattig aushärten lassen.",
        ],
        note: "Frischer Beton und Zementstaub reizen Haut und Augen stark: immer Handschuhe, Schutzbrille und beim Anmischen eine Staubmaske tragen.",
      },
      {
        title: "Daten & Privatsphäre",
        lead: "Konten gibt es nur für Schulen und Projekte, nicht für einzelne Schülerinnen und Schüler. Auf Fotos sind keine Personen zu sehen.",
        points: [
          "Die genaue Position einer Kachel ist freiwillig. Öffentlich wird sie auf etwa 100 m gerundet, bei Schulen nie genauer.",
          "Standortdaten in Fotos werden beim Hochladen automatisch entfernt.",
          "Alle Beobachtungen sind offene Daten (CC BY), alle Muster frei abwandelbar (CC BY-SA).",
        ],
      },
      {
        title: "Was wir herausfinden wollen",
        lead: "Welche Pflanzen und Tiere sind nach welcher Zeit auf den Kacheln zu finden? Und welche Oberflächen aus der Natur werden am besten besiedelt?",
        points: [
          "Hilft der Moos-Starter? Mit ihm zeigt sich das erste Grün meist nach einigen Monaten, ohne ihn kann es ein Jahr oder länger dauern.",
          "Wachsen Kopien echter Oberflächen besser als erfundene oder glatte?",
          "Wie viel macht die Himmelsrichtung aus?",
          "Darum gehören in jede Wand zwei Vergleichskacheln: eine glatte und eine Standard-Kachel.",
        ],
      },
    ],
    sources: "Grundlagen: Mustafa et al. 2021 (Sustainability 13:7453), Jakubovskis 2025 (Buildings 15:3646), Veeger et al. 2021, Larrieu et al. 2018 (Ecological Indicators 84), Moisan 2011, Schell et al. 2024.",
  },
  en: {
    title: "How it works",
    lead: "Cities are smooth, dry and hard. Mosses, lichens and many small animals need the opposite: rough, damp, sheltered surfaces. BIOTILE learns from such surfaces in nature and turns them into tiles that anyone can make.",
    blocks: [
      {
        title: "Research together",
        lead: "BIOTILE is a citizen science project. School classes, neighbourhoods and researchers hang tiles and photograph them regularly. Each tile is a small experiment; together they form an open dataset.",
        points: [
          "The goal is to find out which nature-inspired surfaces are colonised best.",
          "Every tile gets a number, so we can follow what grows where, and how fast.",
          "Plastic is only the tool. Only fired clay or concrete goes outside.",
        ],
      },
      {
        title: "Who moves in",
        lead: "Algae and lichens come first, then mosses. With them come very small animals that find shelter and moisture in cracks and moss cushions.",
        points: [
          "Fine cracks of 1 to 3 mm: springtails and mites.",
          "Wider gaps of 5 to 8 mm: small spiders, woodlice and earwigs.",
          "In moss cushions: tardigrades, rotifers and nematodes, tiny but numerous.",
          "Broad, shallow hollows hold water. Hollows and grooves should run with the water, from top to bottom.",
        ],
        note: "Which animals prefer which gap width is only roughly known so far. That is exactly what the tiles should help to find out.",
      },
      {
        title: "From photo to tile",
        lead: "Tripo AI turns your photo into a 3D model. BIOTILE uses the Tripo API for this: an interface through which our server sends the photo to Tripo and receives the finished model. You don't need your own Tripo account.",
        points: [
          "We keep only the top surface of the model and make it seamless, so tiles fit together without a visible joint.",
          "Then we add moss nests: small pockets in the natural hollows that take the moss starter. Fine rills lead rain water into them.",
          "Before printing, BIOTILE checks that the tile comes out of the mould, is strong enough and that the parts fit a common 3D printer.",
          "Clay shrinks when fired, so the mould is printed a little larger.",
        ],
      },
      {
        title: "Making the moss starter",
        lead: "The moss starter brings life from the neighbourhood onto the tile: paper pulp holds water, and the soil carries spores of mosses, algae and lichens that are used to the local climate.",
        steps: [
          "Tear egg cartons or unprinted paper into small pieces, soak them in water overnight and blend into a pulp. Squeeze out well.",
          "Find a spot where moss already grows, such as a wall joint, the edge of a pavement or a shady corner. Take the top layer of soil with bits of moss, one to two centimetres is enough, and sieve it roughly.",
          "Use at least as much soil as pulp, more is fine. Mix and add water until you get a soft, spreadable paste.",
          "Press the paste into the moss nests and set small moss cushions into it.",
          "Mist with water during dry spells in the first weeks.",
        ],
        note: "Collect only small amounts, only on your own grounds, from paving joints or walls, never in protected areas. Peat mosses and cushion moss are protected.",
      },
      {
        title: "The right spot",
        lead: "Orientation matters most. A tile whose front faces north gets hardly any direct sun and stays damp longer. That is where things grow fastest.",
        points: [
          "Light shade, under trees or next to a wall, helps as well.",
          "South-facing spots dry out quickly and get hot in summer.",
          "Hang tiles with gaps (2 cm sideways, 5 cm downwards) so water from one tile doesn't run onto the next.",
        ],
      },
      {
        title: "Clay: type and firing",
        lead: "For schools, clay is the easiest: the tile is pressed into the mould by hand and fired in a kiln, which many schools have in their art department.",
        points: [
          "Type: frost-resistant clay with grog (fine grain), as used for garden ceramics. Available from pottery suppliers.",
          "Shrinkage: every clay shrinks when drying and firing, usually by 8 to 12 percent. Measure it once on a test bar and enter the value in BIOTILE.",
          "Drying: slowly, one to two weeks under a cloth, so nothing cracks.",
          "Firing: as high as the supplier specifies for frost resistance, for garden ceramics usually around 1000 to 1150 °C. Don't glaze, or nothing will hold on to the surface.",
        ],
      },
      {
        title: "Concrete: mix and method",
        lead: "Concrete is tougher but needs more care. Blast-furnace cement (CEM III) works well; it was used in studies on green concrete walls. It is sold by builders' merchants.",
        points: [
          "Facing layer: cement with fine sand (0 to 2 mm), so the fine structure of the mould comes through. Behind it, a coarser mix with gravel (up to 8 mm).",
          "Mix: roughly 1 part cement to 3 to 4 parts sand and gravel, with just enough water that the concrete is still mouldable.",
          "Release agent: rapeseed oil. No silicone spray, it makes the surface water-repellent.",
          "Brush a surface retarder (as used for exposed-aggregate concrete) onto the mould. After demoulding, brush off the top cement layer: the rough, open surface takes up water and spores much better.",
          "Let it cure for a few days, damp and in the shade.",
        ],
        note: "Fresh concrete and cement dust strongly irritate skin and eyes: always wear gloves and goggles, and a dust mask when mixing.",
      },
      {
        title: "Data & privacy",
        lead: "Accounts are only for schools and projects, not for individual students. No people appear on photos.",
        points: [
          "The exact position of a tile is optional. Publicly it is rounded to about 100 m, for schools never more precise.",
          "Location data in photos is removed automatically when uploading.",
          "All observations are open data (CC BY), all patterns are free to remix (CC BY-SA).",
        ],
      },
      {
        title: "What we want to find out",
        lead: "Which plants and animals can be found on the tiles, and after how long? And which surfaces from nature are colonised best?",
        points: [
          "Does the moss starter help? With it, the first green usually shows after a few months; without it, it can take a year or longer.",
          "Do copies of real surfaces do better than invented or smooth ones?",
          "How much does the orientation matter?",
          "That is why every wall has two control tiles: a smooth one and a standard one.",
        ],
      },
    ],
    sources: "Based on Mustafa et al. 2021 (Sustainability 13:7453), Jakubovskis 2025 (Buildings 15:3646), Veeger et al. 2021, Larrieu et al. 2018 (Ecological Indicators 84), Moisan 2011, Schell et al. 2024.",
  },
};

export default function Method() {
  const { i18n, t } = useTranslation();
  const c = CONTENT[i18n.resolvedLanguage === "de" ? "de" : "en"];
  return (
    <article className="wrap">
      <header className="grid gap-6 py-col md:grid-cols-12">
        <h1 className="title-xl md:col-span-12">{c.title}</h1>
        <p className="lead max-w-[48ch] md:col-span-8">{c.lead}</p>
      </header>
      {c.blocks.map((b, i) => (
        <section key={b.title} className="grid gap-6 border-t border-line py-12 md:grid-cols-12">
          <div className="md:col-span-4">
            <div className="font-mono text-xs opacity-40">{String(i + 1).padStart(2, "0")}</div>
            <h2 className="title-md mt-3">{b.title}</h2>
          </div>
          <div className="md:col-span-7 md:col-start-6">
            <p className="text-[22px] leading-snug tracking-tight">{b.lead}</p>
            {b.steps && (
              <ol className="mt-6 space-y-3">
                {b.steps.map((p, k) => (
                  <li key={p} className="grid grid-cols-[1.5rem_1fr] text-sm leading-relaxed">
                    <span className="font-mono text-xs opacity-40">{k + 1}</span><span className="opacity-80">{p}</span>
                  </li>
                ))}
              </ol>
            )}
            {b.points && (
              <ul className="mt-6 space-y-3">
                {b.points.map((p) => (
                  <li key={p} className="grid grid-cols-[1.5rem_1fr] text-sm leading-relaxed opacity-70">
                    <span aria-hidden>—</span><span>{p}</span>
                  </li>
                ))}
              </ul>
            )}
            {b.note && <p className="mt-6 border-l-2 border-line pl-4 text-sm opacity-60">{b.note}</p>}
          </div>
        </section>
      ))}
      <section className="grid gap-6 border-t border-line py-12 md:grid-cols-12">
        <p className="text-xs opacity-50 md:col-span-6">{c.sources}</p>
        <div className="md:col-span-5 md:col-start-8">
          <Link to="/create" className="row-link">
            <span className="text-[22px] font-medium tracking-tight">{t("nav.make")}</span>
            <ArrowRight />
          </Link>
        </div>
      </section>
    </article>
  );
}
