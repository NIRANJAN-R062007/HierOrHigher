import { useEffect, useRef } from "react";

/**
 * Scroll-triggered reveal: returns a ref; the element gets `.is-visible`
 * once it enters the viewport (pairs with the `.reveal` CSS class).
 */
export function useReveal() {
  const ref = useRef(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return ref;
}
