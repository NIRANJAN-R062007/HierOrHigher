import Faq from "../components/landing/Faq";
import Footer from "../components/landing/Footer";
import Hero from "../components/landing/Hero";
import HowItWorks from "../components/landing/HowItWorks";
import ModuleShowcase from "../components/landing/ModuleShowcase";
import Navbar from "../components/landing/Navbar";
import Outcomes from "../components/landing/Outcomes";
import ScrollProgress from "../components/landing/ScrollProgress";
import StatsBand from "../components/landing/StatsBand";

/** Marketing page: cinematic dark, editorial type, scroll-triggered motion. */
export default function Landing() {
  return (
    <div className="bg-ink-950 text-paper-50">
      <ScrollProgress />
      <Navbar />
      <main>
        <Hero />
        <HowItWorks />
        <ModuleShowcase />
        <StatsBand />
        <Outcomes />
        <Faq />
      </main>
      <Footer />
    </div>
  );
}
