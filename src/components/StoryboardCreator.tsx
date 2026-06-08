import React, { useState, useRef } from "react";
import { Upload, Book, Settings, Compass, Sparkles, Film, Image as ImageIcon } from "lucide-react";
import { Storyboard, GenerationStatus } from "../types";

interface StoryboardCreatorProps {
  onStoryboardGenerated: (storyboard: Storyboard, originalImages: string[]) => void;
  status: GenerationStatus;
  setStatus: React.Dispatch<React.SetStateAction<GenerationStatus>>;
}

const COMIC_STYLES = [
  { name: "Classic Widescreen Comicbook", desc: "Bold lines, vintage ben-day dots, rich classic ink", val: "1980s Retro Marvel Comic book style" },
  { name: "Noir Ink Graphic Novel", desc: "Heavy shadows, high contrast black & white wash", val: "Sin City noir ink wash graphic novel style, high contrast dark atmosphere" },
  { name: "Sleek Manga Sketch", desc: "Japanese manga line art with dynamic speedlines", val: "Modern action manga art, highly detailed anime line art" },
  { name: "Futuristic Synthwave Cyberpunk", desc: "Vibrant neon tones and gridscapes", val: "Neon glowing cyberpunk comic book art with deep purple and cyan, retro-future" },
  { name: "Widescreen Cinematic Oil Painting", desc: "Dramatically lit, rich brushwork and textures", val: "Cinematic digital oil painting graphic novel, dramatic rim lighting" }
];

const STORY_GENRES = [
  "Action Adventure",
  "Sci-Fi / Space Opera",
  "Fantasy Epic",
  "Comedy Slapstick",
  "Mystery Detective",
  "Horror Thug",
  "Historical Chronicle"
];

