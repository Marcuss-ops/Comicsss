import React, { useState, useRef } from "react";
import { 
  Upload, Book, FileJson, Copy, Download, Volume2, VolumeX, 
  ChevronRight, ChevronLeft, BookOpen, Sparkles, Check, Play, User, RefreshCw
} from "lucide-react";
import { ExtractResponse, ExtractedPanel } from "../types";

export default function ComicPanelExtractor() {
  const [uploadedFiles, setUploadedFiles] = useState<{ name: string; type: string; data: string }[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [status, setStatus] = useState({
    step: "idle" as "idle" | "parsing" | "completed" | "failed",
    progress: 0,
    message: ""
  });
  
  const [extractedData, setExtractedData] = useState<ExtractResponse | null>(null);
  const [selectedPanelIndex, setSelectedPanelIndex] = useState<number>(0);
  const [viewMode, setViewMode] = useState<"cards" | "reader">("cards");
  const [copied, setCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [activeSpeechIndex, setActiveSpeechIndex] = useState<number | null>(null);
  
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

  const handleExtract = async () => {
    if (uploadedFiles.length === 0) return;

    setStatus({
      step: "parsing",
      progress: 30,
      message: "Processing pages with Gemini Core to extract multi-panel dialogue structure...",
    });

    try {
      // Map files to JSON payload structure
      const payloadFiles = uploadedFiles.map((f) => ({
        data: f.data,
        mimeType: f.type,
      }));

      const res = await fetch("/api/extract-panels", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ files: payloadFiles }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "The server failed to parse the comic.");
      }

      const responseData: ExtractResponse = await res.json();
      setExtractedData(responseData);
      setSelectedPanelIndex(0);

      setStatus({
        step: "completed",
        progress: 100,
        message: "Panel dialogues extracted successfully!",
      });
    } catch (err: any) {
      console.error(err);
      setStatus({
        step: "failed",
        progress: 0,
        message: err.message || "Failed to digest the comic book document panels.",
      });
    }
  };

  const copyToClipboard = () => {
    if (!extractedData) return;
    navigator.clipboard.writeText(JSON.stringify(extractedData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadJsonFile = () => {
    if (!extractedData) return;
    const blob = new Blob([JSON.stringify(extractedData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${extractedData.title || "comic_extract"}_panels.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const speakPanelDialogue = (panel: ExtractedPanel, idx: number) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    
    setIsSpeaking(true);
    setActiveSpeechIndex(idx);

    let textToSpeak = "";
    if (panel.youtubeDescription) {
      textToSpeak += `Scene context: ${panel.youtubeDescription}. `;
    }
    if (panel.narrativeCaption) {
      textToSpeak += `Narrator says: ${panel.narrativeCaption}. `;
    }

    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.rate = 1.0;
    utterance.pitch = 1.05;
    
    utterance.onend = () => {
      setIsSpeaking(false);
      setActiveSpeechIndex(null);
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
      setActiveSpeechIndex(null);
    };

    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
    setActiveSpeechIndex(null);
  };

  const handleReset = () => {
    setExtractedData(null);
    setUploadedFiles([]);
    setStatus({ step: "idle", progress: 0, message: "" });
  };

  return (
    <div id="comic-extractor-workspace" className="space-y-8">
      {!extractedData ? (
        <div className="bg-[#0C0C0E] border border-white/5 rounded-xl p-6 sm:p-8 shadow-2xl space-y-8 animate-fade-in text-[#E5E5E5]">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-5">
            <div>
              <span className="text-[10px] uppercase tracking-[0.2em] px-2.5 py-1 bg-[#A1824A]/10 text-[#A1824A] rounded-full border border-[#A1824A]/20 font-mono">
                SIMPLE COMIC JSON DIGEST
              </span>
              <h2 className="text-2xl font-serif italic text-white mt-2 flex items-center gap-2.5">
                <FileJson className="w-5 h-5 text-[#A1824A]" />
                Interactive Comic Panel & Dialogue Text Extractor
              </h2>
              <p className="text-xs text-neutral-400 mt-1">
                Upload image pages or full storybooks to automatically isolate page layouts, identify panels, and spit out raw dialogue data.
              </p>
            </div>
          </div>

          <div
            id="extractor-drop-zone"
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
                    browse document files
                  </button>
                </p>
                <p className="text-[11px] text-neutral-500 mt-1">
                  Supports manga, storyboard drawings, PDFs, JPGs, or PNG comic cuts.
                </p>
              </div>
            </div>

            {uploadedFiles.length > 0 && (
              <div className="mt-6 pt-6 border-t border-white/5 max-h-48 overflow-y-auto space-y-2 text-left">
                <div className="flex items-center justify-between text-xs text-neutral-400 px-1 mb-2">
                  <span className="uppercase tracking-[0.15em] text-[10px] font-medium text-white/60">
                    Ready Queue ({uploadedFiles.length} item(s)):
                  </span>
                  <button
                    onClick={clearUploaded}
                    className="text-red-400 hover:text-red-350 transition-colors cursor-pointer text-[10px] uppercase font-mono"
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
                      <BookOpen className="w-3.5 h-3.5 text-[#A1824A] shrink-0" />
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

          {status.step !== "idle" && status.step !== "completed" && status.step !== "failed" && (
            <div className="bg-[#0F0F11] rounded-xl p-5 border border-white/5 text-center animate-pulse space-y-3">
              <p className="text-[10px] uppercase tracking-[0.2em] text-[#A1824A] font-bold">
                NEURAL BOUNDARY OCR EXTRACTION IN PROGRESS...
              </p>
              <p className="text-xs font-light text-neutral-300">{status.message}</p>
              <div className="w-full bg-white/10 rounded-full h-1 overflow-hidden mt-2">
                <div
                  className="bg-[#A1824A] h-full transition-all duration-500"
                  style={{ width: `${status.progress}%` }}
                ></div>
              </div>
            </div>
          )}

          {status.step === "failed" && (
            <div className="bg-red-950/20 text-red-400 p-4 border border-red-900/40 rounded-xl text-center text-xs space-y-2">
              <p className="font-bold">Extraction Fault Encountered</p>
              <p>{status.message}</p>
              <button
                onClick={handleReset}
                className="mt-2 text-[#A1824A] underline font-semibold cursor-pointer"
              >
                Reset & retry
              </button>
            </div>
          )}

          <button
            disabled={uploadedFiles.length === 0 || status.step === "parsing"}
            onClick={handleExtract}
            className={`w-full py-4 rounded font-bold flex items-center justify-center gap-2.5 tracking-widest uppercase transition-all shadow-lg text-xs ${
              uploadedFiles.length === 0
                ? "bg-white/10 text-white/30 cursor-not-allowed border border-white/5"
                : "bg-[#A1824A] hover:brightness-110 text-black font-bold active:scale-95 cursor-pointer shadow-lg shadow-[#A1824A]/10"
            }`}
          >
            <FileJson className="w-4 h-4" />
            Isolate Panels & Export Dialogue JSON
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 animate-fade-in text-[#E5E5E5]">
          {/* Main Display Area (Left Panel) - Takes 7 Cols on desktop */}
          <div className="xl:col-span-7 space-y-6">
            
            {/* Header info card */}
            <div className="bg-[#0C0C0E] border border-white/5 rounded-xl p-6 relative">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] uppercase tracking-widest font-mono font-bold bg-[#A1824A]/15 text-[#A1824A] px-2 py-0.5 rounded border border-[#A1824A]/25">
                      Extracted Document
                    </span>
                    <span className="text-[9px] uppercase tracking-widest font-mono text-neutral-400">
                      Pages Analyzed: {extractedData.pageCount}
                    </span>
                  </div>
                  <h2 className="text-xl font-serif italic text-white mt-1.5">{extractedData.title}</h2>
                  <p className="text-xs text-neutral-400 leading-relaxed mt-1 font-light">
                    {extractedData.summary}
                  </p>
                </div>
                <button
                  onClick={handleReset}
                  className="px-3 py-1.5 text-xs font-mono uppercase border border-white/10 hover:bg-white/5 rounded text-neutral-400 hover:text-white shrink-0 self-start sm:self-center flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3 h-3" /> Parse New File
                </button>
              </div>

              {/* View toggle tabs */}
              <div className="flex items-center gap-1.5 bg-[#0F0F11] border border-white/5 p-1 rounded-sm mt-5 inline-flex">
                <button
                  onClick={() => setViewMode("cards")}
                  className={`px-3 py-1.5 text-xs font-bold font-mono uppercase rounded-sm transition-all flex items-center gap-1.5 ${
                    viewMode === "cards"
                      ? "bg-[#A1824A] text-black"
                      : "text-neutral-400 hover:text-white"
                  }`}
                >
                  <BookOpen className="w-3.5 h-3.5" /> Interactive Cards
                </button>
                <button
                  onClick={() => setViewMode("reader")}
                  className={`px-3 py-1.5 text-xs font-bold font-mono uppercase rounded-sm transition-all flex items-center gap-1.5 ${
                    viewMode === "reader"
                      ? "bg-[#A1824A] text-black"
                      : "text-neutral-400 hover:text-white"
                  }`}
                >
                  <ChevronRight className="w-3.5 h-3.5" /> Dialogue Panel Reader
                </button>
              </div>
            </div>

            {viewMode === "cards" ? (
              /* CARD VIEW - ALL detected panels in sequence */
              <div className="space-y-4 max-h-[1000px] overflow-y-auto pr-1">
                {extractedData.panels.map((panel, index) => (
                  <div 
                    key={index} 
                    className="bg-[#0C0C0E] border border-white/5 rounded-xl p-5 hover:border-[#A1824A]/20 transition-all space-y-4"
                  >
                    <div className="flex items-center justify-between border-b border-white/5 pb-2.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-[#A1824A] uppercase font-bold tracking-wider">
                          PANEL #{panel.panelNumber} (PAGE {panel.pageNumber})
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {panel.characters.map((char, cIdx) => (
                          <span key={cIdx} className="text-[9px] font-mono px-1.5 py-0.5 bg-[#A1824A]/10 text-white rounded-sm text-opacity-80">
                            {char}
                          </span>
                        ))}
                        <button
                          onClick={() => speakPanelDialogue(panel, index)}
                          className={`p-1.5 rounded-sm ${
                            activeSpeechIndex === index 
                              ? "bg-red-500/20 text-red-400 animate-pulse" 
                              : "bg-white/5 hover:bg-white/10 text-[#A1824A]"
                          }`}
                          title="Speak dialogues aloud using Neural TTS narrator"
                        >
                          {activeSpeechIndex === index ? <VolumeX className="w-3.5 h-3.5" onClick={(e) => { e.stopPropagation(); stopSpeaking(); }} /> : <Volume2 className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>

                    {panel.youtubeDescription && (
                      <div className="bg-[#A1824A]/5 border-l-2 border-[#A1824A] p-3 text-xs rounded-sm space-y-1">
                        <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-[#A1824A] flex items-center gap-1.5 font-bold">
                          <Sparkles className="w-3" /> YouTube Video Narrator Cue
                        </span>
                        <p className="text-stone-200 font-sans leading-relaxed">{panel.youtubeDescription}</p>
                      </div>
                    )}

                    {panel.narrativeCaption && (
                      <div className="bg-[#A1824A]/5 border-l-2 border-[#A1824A] p-3 text-xs rounded-sm">
                        <span className="text-[9px] font-mono uppercase tracking-widest text-[#A1824A] block mb-1">Narration Box Caption:</span>
                        <p className="text-stone-300 italic font-serif">{panel.narrativeCaption}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              /* DETAILED READER VIEW - Focus on one panel at a time */
              <div className="bg-[#0C0C0E] border border-white/5 rounded-xl p-8 space-y-6 flex flex-col justify-between min-h-[500px]">
                {(() => {
                  const currentPanel = extractedData.panels[selectedPanelIndex];
                  if (!currentPanel) return <p className="text-center text-xs text-neutral-500">No panels available to draw.</p>;
                  return (
                    <>
                      <div className="space-y-6 flex-1">
                        {/* Panel Indicator */}
                        <div className="flex items-center justify-between border-b border-white/5 pb-4">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono font-bold tracking-widest text-[#A1824A]">
                              PANEL FOCUS: {selectedPanelIndex + 1} OF {extractedData.panels.length}
                            </span>
                            <span className="text-[9px] font-mono bg-white/5 px-2 py-0.5 rounded text-[#A1824A] border border-white/5 uppercase">
                              Page {currentPanel.pageNumber} • Panel {currentPanel.panelNumber}
                            </span>
                          </div>
                        </div>

                        {/* YouTube Narrator Cue */}
                        {currentPanel.youtubeDescription && (
                          <div className="bg-[#A1824A]/5 border-l-2 border-[#A1824A] p-4 rounded-sm text-stone-200 space-y-1">
                            <span className="text-[10px] font-mono tracking-wider text-[#A1824A] flex items-center gap-1.5 font-bold uppercase">
                              <Sparkles className="w-3.5 h-3.5 text-[#A1824A]" /> YouTube Video Narrator Cue
                            </span>
                            <p className="text-stone-300 text-sm leading-relaxed">{currentPanel.youtubeDescription}</p>
                          </div>
                        )}

                        {/* Caption Box */}
                        {currentPanel.narrativeCaption && (
                          <div className="bg-[#A1824A]/5 border-l-2 border-[#A1824A] p-4 rounded-sm text-stone-200">
                            <span className="text-[10px] font-mono tracking-wider text-[#A1824A] block mb-1 uppercase">Narration Voiceover:</span>
                            <p className="font-serif italic text-sm">"{currentPanel.narrativeCaption}"</p>
                          </div>
                        )}
                      </div>

                      {/* Speaking & Control buttons */}
                      <div className="flex items-center justify-between border-t border-white/5 pt-6 mt-6">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => speakPanelDialogue(currentPanel, selectedPanelIndex)}
                            className={`px-4 py-2 bg-white/5 hover:bg-white/10 text-xs rounded font-bold uppercase tracking-wider flex items-center gap-2 ${
                              isSpeaking ? "text-red-400 animate-pulse border border-red-950" : "text-[#A1824A]"
                            }`}
                          >
                            {isSpeaking ? <VolumeX className="w-4 h-4 text-red-400" onClick={(e) => { e.stopPropagation(); stopSpeaking(); }} /> : <Volume2 className="w-4 h-4 text-[#A1824A]" />}
                            {isSpeaking ? "Narrating..." : "Read Aloud Panel"}
                          </button>
                        </div>

                        {/* Pagination */}
                        <div className="flex items-center gap-2">
                          <button
                            disabled={selectedPanelIndex === 0}
                            onClick={() => setSelectedPanelIndex((prev) => prev - 1)}
                            className="p-2 bg-white/5 border border-white/10 hover:border-[#A1824A]/30 text-white rounded cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <ChevronLeft className="w-4 h-4" />
                          </button>
                          <span className="text-xs font-mono font-bold mx-2">
                            {selectedPanelIndex + 1} / {extractedData.panels.length}
                          </span>
                          <button
                            disabled={selectedPanelIndex === extractedData.panels.length - 1}
                            onClick={() => setSelectedPanelIndex((prev) => prev + 1)}
                            className="p-2 bg-white/5 border border-white/10 hover:border-[#A1824A]/30 text-white rounded cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </>
                  );
                })()}
              </div>
            )}
          </div>

          {/* JSON Terminal Area (Right Panel) - Takes 5 Cols on desktop */}
          <div className="xl:col-span-5 space-y-6">
            <div className="bg-[#0C0C0E] border border-white/5 rounded-xl p-6 space-y-4 flex flex-col justify-start min-h-[600px]">
              <div className="flex items-center justify-between border-b border-white/5 pb-3">
                <div className="flex items-center gap-2">
                  <FileJson className="w-4.5 h-4.5 text-[#A1824A]" />
                  <h3 className="text-sm uppercase tracking-[0.2em] font-medium text-white">Parsed Dialogue JSON</h3>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={copyToClipboard}
                    className="p-2 bg-white/5 border border-white/10 hover:bg-white/10 text-[#A1824A] rounded hover:text-white text-xs flex items-center gap-1.5 transition-all text-[11px] uppercase font-mono font-medium"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copied ? "Copied" : "Copy"}
                  </button>
                  <button
                    onClick={downloadJsonFile}
                    className="p-2 bg-[#A1824A]/15 border border-[#A1824A]/20 hover:bg-[#A1824A]/30 text-[#A1824A] rounded text-xs flex items-center gap-1.5 transition-all text-[11px] uppercase font-mono font-medium"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </button>
                </div>
              </div>

              <div className="flex-1 bg-[#050506] border border-white/5 rounded p-4 overflow-auto max-h-[800px] font-mono text-[11px] leading-relaxed text-[#00E5FF]/90 scrollbar-thin">
                <pre className="whitespace-pre-wrap select-all selection:bg-cyan-500/20">
                  {JSON.stringify(extractedData, null, 2)}
                </pre>
              </div>

              <div className="text-[10px] text-neutral-500 font-mono leading-relaxed pt-2">
                This structured schema includes extracted panel coordinates, relative locations, narration texts, scenery descriptions and YouTube comment scripts suitable for immediately producing a video.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
