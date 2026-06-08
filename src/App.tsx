import { useState } from "react";
import { Film, BookOpen, ShieldAlert, BadgeCheck, HelpCircle, FileText, PlayCircle } from "lucide-react";
import StoryboardCreator from "./components/StoryboardCreator";
import CinematicVideoPlayer from "./components/CinematicVideoPlayer";
import ComicPanelExtractor from "./components/ComicPanelExtractor";
import { Storyboard, GenerationStatus } from "./types";

export default function App() {
  const [activeTab, setActiveTab] = useState<"extractor" | "cinematic">("extractor");
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [originalImages, setOriginalImages] = useState<string[]>([]);
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus>({
    step: "idle",
    progress: 0,
    message: "",
  });

  const handleStoryboardGenerated = (newStoryboard: Storyboard, images: string[]) => {
    setStoryboard(newStoryboard);
    setOriginalImages(images);
  };

  const clearActiveStoryboard = () => {
    setStoryboard(null);
    setOriginalImages([]);
    setGenerationStatus({ step: "idle", progress: 0, message: "" });
  };

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col font-sans selection:bg-[#A1824A] selection:text-[#0A0A0B] text-[#E5E5E5]">
      
      {/* Delicate Dark Ambient Overlay Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.01)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.01)_1px,transparent_1px)] bg-[size:3rem_3rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_60%,transparent_100%)] pointer-events-none z-0"></div>

      {/* Main Header / Navigation Bar styled after the premium design */}
      <header className="relative border-b border-white/5 bg-[#0F0F11] z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-[#A1824A] rounded flex items-center justify-center text-black shadow-md">
              <Film className="w-5 h-5 text-black" />
            </div>
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-xl tracking-widest font-serif italic font-semibold text-white">TOONPLAY</span>
                <span className="text-[10px] text-[#A1824A] uppercase tracking-[0.2em] font-medium">Pageslate Studio</span>
              </div>
              <p className="text-xs text-neutral-450 font-light mt-0.5">
                Convert static files into cinematic video slideshows with speech narration & sound FX overlays
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 self-start sm:self-center">
            <div className="text-right hidden sm:block">
              <span className="text-[9px] font-mono text-[#A1824A] block uppercase tracking-widest">Neural Adaptation Engine v2.4</span>
              <span className="text-[11px] text-white/50 font-mono font-medium flex items-center gap-1.5 justify-end mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]"></span>
                Google GenAI Active
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Primary Workspace container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10 flex flex-col justify-start">
        
        {/* Workspace Mode Tabs selector */}
        {!storyboard && (
          <div className="flex bg-[#0C0C0E]/60 border border-white/5 p-1 rounded max-w-xl mx-auto mb-8 w-full">
            <button
              onClick={() => setActiveTab("extractor")}
              className={`flex-1 py-2.5 text-xs font-mono uppercase font-semibold tracking-wider transition-all flex items-center justify-center gap-2 rounded-sm cursor-pointer ${
                activeTab === "extractor"
                  ? "bg-[#A1824A] text-black font-bold"
                  : "text-neutral-400 hover:text-white"
              }`}
            >
              <FileText className="w-3.5 h-3.5" /> Dialogue JSON Extractor
            </button>
            <button
              onClick={() => setActiveTab("cinematic")}
              className={`flex-1 py-2.5 text-xs font-mono uppercase font-semibold tracking-wider transition-all flex items-center justify-center gap-2 rounded-sm cursor-pointer ${
                activeTab === "cinematic"
                  ? "bg-[#A1824A] text-black font-bold"
                  : "text-neutral-400 hover:text-white"
              }`}
            >
              <Film className="w-3.5 h-3.5" /> Cinematic Movie Maker
            </button>
          </div>
        )}

        {storyboard ? (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#0C0C0E] border border-white/5 p-4 rounded-xl">
              <div>
                <h2 className="text-lg font-serif italic text-white flex items-center gap-2">
                  <Film className="w-5 h-5 text-[#A1824A]" />
                  Scene Control Room
                </h2>
                <p className="text-xs text-[#E5E5E5]/70 mt-0.5">
                  Play the animated story, customize speakers, or regenerate high fidelity widescreen slide designs.
                </p>
              </div>
              <button
                onClick={clearActiveStoryboard}
                className="px-4 py-2 bg-white/5 hover:bg-white/10 text-white/80 hover:text-white transition-all text-xs font-semibold rounded-xl border border-white/10 uppercase tracking-wider"
              >
                ← Back to Parser Upload
              </button>
            </div>

            <CinematicVideoPlayer
              storyboard={storyboard}
              originalImages={originalImages}
              onBackToUpload={clearActiveStoryboard}
            />
          </div>
        ) : activeTab === "extractor" ? (
          <ComicPanelExtractor />
        ) : (
          <div className="space-y-8 max-w-4xl mx-auto w-full">
            <StoryboardCreator
              onStoryboardGenerated={handleStoryboardGenerated}
              status={generationStatus}
              setStatus={setGenerationStatus}
            />

            {/* Quick Informational Guide Cards - Cinematic Process description */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-white/5">
              
              <div className="bg-[#0C0C0E] border border-white/5 p-4 rounded-xl space-y-2">
                <div className="w-8 h-8 rounded-lg bg-[#A1824A]/10 flex items-center justify-center border border-[#A1824A]/20">
                  <BookOpen className="w-4 h-4 text-[#A1824A]" />
                </div>
                <h4 className="text-[10px] uppercase tracking-[0.2em] text-[#A1824A] font-bold">1. Upload & Analyze</h4>
                <p className="text-[11px] text-neutral-400 leading-relaxed font-light">
                  Supply single/multi image strips or full storybook PDFs. Gemini analyzes text bubbles and characters page-by-page.
                </p>
              </div>

              <div className="bg-[#0C0C0E] border border-white/5 p-4 rounded-xl space-y-2">
                <div className="w-8 h-8 rounded-lg bg-[#A1824A]/10 flex items-center justify-center border border-[#A1824A]/20">
                  <Film className="w-4 h-4 text-[#A1824A]" />
                </div>
                <h4 className="text-[10px] uppercase tracking-[0.2em] text-[#A1824A] font-bold">2. Adaptive Animation</h4>
                <p className="text-[11px] text-neutral-400 leading-relaxed font-light">
                  Gemini generates wide visual graphics, sound FX markers, speech bubble overlays, and plans cinematic Ken Burns pans/zooms.
                </p>
              </div>

              <div className="bg-[#0C0C0E] border border-white/5 p-4 rounded-xl space-y-2">
                <div className="w-8 h-8 rounded-lg bg-[#A1824A]/10 flex items-center justify-center border border-[#A1824A]/20">
                  <HelpCircle className="w-4 h-4 text-[#A1824A]" />
                </div>
                <h4 className="text-[10px] uppercase tracking-[0.2em] text-[#A1824A] font-bold">3. Narrated TTS Audio</h4>
                <p className="text-[11px] text-neutral-400 leading-relaxed font-light">
                  Synthesizes custom narrator voice presets, character lines, and couples them with procedural sci-fi or dramatic drones.
                </p>
              </div>

            </div>
          </div>
        )}
      </main>

      {/* Persistent platform footer */}
      <footer className="h-10 bg-[#0F0F11] border-t border-white/5 flex items-center justify-between px-6 text-[10px] uppercase tracking-[0.2em] font-medium text-white/40">
        <div className="flex gap-6">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]"></span>
            NEURAL ENGINE ACTIVE
          </div>
          <div className="hidden sm:block">GPU LOAD: 74%</div>
        </div>
        <div className="flex gap-4 font-mono font-medium">
          <span className="text-[#A1824A]">v2.4.0-stable</span>
          <span className="hidden sm:inline">PRO STATUS INGRESS</span>
        </div>
      </footer>
    </div>
  );
}