export default function StoryboardCreator({
  onStoryboardGenerated,
  status,
  setStatus,
}: StoryboardCreatorProps) {
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<{ name: string; type: string; data: string }[]>([]);
  const [styleTemplate, setStyleTemplate] = useState(COMIC_STYLES[0].val);
  const [selectedGenre, setSelectedGenre] = useState("Matched automatically");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const processFiles = (filesList: FileList) => {
    const promises: Promise<{ name: string; type: string; data: string }>[] = [];

    Array.from(filesList).forEach((file) => {
      const reader = new FileReader();
      const promise = new Promise<{ name: string; type: string; data: string }>((resolve) => {
        reader.onload = (e) => {
          resolve({
            name: file.name,
            type: file.type || (file.name.endsWith(".cbz") ? "application/zip" : "image/jpeg"),
            data: e.target?.result as string,
          });
        };
        reader.readAsDataURL(file);
      });
      promises.push(promise);
    });

    Promise.all(promises).then((results) => {
      setUploadedFiles((prev) => [...prev, ...results]);
    });
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      processFiles(e.target.files);
    }
  };

  const clearUploaded = () => {
    setUploadedFiles([]);
  };

  const handleGenerate = async () => {
    if (uploadedFiles.length === 0) return;

    setStatus({
      step: "parsing",
      progress: 25,
      message: "Sending file parts to Google Gemini to distill comic scenes...",
    });

    try {
      // Map files to JSON payload structure
      const payloadFiles = uploadedFiles.map((f) => ({
        data: f.data,
        mimeType: f.type,
      }));

      const res = await fetch("/api/read-comic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          files: payloadFiles,
          customGenre: selectedGenre,
          customStyle: styleTemplate,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "The server failed to translate the document.");
      }

      const parsedStoryboard: Storyboard = await res.json();

      // Filter uploaded image URLs to map back as original visual references
      const originalImageUrls = uploadedFiles
        .filter((f) => f.type.startsWith("image/"))
        .map((f) => f.data);

      setStatus({
        step: "completed",
        progress: 100,
        message: "Cinematic adaptation complete!",
      });

      onStoryboardGenerated(parsedStoryboard, originalImageUrls);
    } catch (err: any) {
      console.error(err);
      setStatus({
        step: "failed",
        progress: 0,
        message: err.message || "Something went wrong in the story synthesis phase.",
      });
    }
  };

  const imagesCount = uploadedFiles.filter((f) => f.type.startsWith("image/")).length;
  const pdfsCount = uploadedFiles.filter((f) => f.type.includes("pdf")).length;

  return (
    <div id="storyboard-creator-card" className="bg-[#0C0C0E] border border-white/5 rounded-xl p-6 sm:p-8 shadow-2xl space-y-8 animate-fade-in text-[#E5E5E5]">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-5">
        <div>
          <span className="text-[10px] uppercase tracking-[0.2em] px-2.5 py-1 bg-[#A1824A]/10 text-[#A1824A] rounded-full border border-[#A1824A]/20 font-mono">
            STEP 01: STORY DIGEST
          </span>
          <h2 className="text-2xl font-serif italic text-white mt-2 flex items-center gap-2.5">
            <Book className="w-5 h-5 text-[#A1824A]" />
            Direct Comic or PDF into Cinematic Storyboard
          </h2>
          <p className="text-xs text-neutral-450 mt-1">
            Upload comic strips, drawings, manga pages, or storybooks to analyze and cast characters with speech and sound bubbles.
          </p>
        </div>
      </div>

      {/* Drag & Drop Canvas */}
      <div
        id="uploader-drop-zone"
        className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all ${
          dragActive
            ? "border-[#A1824A] bg-[#A1824A]/5"
            : "border-white/10 bg-white/5 hover:border-[#A1824A]/40"
        }`}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          id="input-file-upload"
          multiple
          accept="image/*,application/pdf"
          className="hidden"
          onChange={handleChange}
        />

        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="p-4 bg-white/5 rounded-full border border-white/10 group-hover:scale-105 transition-transform">
            <Upload className="w-8 h-8 text-[#A1824A]" />
          </div>
          <div>
            <p className="text-sm font-medium">
              Drag & drop files here, or{" "}
              <button
                type="button"
                className="text-[#A1824A] hover:text-[#c4a974] font-semibold underline"
                onClick={() => fileInputRef.current?.click()}
              >
                browse matching pages
              </button>
            </p>
            <p className="text-[11px] text-neutral-500 mt-1">
              Supports PDF documents, JPEGs, PNGs, and WEBP comic files.
            </p>
          </div>
        </div>

        {uploadedFiles.length > 0 && (
          <div className="mt-6 pt-6 border-t border-white/5 max-h-48 overflow-y-auto space-y-2 text-left">
            <div className="flex items-center justify-between text-xs text-neutral-400 px-1 mb-2">
              <span className="uppercase tracking-[0.15em] text-[10px] font-medium text-white/60">Ready Stack ({uploadedFiles.length} file(s)):</span>
              <button
                onClick={clearUploaded}
                className="text-red-400 hover:text-red-300 transition-colors cursor-pointer text-[10px] uppercase font-mono"
              >
                Clear all
              </button>
            </div>
            {uploadedFiles.map((file, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between bg-black/40 px-3 py-2 rounded border border-white/5 text-xs"
              >
                <div className="flex items-center gap-2 truncate">
                  {file.type.startsWith("image/") ? (
                    <ImageIcon className="w-4 h-4 text-[#A1824A] shrink-0" />
                  ) : (
                    <Film className="w-4 h-4 text-[#A1824A] shrink-0" />
                  )}
                  <span className="truncate text-white/80">{file.name}</span>
                </div>
                <span className="text-[9px] font-mono text-[#A1824A] uppercase px-1.5 py-0.5 bg-white/5 rounded">
                  {file.type.split("/")[1] || "File"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Style Design Panel */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
        <div className="space-y-3">
          <label className="text-[10px] uppercase tracking-[0.2em] text-[#A1824A] font-bold block">
            Visual Adaptation Style
          </label>
          <div className="grid grid-cols-1 gap-2">
            {COMIC_STYLES.map((style) => (
              <button
                key={style.val}
                onClick={() => setStyleTemplate(style.val)}
                className={`text-left p-3 rounded border transition-all flex flex-col ${
                  styleTemplate === style.val
                    ? "bg-white/10 border-[#A1824A] text-[#A1824A] ring-1 ring-[#A1824A]"
                    : "bg-white/5 border border-white/10 text-[#E5E5E5]/80 hover:bg-white/10"
                }`}
              >
                <span className="text-xs font-bold flex items-center gap-2">
                  <Sparkles className={`w-3.5 h-3.5 ${styleTemplate === style.val ? "text-[#A1824A]" : "text-neutral-500"}`} />
                  {style.name}
                </span>
                <span className="text-[11px] text-neutral-400 mt-0.5 font-light leading-relaxed">
                  {style.desc}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="space-y-3">
            <label className="text-[10px] uppercase tracking-[0.2em] text-[#A1824A] font-bold block">
              Narrative Adaptation Genre
            </label>
            <div className="flex flex-wrap gap-1.5">
              {STORY_GENRES.map((genre) => (
                <button
                  key={genre}
                  onClick={() => setSelectedGenre(genre)}
                  className={`px-3 py-1.5 rounded text-[11px] font-medium border transition-colors ${
                    selectedGenre === genre
                      ? "bg-[#A1824A]/10 text-[#A1824A] border-[#A1824A]/20"
                      : "bg-[#0A0A0B] text-neutral-455 border border-white/5 hover:text-white"
                  }`}
                >
                  {genre}
                </button>
              ))}
              <button
                onClick={() => setSelectedGenre("Matched automatically")}
                className={`px-3 py-1.5 rounded text-[11px] font-medium border transition-colors ${
                  selectedGenre === "Matched automatically"
                    ? "bg-[#A1824A]/10 text-[#A1824A] border-[#A1824A]/21"
                    : "bg-[#0A0A0B] text-neutral-455 border border-white/5 hover:text-white"
                }`}
              >
                Auto-Detect From File
              </button>
            </div>
          </div>

          <div className="bg-white/5 rounded p-4 border border-white/5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-neutral-300 flex items-center gap-1.5">
                <Settings className="w-3.5 h-3.5 text-neutral-400" />
                Custom Model Options
              </span>
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-[10px] text-[#A1824A] hover:underline"
              >
                {showAdvanced ? "Hide settings" : "Show settings"}
              </button>
            </div>

            {showAdvanced && (
              <div className="space-y-3 pt-2 text-xs text-neutral-400 animate-slide-down">
                <div>
                  <label className="block text-[10px] text-neutral-400 font-mono mb-1 uppercase">
                    Custom Prompt Override (Add elements)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Include vibrant synth lines, futuristic cinematic lightning, dynamic 8k..."
                    value={styleTemplate}
                    onChange={(e) => setStyleTemplate(e.target.value)}
                    className="w-full bg-[#0A0A0B] border border-white/10 rounded px-2.5 py-1.5 text-xs text-neutral-200 focus:outline-none focus:border-[#A1824A]"
                  />
                </div>
              </div>
            )}

            <div className="text-xs space-y-1 text-neutral-400">
              <p className="flex items-center gap-1.5 pt-1">
                <span className="inline-block w-1.5 h-1.5 bg-[#A1824A] rounded-full animate-ping"></span>
                Using: <strong className="text-[#A1824A] font-mono">gemini-3.5-flash</strong> (Multimodal Engine)
              </p>
              <p className="text-[10px] text-neutral-500 font-light leading-relaxed">
                Securely processes content server-side. Text is converted using high-fidelity pre-compiled story schemas.
              </p>
            </div>
          </div>
        </div>
      </div>

      {status.step !== "idle" && status.step !== "completed" && status.step !== "failed" && (
        <div className="bg-[#0F0F11] rounded-xl p-5 border border-white/5 text-center animate-pulse space-y-3">
          <p className="text-[10px] uppercase tracking-[0.2em] text-[#A1824A] font-bold">
            {status.step === "parsing" ? "DIGESTING PAGES..." : "COMPILING CINEMA..."}
          </p>
          <p className="text-sm font-light text-neutral-300">{status.message}</p>
          <div className="w-full bg-white/10 rounded-full h-1 overflow-hidden mt-2">
            <div
              className="bg-[#A1824A] h-full transition-all duration-500"
              style={{ width: `${status.progress}%` }}
            ></div>
          </div>
        </div>
      )}

      {status.step === "failed" && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-xs text-red-200 text-center">
          <p className="font-bold mb-1">Compilation Blocked</p>
          <p>{status.message}</p>
          <button
            onClick={() => setStatus({ step: "idle", progress: 0, message: "" })}
            className="mt-2 text-[#A1824A] underline font-semibold cursor-pointer"
          >
            Reset Upload Queue
          </button>
        </div>
      )}

      <button
        id="btn-trigger-cinema-generation"
        disabled={uploadedFiles.length === 0 || status.step === "parsing"}
        onClick={handleGenerate}
        className={`w-full py-4 rounded font-bold flex items-center justify-center gap-2.5 tracking-widest uppercase transition-all shadow-lg text-xs ${
          uploadedFiles.length === 0
            ? "bg-white/10 text-white/30 cursor-not-allowed border border-white/5"
            : "bg-[#A1824A] hover:brightness-110 text-black font-bold active:scale-95 cursor-pointer shadow-lg shadow-[#A1824A]/10"
        }`}
      >
        <Film className="w-4 h-4" />
        Generate Comic Cinematic Screenplay
      </button>
    </div>
  );
}
