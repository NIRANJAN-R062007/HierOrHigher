import Footer from "../components/landing/Footer";
import Hero from "../components/landing/Hero";
import ModuleShowcase from "../components/landing/ModuleShowcase";
import Navbar from "../components/landing/Navbar";
import Outcomes from "../components/landing/Outcomes";

/** Marketing page: cinematic dark, editorial type, scroll-triggered motion. */
export default function Landing() {
  return (
    <div className="bg-ink-950 text-paper-50">
      <Navbar />
      <main>
        <Hero />
        <ModuleShowcase />
        <Outcomes />
      </main>
      <Footer />
    </div>
  );
}
