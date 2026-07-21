import { useEffect, useState } from "react";

/**
 * Dashboard navigation rail: the four module sections as a numbered stepper
 * (scroll-spy highlights the section in view; a dot marks the ones that
 * already have results) plus a History entry that opens the past-runs panel.
 *
 * A sticky left column on large screens; a sticky horizontal pill bar on
 * small ones. Brand + account live in the page header, so this stays nav-only.
 */
export default function Sidebar({ sections, onOpenHistory }) {
  const [activeId, setActiveId] = useState(sections[0]?.id);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActiveId(visible.target.id);
      },
      { rootMargin: "-30% 0px -55% 0px", threshold: [0, 0.25, 0.5] },
    );
    sections.forEach(({ id }) => {
      const node = document.getElementById(id);
      if (node) observer.observe(node);
    });
    return () => observer.disconnect();
  }, [sections]);

  const itemBase =
    "flex items-center gap-2.5 whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium transition-colors lg:w-full lg:rounded-xl lg:py-2.5";

  return (
    <aside className="sticky top-0 z-30 -mx-5 border-b border-paper-200 bg-paper-50/90 px-5 py-2 backdrop-blur-md sm:-mx-8 sm:px-8 lg:mx-0 lg:h-[calc(100vh-4rem)] lg:w-56 lg:shrink-0 lg:self-start lg:border-b-0 lg:border-r lg:border-paper-200 lg:bg-transparent lg:px-0 lg:py-6 lg:pr-6 lg:backdrop-blur-none">
      <nav aria-label="Dashboard sections">
        <ul className="flex gap-1 overflow-x-auto lg:flex-col lg:gap-1 lg:overflow-visible">
          {sections.map(({ id, label, ready }, index) => {
            const active = activeId === id;
            return (
              <li key={id}>
                <a
                  href={`#${id}`}
                  aria-current={active ? "location" : undefined}
                  className={`${itemBase} ${
                    active
                      ? "bg-ink-900 text-paper-50"
                      : "text-ink-500 hover:bg-paper-200/70 hover:text-ink-900"
                  }`}
                >
                  <span
                    className={`hidden h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-semibold lg:flex ${
                      active ? "bg-paper-50/20 text-paper-50" : "bg-paper-200 text-ink-500"
                    }`}
                  >
                    {index + 1}
                  </span>
                  <span className="flex-1">{label}</span>
                  {ready && (
                    <span
                      aria-label="completed"
                      className={`h-1.5 w-1.5 rounded-full ${
                        active ? "bg-gold-400" : "bg-emerald-500"
                      }`}
                    />
                  )}
                </a>
              </li>
            );
          })}
          <li className="lg:mt-2 lg:border-t lg:border-paper-200 lg:pt-3">
            <button type="button" onClick={onOpenHistory} className={`${itemBase} text-ink-500 hover:bg-paper-200/70 hover:text-ink-900`}>
              <span aria-hidden className="text-base leading-none">🕘</span>
              <span className="flex-1 text-left">History</span>
            </button>
          </li>
        </ul>
      </nav>
    </aside>
  );
}
