/** Fixed, page-wide ambient backdrop: fine gold grid, slow orbs, vignette. */
export default function PageBackground() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-ink-950"
    >
      {/* Fine grid, masked to fade out toward the edges. */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(201,169,97,0.05) 1px, transparent 1px)," +
            "linear-gradient(to bottom, rgba(201,169,97,0.05) 1px, transparent 1px)",
          backgroundSize: "58px 58px",
          maskImage:
            "radial-gradient(ellipse 75% 60% at 50% 35%, #000 40%, transparent 92%)",
          WebkitMaskImage:
            "radial-gradient(ellipse 75% 60% at 50% 35%, #000 40%, transparent 92%)",
        }}
      />
      {/* Slow-drifting ambient orbs for depth. */}
      <div className="absolute left-[8%] top-[14%] h-72 w-72 animate-float rounded-full bg-gold-500/[0.07] blur-3xl" />
      <div
        className="absolute right-[6%] top-[42%] h-96 w-96 animate-float rounded-full bg-ink-500/20 blur-3xl"
        style={{ animationDuration: "13s" }}
      />
      <div
        className="absolute bottom-[10%] left-[32%] h-80 w-80 animate-float rounded-full bg-gold-600/[0.06] blur-3xl"
        style={{ animationDuration: "16s", animationDelay: "-5s" }}
      />
      {/* Edge vignette to keep focus toward the center. */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(130% 90% at 50% 0%, transparent 50%, rgba(6,8,13,0.55) 100%)",
        }}
      />
    </div>
  );
}
