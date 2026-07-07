import { useEffect, useState } from "react";

/**
 * Sticky in-page navigation for the four connected module sections, with
 * scroll-spy highlighting of the section currently in view.
 */
export default function SectionNav({ sections }) {
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

  return (
    <nav
      aria-label="Dashboard sections"
      className="sticky top-0 z-40 -mx-5 border-b border-paper-200 bg-paper-50/90 px-5 backdrop-blur-md sm:-mx-8 sm:px-8"
    >
      <ul className="mx-auto flex max-w-5xl gap-1 overflow-x-auto py-2">
        {sections.map(({ id, label, ready }) => (
          <li key={id}>
            <a
              href={`#${id}`}
              aria-current={activeId === id ? "location" : undefined}
              className={`flex items-center gap-2 whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                activeId === id
                  ? "bg-ink-900 text-paper-50"
                  : "text-ink-500 hover:bg-paper-200/70 hover:text-ink-900"
              }`}
            >
              {label}
              {ready && (
                <span
                  aria-label="completed"
                  className={`h-1.5 w-1.5 rounded-full ${
                    activeId === id ? "bg-gold-400" : "bg-emerald-500"
                  }`}
                />
              )}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
