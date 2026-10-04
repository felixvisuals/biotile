import { useTranslation } from "react-i18next";
import type { Observation } from "../api";

/** Details of one observation photo: date, observer, what was seen, notes. */
export default function ObservationDetails({ o }: { o: Observation }) {
  const { t } = useTranslation();
  return (
    <>
      <div className="font-mono text-xs">{o.observed_at} · {t(`observe.who_opts.${o.observer_role}`)}</div>
      {o.species.length > 0 && (
        <ul className="space-y-0.5">
          {o.species.map((s, i) => (
            <li key={i} className="font-medium">
              {s.name}{s.group ? ` (${t(`observe.groups.${s.group}`)})` : ""} <span className="opacity-60">· {t(`observe.sure.${s.certainty}`)}</span>
            </li>
          ))}
        </ul>
      )}
      {o.weight_g !== null && <div className="text-xs">{o.weight_g} g</div>}
      {o.notes && <p className="text-xs leading-relaxed">{o.notes}</p>}
    </>
  );
}
