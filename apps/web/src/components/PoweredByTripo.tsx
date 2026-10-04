/** "Powered by Tripo AI" with the cut-out logo (light and dark variant). */
export default function PoweredByTripo({ className = "", height = 18 }: { className?: string; height?: number }) {
  return (
    <a href="https://www.tripo3d.ai" target="_blank" rel="noreferrer"
      className={`flex w-fit items-center gap-2.5 opacity-70 transition-opacity hover:opacity-100 ${className}`}
      aria-label="Powered by Tripo AI">
      <span className="font-mono text-[10px] uppercase tracking-widest">Powered by</span>
      <img src="/brand/tripo-logo.png" alt="Tripo AI" style={{ height }} className="w-auto dark:hidden" />
      <img src="/brand/tripo-logo-dark.png" alt="Tripo AI" style={{ height }} className="hidden w-auto dark:block" />
    </a>
  );
}
