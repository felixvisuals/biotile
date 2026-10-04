import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api, type DesignSummary, type Preview } from "../api";
import ReliefViewer from "./ReliefViewer";
import { ArrowRight, PinIcon } from "./ui";
import { useLocalized } from "../localized";

/** Collection card: an interactive 3D relief (drag to turn, Ctrl/⌘ + scroll or pinch to zoom),
 *  loaded only while the card is on screen; the rendered image stands in before that. */
export default function TileCard({ design: d, interactive = true }: { design: DesignSummary; interactive?: boolean }) {
  const { t } = useTranslation();
  const L = useLocalized();
  const href = d.stage === "exported" || d.status === "published" ? `/designs/${d.id}` : `/designs/${d.id}/edit`;
  const box = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [preview, setPreview] = useState<Preview | null>(null);

  useEffect(() => {
    if (!interactive || !box.current) return;
    const io = new IntersectionObserver(([e]) => setVisible(e.isIntersecting), { rootMargin: "200px" });
    io.observe(box.current);
    return () => io.disconnect();
  }, [interactive]);
  useEffect(() => {
    if (visible && !preview && (d.stage === "exported" || d.status === "published")) {
      api.preview(d.id, 96).then(setPreview).catch(() => {});
    }
  }, [visible, preview, d.id, d.stage, d.status]);

  return (
    <div className="group bg-surface">
      <div ref={box} className="relative aspect-[1/1.12]">
        {visible && preview ? (
          <ReliefViewer preview={preview} view="one" compact className="absolute inset-0" />
        ) : (
          <Link to={href} className="absolute inset-0 block p-[12%] pb-[6%]">
            {d.preview_url ? (
              <img src={d.preview_url} alt={L.title(d)} loading="lazy" className="aspect-square w-full object-contain" />
            ) : (
              <div className="flex aspect-square w-full items-center justify-center border border-dashed border-fg/20 font-mono text-xs uppercase opacity-50">
                {t("editor.title")}
              </div>
            )}
          </Link>
        )}
      </div>
      <Link to={href} className="flex items-center gap-3 px-[7%] pb-5 transition-opacity hover:opacity-70">
        <span className="min-w-0 flex-1 truncate text-sm font-medium">{L.title(d)}</span>
        {d.status !== "published" && <span className="font-mono text-[10px] uppercase opacity-40">draft</span>}
        <span className="flex items-center gap-1 text-xs opacity-50" title={t("home.tiles_count", { count: d.instance_count })}>
          <PinIcon size={15} /> {d.instance_count}
        </span>
        <ArrowRight size={16} className="opacity-50" />
      </Link>
    </div>
  );
}
