import Footer from "../components/landing/Footer";
import Hero from "../components/landing/Hero";
import HowItWorks from "../components/landing/HowItWorks";
import ModuleShowcase from "../components/landing/ModuleShowcase";
import Navbar from "../components/landing/Navbar";
import Outcomes from "../components/landing/Outcomes";
import StatsBand from "../components/landing/StatsBand";

/** Marketing page: cinematic dark, editorial type, scroll-triggered motion. */
export default function Landing() {
  return (
    <div className="bg-ink-950 text-paper-50">
      <Navbar />
      <main>
        <Hero />
        <HowItWorks />
        <ModuleShowcase />
        <StatsBand />
        <Outcomes />
      </main>
      <Footer />
    </div>
  );
}
