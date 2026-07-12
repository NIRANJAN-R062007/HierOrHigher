import Footer from "../components/landing/Footer";
import Navbar from "../components/landing/Navbar";
import CurriculumTimeline from "../components/masterclass/CurriculumTimeline";
import EnrollCta from "../components/masterclass/EnrollCta";
import MasterclassHero from "../components/masterclass/MasterclassHero";
import MentorSpotlight from "../components/masterclass/MentorSpotlight";
import StatsBand from "../components/masterclass/StatsBand";
import TopicTicker from "../components/masterclass/TopicTicker";

/** Event-style landing page for the live career masterclass. */
export default function Masterclass() {
  return (
    <div className="bg-ink-950 text-paper-50">
      <Navbar />
      <main>
        <MasterclassHero />
        <TopicTicker />
        <CurriculumTimeline />
        <StatsBand />
        <MentorSpotlight />
        <EnrollCta />
      </main>
      <Footer />
    </div>
  );
}
