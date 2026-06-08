import React, { useState, useEffect, useRef } from "react";
import { Play, Pause, Square, Music, Volume2, VolumeX, RotateCcw, ChevronRight, ChevronLeft, Sparkles, Wand2, Volume1, Film, Maximize2, Download, Edit, Check, ArrowRight, Eye, Monitor, Smartphone, LayoutGrid } from "lucide-react";
import { Storyboard, Scene } from "../types";
import { audioSynth } from "../utils/audioSynth";

interface CinematicVideoPlayerProps {
  storyboard: Storyboard;
  originalImages: string[];
  onBackToUpload: () => void;
}

export default function CinematicVideoPlayer({
  storyboard: initialStoryboard,
  originalImages,
  onBackToUpload,
}: CinematicVideoPlayerProps) {
  // Configured Storyboard State
  const [storyboard, setStoryboard] = useState<Storyboard>(initialStoryboard);
  const [selectedSceneIndex, setSelectedSceneIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackTime, setPlaybackTime] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [synthSoundtrackEnabled, setSynthSoundtrackEnabled] = useState(false);
  const [viewMode, setViewMode] = useState<"ai_widescreen" | "original">("ai_widescreen");
  const [aspectRatio, setAspectRatio] = useState<"16_9" | "9_16" | "1_1">("16_9");
  
  // Custom edits states
  const [editingSceneId, setEditingSceneId] = useState<string | null>(null);
  const [editNarratorText, setEditNarratorText] = useState("");
  const [editDialogueText, setEditDialogueText] = useState("");
  const [editSpeaker, setEditSpeaker] = useState("");
  const [editSoundEffect, setEditSoundEffect] = useState("");
  const [editCamera, setEditCamera] = useState<any>("static");

  // Dynamic Assets Generation States
  const [assetsStatus, setAssetsStatus] = useState<{ [sceneId: string]: 'idle' | 'generating' | 'ready' | 'error' }>({});
  const [activeVoice, setActiveVoice] = useState("Kore"); // Kore, Puck, Fenrir, Zephyr
  const [veoSupportMode, setVeoSupportMode] = useState(false); // Enable Veo AI videos

  // HTML5 audio refs
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const playbackTimerRef = useRef<any>(null);

  const activeScene = storyboard.scenes[selectedSceneIndex];

  // Initiate default status states upon load
  useEffect(() => {
    const freshStatus: any = {};
    storyboard.scenes.forEach((sc) => {
      freshStatus[sc.id] = sc.imageUrl || sc.speechAudio ? 'ready' : 'idle';
    });
    setAssetsStatus(freshStatus);

    // Warm-up clean voice setup if WebSpeech voice is required
    return () => {
      audioSynth.stop();
      if (playbackTimerRef.current) clearInterval(playbackTimerRef.current);
    };
  }, [storyboard]);

  // Handle procedural audio synthesizer triggers
  useEffect(() => {
    if (synthSoundtrackEnabled && isPlaying) {
      audioSynth.start(storyboard.soundtrackStyle);
    } else {
      audioSynth.stop();
    }
  }, [synthSoundtrackEnabled, isPlaying, storyboard.soundtrackStyle]);

  // Speech browser fallback if audio block represents TTS fail
  const triggerBrowserSpeechFallback = (text: string) => {
    try {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.05;
        // Map mock voice pitch
        if (activeVoice === "Puck") utterance.pitch = 1.25;
        if (activeVoice === "Fenrir") utterance.pitch = 0.8;
        window.speechSynthesis.speak(utterance);
      }
    } catch (e) {
      console.warn("Speech Synthesis fallback failed", e);
    }
  };

  // Run or control scene play triggers
  const playCurrentSceneAssets = () => {
    if (!isPlaying) return;

    // Reset Speech synthesis
    if (window.speechSynthesis) window.speechSynthesis.cancel();

    // Play synthesized narration if downloaded
    if (activeScene.speechAudio) {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      const audioObj = new Audio(activeScene.speechAudio);
      audioObj.muted = isMuted;
      audioRef.current = audioObj;
      audioObj.play().catch((err) => {
        console.warn("Audio element blocked, executing fallback TTS:", err);
        triggerBrowserSpeechFallback(`${activeScene.narratorText}. ${activeScene.characterDialogueSpeaker} says: ${activeScene.characterDialogue}`);
      });
    } else {
      // Fallback voice reading
      triggerBrowserSpeechFallback(`${activeScene.narratorText}. ${activeScene.characterDialogueSpeaker} says: ${activeScene.characterDialogue}`);
    }

    // Set timeline timer to advance to next scene dynamically
    if (playbackTimerRef.current) clearInterval(playbackTimerRef.current);
    
    setPlaybackTime(0);
    const stepInterval = 100; // ms
    let timeElapsed = 0;
    const totalDurationMs = activeScene.duration * 1000;

    playbackTimerRef.current = setInterval(() => {
      timeElapsed += stepInterval;
      setPlaybackTime((timeElapsed / totalDurationMs) * 100);

      if (timeElapsed >= totalDurationMs) {
        clearInterval(playbackTimerRef.current);
        handleNextScene();
      }
    }, stepInterval);
  };

  // Playback master toggle
  const togglePlay = () => {
    const nextPlaying = !isPlaying;
    setIsPlaying(nextPlaying);
    if (!nextPlaying) {
      if (audioRef.current) audioRef.current.pause();
      if (window.speechSynthesis) window.speechSynthesis.cancel();
      if (playbackTimerRef.current) clearInterval(playbackTimerRef.current);
      audioSynth.stop();
    }
  };

  useEffect(() => {
    if (isPlaying) {
      playCurrentSceneAssets();
    }
  }, [selectedSceneIndex, isPlaying]);

  const handleNextScene = () => {
    if (selectedSceneIndex < storyboard.scenes.length - 1) {
      setSelectedSceneIndex((prev) => prev + 1);
    } else {
      setIsPlaying(false);
      setPlaybackTime(100);
      if (playbackTimerRef.current) clearInterval(playbackTimerRef.current);
      audioSynth.stop();
    }
  };

  const handlePrevScene = () => {
    if (playbackTimerRef.current) clearInterval(playbackTimerRef.current);
    if (selectedSceneIndex > 0) {
      setSelectedSceneIndex((prev) => prev - 1);
    } else {
      setPlaybackTime(0);
      if (isPlaying) playCurrentSceneAssets();
    }
  };

  const handleSelectSceneDirect = (idx: number) => {
    if (playbackTimerRef.current) clearInterval(playbackTimerRef.current);
    setSelectedSceneIndex(idx);
    setPlaybackTime(0);
  };

  // Edit Panel Actions
  const openEditPanel = (sc: Scene) => {
    setEditingSceneId(sc.id);
    setEditNarratorText(sc.narratorText);
    setEditDialogueText(sc.characterDialogue);
    setEditSpeaker(sc.characterDialogueSpeaker);
    setEditSoundEffect(sc.soundEffect);
    setEditCamera(sc.cameraMovement);
  };

  const saveSceneEdits = () => {
    if (!editingSceneId) return;

    setStoryboard((prev) => {
      const updatedScenes = prev.scenes.map((sc) => {
        if (sc.id === editingSceneId) {
          return {
            ...sc,
            narratorText: editNarratorText,
            characterDialogue: editDialogueText,
            characterDialogueSpeaker: editSpeaker,
            soundEffect: editSoundEffect,
            cameraMovement: editCamera,
            // Flush old generated tracks to trigger clean refresh
            imageUrl: sc.narratorText === editNarratorText ? sc.imageUrl : null,
            speechAudio: sc.narratorText === editNarratorText && sc.characterDialogue === editDialogueText ? sc.speechAudio : null,
          };
        }
        return sc;
      });
      return { ...prev, scenes: updatedScenes };
    });

    setEditingSceneId(null);
  };

  // INDIVIDUAL COMPILATION (SINGLE SCENE)
  const generateSingleSceneAssets = async (sceneId: string) => {
    const targetScene = storyboard.scenes.find((sc) => sc.id === sceneId);
    if (!targetScene) return;

    setAssetsStatus((prev) => ({ ...prev, [sceneId]: 'generating' }));

    try {
      // 1. Generate Voice Narration
      let updatedAudio = targetScene.speechAudio;
      try {
        const ttsRes = await fetch("/api/generate-speech-asset", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            narratorText: targetScene.narratorText,
            dialogue: targetScene.characterDialogue,
            speaker: targetScene.characterDialogueSpeaker,
            voiceName: activeVoice,
          }),
        });
        if (ttsRes.ok) {
          const ttsData = await ttsRes.json();
          updatedAudio = ttsData.speechAudio;
        }
      } catch (err) {
        console.warn("Speech API failed for scene", sceneId, err);
      }

      // 2. Generate Image Illustration or Veo Video Clip
      let updatedImage = targetScene.imageUrl;
      let updatedVideo = targetScene.videoUrl;
      let updatedVideoOp = targetScene.videoOperationName;
      let updatedVideoStatus = targetScene.videoStatus;

      try {
        const imgRes = await fetch("/api/generate-image-asset", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            visualPrompt: targetScene.visualPrompt,
            style: storyboard.scenes[0]?.visualPrompt?.split(".")[0] || "modern graphics",
          }),
        });
        if (imgRes.ok) {
          const imgData = await imgRes.json();
          updatedImage = imgData.imageUrl;
        }
      } catch (err) {
        console.warn("Visual generation failed for scene", sceneId, err);
      }

      // If Veo is turned on, run direct Veo sequence
      if (veoSupportMode && updatedImage) {
        try {
          const veoRes = await fetch("/api/generate-video-asset", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              prompt: targetScene.visualPrompt,
              base64Image: updatedImage,
            }),
          });
          if (veoRes.ok) {
            const veoData = await veoRes.json();
            updatedVideoOp = veoData.operationName;
            updatedVideoStatus = 'pending';
          }
        } catch (err) {
          console.warn("Veo generation block failed:", err);
        }
      }

      // Write changes back to Local Story data block
      setStoryboard((prev) => {
        const scenes = prev.scenes.map((sc) => {
          if (sc.id === sceneId) {
            return {
              ...sc,
              imageUrl: updatedImage,
              speechAudio: updatedAudio,
              videoOperationName: updatedVideoOp,
              videoStatus: updatedVideoStatus,
            };
          }
          return sc;
        });
        return { ...prev, scenes };
      });

      setAssetsStatus((prev) => ({ ...prev, [sceneId]: 'ready' }));
    } catch (e) {
      console.error("Single asset render failed:", e);
      setAssetsStatus((prev) => ({ ...prev, [sceneId]: 'error' }));
    }
  };

  // FULL SEQUENTIAL RENDERING (BATCH BUILD)
  const renderAllAssetsBatch = async () => {
    const scenesToProcess = storyboard.scenes;
    for (const sc of scenesToProcess) {
      await generateSingleSceneAssets(sc.id);
    }
  };

  // Poll Veo video generation operations if pending
  const checkVeoVideoStatus = async (sceneId: string, opName: string) => {
    try {
      const res = await fetch("/api/video-status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operationName: opName }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.done) {
          // Video is compiled! Save with proxy download stream url
          const videoProxyUrl = `/api/video-download?operationName=${encodeURIComponent(opName)}`;
          setStoryboard((prev) => {
            const scenes = prev.scenes.map((sc) => {
              if (sc.id === sceneId) {
                return { ...sc, videoUrl: videoProxyUrl, videoStatus: 'completed' as const };
              }
              return sc;
            });
            return { ...prev, scenes };
          });
        }
      }
    } catch (e) {
      console.warn("Poll failed for scene video status:", e);
    }
  };

  // Helper dictionary mapping camera enum directly to pure Tailwind Ken Burns animation
  const getCameraMotionStyle = (mov: string) => {
    if (!isPlaying) return "scale-105";

    switch (mov) {
      case "pan_left":
        return "scale-115 translate-x-4 animate-slow-pan-left";
      case "pan_right":
        return "scale-115 -translate-x-4 animate-slow-pan-right";
      case "zoom_in":
        return "animate-slow-zoom-in";
      case "zoom_out":
        return "scale-120 animate-slow-zoom-out";
      case "tilt_up":
        return "scale-115 translate-y-4 animate-slow-tilt-up";
      case "tilt_down":
        return "scale-115 -translate-y-4 animate-slow-tilt-down";
      default:
        return "scale-105 duration-1000";
    }
  };

  // Dynamic Aspect ratio container classes
  const getAspectRatioClasses = () => {
    switch (aspectRatio) {
      case "9_16":
        return "aspect-[9/16] max-h-[580px] w-[326px]";
      case "1_1":
        return "aspect-square max-h-[500px] w-[500px]";
      default:
        return "aspect-[16/9] w-full"; // Widescreen
    }
  };

  const downloadScriptTxt = () => {
    const lines = [
      `=== CINEMATIC STORY SCREENPLAY: ${storyboard.title.toUpperCase()} ===`,
      `Genre: ${storyboard.genre}`,
      `Summary: ${storyboard.summary}`,
      `Soundtrack Direction: ${storyboard.soundtrackStyle}`,
      "",
      ...storyboard.scenes.map((sc, idx) => {
        return `[SCENE ${idx + 1}] ${sc.title.toUpperCase()}
Camera Direction: ${sc.cameraMovement.toUpperCase()}
On-Screen SFX: *${sc.soundEffect}*
Narrator Track: "${sc.narratorText}"
${sc.characterDialogueSpeaker}: "${sc.characterDialogue}"
------------------------------------------------------`;
      })
    ].join("\n");

    const blob = new Blob([lines], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${storyboard.title.toLowerCase().replace(/\s+/g, '_')}_screenplay.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 text-neutral-100 animate-fade-in">
      
      {/* LEFT COLUMN: Main Video Player Stage & Controls */}
      <div className="xl:col-span-8 space-y-6">
        
        {/* Main Cinema Screen Container */}
        <div className="bg-[#0F0F11] border border-white/5 rounded-xl shadow-3xl overflow-hidden relative flex flex-col items-center">
          
          {/* Aesthetic Cinema Bar */}
          <div className="w-full bg-[#0C0C0E] border-b border-white/5 px-4 py-3 flex items-center justify-between z-10">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-red-650 rounded-full animate-pulse"></span>
              <span className="text-[10px] font-mono tracking-wider text-[#A1824A] uppercase font-bold">
                TOONPLAY REC: SCENE {selectedSceneIndex + 1}/{storyboard.scenes.length}
              </span>
            </div>
            <h3 className="text-xs font-semibold text-neutral-400 truncate max-w-xs sm:max-w-md">
              {storyboard.title} — {activeScene.title}
            </h3>
            <div className="flex gap-1.5 bg-black/45 p-1 rounded border border-white/10">
              <button
                onClick={() => setAspectRatio("16_9")}
                className={`p-1 rounded text-xs transition-colors ${aspectRatio === "16_9" ? "bg-[#A1824A]/10 text-[#A1824A]" : "text-neutral-500"}`}
                title="Widescreen (16:9)"
              >
                <Monitor className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setAspectRatio("9_16")}
                className={`p-1 rounded text-xs transition-colors ${aspectRatio === "9_16" ? "bg-[#A1824A]/10 text-[#A1824A]" : "text-neutral-500"}`}
                title="Reels/TikTok (9:16)"
              >
                <Smartphone className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setAspectRatio("1_1")}
                className={`p-1 rounded text-xs transition-colors ${aspectRatio === "1_1" ? "bg-[#A1824A]/10 text-[#A1824A]" : "text-neutral-500"}`}
                title="Grid (1:1)"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Active Cinema Stage */}
          <div className="relative w-full flex items-center justify-center bg-black overflow-hidden py-1">
            <div 
              id="cinematic-canvas-stage"
              className={`relative overflow-hidden transition-all duration-500 ${getAspectRatioClasses()}`}
            >
              
              {/* Media Renderer (Image or Video) */}
              {viewMode === "ai_widescreen" ? (
                // AI Rendered Slide
                activeScene.videoUrl ? (
                  <video
                    src={activeScene.videoUrl}
                    autoPlay
                    loop
                    muted={isMuted}
                    className="w-full h-full object-cover"
                  />
                ) : activeScene.imageUrl ? (
                  <img
                    src={activeScene.imageUrl}
                    alt={activeScene.title}
                    referrerPolicy="no-referrer"
                    className={`w-full h-full object-cover transform transition-transform duration-[10000ms] ease-out ${getCameraMotionStyle(
                      activeScene.cameraMovement
                    )}`}
                  />
                ) : (
                  // Elegant Fallback Comic Matte if visual assets haven't been compiled
                  <div className="w-full h-full bg-gradient-to-br from-neutral-950 to-[#A1824A]/5 flex flex-col items-center justify-center p-6 text-center space-y-4">
                    <div className="w-16 h-16 rounded-full bg-black/55 border border-[#A1824A]/20 flex items-center justify-center animate-pulse">
                      <Sparkles className="w-8 h-8 text-[#A1824A]" />
                    </div>
                    <div>
                      <h4 className="font-serif italic text-lg text-white">Generative Canvas Locked</h4>
                      <p className="text-xs text-neutral-400 mt-1 max-w-sm">
                        Please generate AI slide materials in the sidebar panel to see your custom adaptation.
                      </p>
                    </div>
                  </div>
                )
              ) : (
                // Original Comic Upload slide reference
                originalImages.length > 0 ? (
                  <img
                    src={originalImages[selectedSceneIndex % originalImages.length]}
                    alt="Original Upload reference"
                    referrerPolicy="no-referrer"
                    className={`w-full h-full object-cover transform transition-transform duration-[10000ms] ease-out ${getCameraMotionStyle(
                      activeScene.cameraMovement
                    )}`}
                  />
                ) : (
                  <div className="w-full h-full bg-neutral-900 flex flex-col items-center justify-center p-6 text-center">
                    <Wand2 className="w-12 h-12 text-neutral-600 mb-2" />
                    <p className="text-sm font-semibold text-neutral-300">No original images uploaded</p>
                    <p className="text-xs text-neutral-500 mt-1">Upload multiple images in Phase 1 to unlock original slides.</p>
                  </div>
                )
              )}

              {/* FLOATING DIALOGUE SPEECH BUBBLE OVERLAY */}
              {isPlaying && activeScene.characterDialogue && (
                <div 
                  id="dialogue-speech-bubble"
                  className="absolute top-8 left-6 right-6 flex justify-start z-20 pointer-events-none animate-bubble-bounce"
                >
                  <div className="bg-white text-neutral-950 px-4 py-2.5 rounded-2xl shadow-xl border-3 border-neutral-950 relative max-w-[85%]">
                    <span className="text-[10px] font-mono tracking-widest font-extrabold text-[#A1824A] block uppercase mb-0.5">
                      {activeScene.characterDialogueSpeaker}
                    </span>
                    <p className="text-xs sm:text-sm font-bold font-sans italic tracking-tight leading-snug">
                      "{activeScene.characterDialogue}"
                    </p>
                    {/* Retro Comic Speech Tail */}
                    <div className="absolute -bottom-2.5 left-6 w-3.5 h-3 bg-white border-b-3 border-r-3 border-neutral-950 transform rotate-45"></div>
                  </div>
                </div>
              )}

              {/* FLOATING ACTION SOUND COMMENT OVERLAY (e.g. WHACK, SMASH) */}
              {isPlaying && activeScene.soundEffect && (
                <div 
                  id="sound-effect-overlay"
                  className="absolute bottom-16 right-8 z-20 pointer-events-none transform rotate-[11deg] scale-110 animate-shake"
                >
                  <span className="px-4 py-1.5 bg-yellow-400 text-neutral-950 font-black text-xl border-4 border-solid border-neutral-950 tracking-tighter uppercase rounded shadow-[4px_4px_0px_#000] inline-block font-mono">
                    {activeScene.soundEffect}!
                  </span>
                </div>
              )}

              {/* Subtitles Overlay */}
              <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/85 via-black/50 to-transparent p-4 pt-10 text-center z-1 z-10">
                <p className="text-xs sm:text-sm text-neutral-200 outline-black max-w-2xl mx-auto leading-relaxed">
                  {activeScene.narratorText}
                </p>
              </div>

            </div>
          </div>

          {/* Player controls Panel */}
          <div className="w-full bg-[#0C0C0E] border-t border-white/5 p-4 space-y-4 z-10 font-sans">
            
            {/* Timeline Progress Slider */}
            <div className="flex items-center gap-3">
              <span className="text-[10px] font-mono text-neutral-400">00:00</span>
              <div className="w-full bg-[#0A0A0B] rounded h-1 overflow-hidden border border-white/5 relative">
                <div
                  className="bg-[#A1824A] h-full transition-all duration-300"
                  style={{ width: `${playbackTime}%` }}
                ></div>
              </div>
              <span className="text-[10px] font-mono text-neutral-400">
                00:{activeScene.duration.toString().padStart(2, "0")}
              </span>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              
              {/* Playback Buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={handlePrevScene}
                  className="p-2 rounded bg-[#0A0A0B] border border-white/5 hover:border-[#A1824A]/40 hover:text-[#A1824A] transition-colors"
                  title="Previous Scene"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>

                <button
                  onClick={togglePlay}
                  className="p-3 rounded bg-[#A1824A] hover:brightness-110 text-black transition-all transform hover:scale-105 active:scale-95"
                  title={isPlaying ? "Pause Video Playback" : "Play Cinematic Video"}
                >
                  {isPlaying ? <Pause className="w-4 h-4 fill-black" /> : <Play className="w-4 h-4 fill-black ml-0.5" />}
                </button>

                <button
                  onClick={handleNextScene}
                  className="p-2 rounded bg-[#0A0A0B] border border-white/5 hover:border-[#A1824A]/40 hover:text-[#A1824A] transition-colors"
                  title="Next Scene"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>

                <button
                  onClick={() => {
                    setIsPlaying(false);
                    setPlaybackTime(0);
                    setSelectedSceneIndex(0);
                    if (audioRef.current) audioRef.current.pause();
                    if (window.speechSynthesis) window.speechSynthesis.cancel();
                  }}
                  className="p-2 rounded bg-[#0A0A0B] border border-white/5 hover:border-[#A1824A]/45 hover:text-red-400 transition-colors ml-2"
                  title="Reset Soundtrack"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              </div>

              {/* View/Slide Toggles */}
              <div className="flex items-center gap-3 bg-[#0A0A0B] p-1 rounded border border-white/5">
                <button
                  onClick={() => setViewMode("ai_widescreen")}
                  className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition-all ${
                    viewMode === "ai_widescreen"
                      ? "bg-[#A1824A]/10 text-[#A1824A] border border-[#A1824A]/20"
                      : "text-neutral-500 hover:text-neutral-300"
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  AI Re-imagining
                </button>
                <button
                  onClick={() => setViewMode("original")}
                  className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition-all ${
                    viewMode === "original"
                      ? "bg-[#A1824A]/10 text-[#A1824A] border border-[#A1824A]/20"
                      : "text-neutral-500 hover:text-neutral-300"
                  }`}
                >
                  <Wand2 className="w-3.5 h-3.5" />
                  Original Panel
                </button>
              </div>

              {/* Mute buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSynthSoundtrackEnabled(!synthSoundtrackEnabled)}
                  className={`p-2 rounded border transition-all ${
                    synthSoundtrackEnabled
                      ? "bg-[#A1824A]/10 border-[#A1824A]/30 text-[#A1824A]"
                      : "bg-[#0A0A0B] border-white/5 text-neutral-500 hover:text-neutral-400"
                  }`}
                  title="Toggle Procedural Soundtrack Synth"
                >
                  <Music className="w-4 h-4" />
                </button>

                <button
                  onClick={() => setIsMuted(!isMuted)}
                  className="p-2 rounded bg-[#0A0A0B] border border-white/5 hover:border-[#A1824A]/40 hover:text-neutral-300 transition-colors"
                  title={isMuted ? "Unmute sound" : "Mute soundtrack"}
                >
                  {isMuted ? <VolumeX className="w-4 h-4 text-red-400" /> : <Volume2 className="w-4 h-4" />}
                </button>
              </div>

            </div>

          </div>

        </div>

        {/* Detailed Screenplay Narrative Layout (Scene-by-scene card inspector) */}
        <div className="bg-[#0C0C0E] border border-white/5 rounded-xl p-6 space-y-5">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <div>
              <h3 className="text-lg font-serif italic text-white flex items-center gap-2">
                <Edit className="w-4 h-4 text-[#A1824A]" />
                Screenplay Dialogues & Script
              </h3>
              <p className="text-xs text-neutral-450 mt-0.5">Edit adapted text lines directly to reshape your cinematic video.</p>
            </div>
            <button
              onClick={downloadScriptTxt}
              className="px-3 py-1.5 bg-white/5 border border-white/10 hover:bg-white/10 text-xs rounded flex items-center gap-1.5 font-medium text-[#A1824A] cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              Download Script (TXT)
            </button>
          </div>

          <div className="space-y-3">
            {storyboard.scenes.map((sc, scIdx) => (
              <div 
                key={sc.id}
                className={`p-4 rounded border transition-colors ${
                  selectedSceneIndex === scIdx 
                    ? "bg-black border-[#A1824A]/40 shadow-md" 
                    : "bg-black/40 border-white/5 hover:bg-black/60"
                }`}
              >
                {editingSceneId === sc.id ? (
                  // Editing Panel inside lists
                  <div className="space-y-3 text-xs">
                    <div className="flex items-center justify-between border-b border-white/5 pb-2">
                      <span className="font-mono text-[#A1824A] uppercase tracking-wider">EDITING SCENE #{scIdx + 1}</span>
                      <div className="flex gap-2">
                        <button
                          onClick={saveSceneEdits}
                          className="px-2 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-sm flex items-center gap-1"
                        >
                          <Check className="w-3 h-3" /> Save Changes
                        </button>
                        <button
                          onClick={() => setEditingSceneId(null)}
                          className="px-2 py-1 bg-white/5 border border-white/10 text-neutral-400 rounded-sm hover:text-white"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-[10px] uppercase font-mono text-neutral-500">Narrator Action Script</label>
                        <textarea
                          value={editNarratorText}
                          onChange={(e) => setEditNarratorText(e.target.value)}
                          rows={3}
                          className="w-full bg-[#0A0A0B] border border-white/10 rounded p-2 text-neutral-200 focus:outline-none focus:border-[#A1824A]"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] uppercase font-mono text-neutral-500">Character Spoken Dialogue</label>
                        <textarea
                          value={editDialogueText}
                          onChange={(e) => setEditDialogueText(e.target.value)}
                          rows={3}
                          className="w-full bg-[#0A0A0B] border border-white/10 rounded p-2 text-neutral-200 focus:outline-none focus:border-[#A1824A]"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="text-[10px] uppercase font-mono text-neutral-500 block mb-1">Speaker Role</label>
                        <input
                          type="text"
                          value={editSpeaker}
                          onChange={(e) => setEditSpeaker(e.target.value)}
                          className="w-full bg-[#0A0A0B] border border-white/10 rounded px-2.5 py-1.5 text-neutral-200 focus:outline-none focus:border-[#A1824A]"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] uppercase font-mono text-neutral-500 block mb-1">Comic SFX Highlight</label>
                        <input
                          type="text"
                          value={editSoundEffect}
                          onChange={(e) => setEditSoundEffect(e.target.value)}
                          className="w-full bg-[#0A0A0B] border border-white/10 rounded px-2.5 py-1.5 text-neutral-200 focus:outline-none focus:border-[#A1824A]"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] uppercase font-mono text-neutral-500 block mb-1">Camera Traversal</label>
                        <select
                          value={editCamera}
                          onChange={(e) => setEditCamera(e.target.value as any)}
                          className="w-full bg-[#0A0A0B] border border-white/10 rounded px-2 py-1.5 text-neutral-200 focus:outline-none focus:border-[#A1824A]"
                        >
                          <option value="pan_left">Pan Left</option>
                          <option value="pan_right">Pan Right</option>
                          <option value="zoom_in">Zoom In</option>
                          <option value="zoom_out">Zoom Out</option>
                          <option value="tilt_up">Tilt Up</option>
                          <option value="tilt_down">Tilt Down</option>
                          <option value="static">Static Stable</option>
                        </select>
                      </div>
                    </div>
                  </div>
                ) : (
                  // Closed Inspection item
                  <div className="flex items-start justify-between gap-3 text-xs sm:text-sm">
                    <div className="space-y-1 cursor-pointer w-full" onClick={() => handleSelectSceneDirect(scIdx)}>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-[#A1824A]">#SCENE 0{scIdx + 1}:</span>
                        <h4 className="font-semibold text-neutral-200">{sc.title}</h4>
                        <span className="text-[9px] font-mono px-1.5 py-0.5 bg-white/5 text-neutral-400 border border-white/10 rounded uppercase">
                          {sc.cameraMovement.replace("_", " ")}
                        </span>
                      </div>
                      <p className="text-neutral-300 text-xs line-clamp-1">{sc.narratorText}</p>
                      {sc.characterDialogue && (
                        <p className="text-[11px] text-neutral-550 truncate">
                          <strong className="text-neutral-400">{sc.characterDialogueSpeaker}</strong>: "{sc.characterDialogue}"
                        </p>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2 text-xs">
                      {assetsStatus[sc.id] === "ready" && (
                        <span className="text-[10px] text-emerald-400 font-mono">Ready</span>
                      )}
                      <button
                        onClick={() => openEditPanel(sc)}
                        className="p-1.5 rounded bg-white/5 border border-white/10 hover:border-[#A1824A]/40 text-neutral-455 transition-colors"
                        title="Edit script parameters"
                      >
                        <Edit className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* RIGHT COLUMN: Scene Timeline & Materials Generation controls */}
      <div className="xl:col-span-4 space-y-6">
        
        {/* Step 2 Materials Generator Terminal */}
        <div className="bg-[#0C0C0E] border border-white/5 rounded-xl p-6 space-y-5">
          <div>
            <span className="text-[10px] font-mono px-2.5 py-0.5 bg-[#A1824A]/10 text-[#A1824A] rounded-full border border-[#A1824A]/21 tracking-wider">
              STEP 02: MATERIAL COMPILER
            </span>
            <h3 className="text-lg font-serif italic text-white mt-2 flex items-center gap-2">
              <Sparkles className="w-4.5 h-4.5 text-[#A1824A]" />
              Generate AI Comic Media Panels
            </h3>
            <p className="text-xs text-neutral-405 mt-1">
              Assemble visual storyboard graphic slides and high-fidelity narrator voices through Google GenAI.
            </p>
          </div>

          {/* Configuration controls */}
          <div className="bg-[#0F0F11] p-4 rounded border border-white/5 space-y-4 text-xs">
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-mono text-neutral-405">Select Narrator Voice Preference</label>
              <div className="grid grid-cols-2 gap-1.5">
                {[
                  { id: "Kore", label: "Kore (Cheerful)" },
                  { id: "Puck", label: "Puck (Energetic)" },
                  { id: "Fenrir", label: "Fenrir (Dramatic)" },
                  { id: "Zephyr", label: "Zephyr (Classic)" }
                ].map((voice) => (
                  <button
                    key={voice.id}
                    onClick={() => setActiveVoice(voice.id)}
                    className={`p-2 rounded text-left transition-colors font-medium border ${
                      activeVoice === voice.id
                        ? "bg-[#A1824A]/10 border-[#A1824A]/30 text-[#A1824A]"
                        : "bg-white/5 border border-white/10 text-neutral-400 hover:text-white"
                    }`}
                  >
                    {voice.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Veo Video Toggle */}
            <div className="pt-2 border-t border-white/5 flex items-center justify-between">
              <div className="space-y-0.5 pr-2">
                <span className="font-semibold text-neutral-200 flex items-center gap-1">
                  <Film className="w-3.5 h-3.5 text-[#A1824A]" /> Use Veo Video Clips
                </span>
                <p className="text-[10px] text-neutral-500">Compiles fully motioned videos instead of panning slides.</p>
              </div>
              <button
                onClick={() => setVeoSupportMode(!veoSupportMode)}
                className={`w-10 h-6 rounded-full p-1 transition-colors ${
                  veoSupportMode ? "bg-[#A1824A]" : "bg-white/10"
                }`}
              >
                <div
                  className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${
                    veoSupportMode ? "translate-x-4" : "translate-x-0"
                  }`}
                ></div>
              </button>
            </div>
          </div>

          {/* Run Block Buttons */}
          <div className="space-y-2">
            <button
              id="btn-render-materials-batch"
              onClick={renderAllAssetsBatch}
              className="w-full py-3 bg-[#A1824A] hover:brightness-110 active:scale-[0.98] text-black font-bold rounded uppercase tracking-widest flex items-center justify-center gap-2 text-xs transition-all shadow-md shadow-[#A1824A]/5 cursor-pointer"
            >
              <Wand2 className="w-4 h-4" />
              Batch Compile All Scenes
            </button>
            <p className="text-[10px] text-neutral-500 text-center">
              Processes widescreen illustration generation and TTS vocal conversions. Usually takes 10-25 seconds per scene.
            </p>
          </div>

          {/* Rendering status item timelines */}
          <div className="space-y-3 pt-2">
            <span className="text-[11px] font-mono uppercase text-neutral-400 block tracking-wider">
              Scenes Render Status ({storyboard.scenes.length})
            </span>
            <div className="space-y-2 overflow-y-auto max-h-[300px]">
              {storyboard.scenes.map((sc, idx) => {
                const stat = assetsStatus[sc.id] || 'idle';
                return (
                  <div 
                    key={sc.id}
                    className="flex items-center justify-between bg-black/40 border border-white/5 px-3 py-2.5 rounded text-xs font-sans"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span className="font-mono text-[11px] text-[#A1824A]">#{idx + 1}</span>
                      <span className="truncate text-neutral-200">{sc.title}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      {stat === 'generating' ? (
                        <div className="flex items-center gap-1.5 text-[#A1824A]">
                          <span className="w-1.5 h-1.5 bg-[#A1824A] rounded-full animate-ping"></span>
                          <span className="font-mono text-[10px]">Compiling...</span>
                        </div>
                      ) : stat === 'ready' ? (
                        <div className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
                          <span className="text-emerald-400 font-mono text-[10px]">Rendered</span>
                        </div>
                      ) : stat === 'error' ? (
                        <span className="text-red-400 font-mono text-[10px]">Retry</span>
                      ) : (
                        <span className="text-neutral-500 font-mono text-[10px]">Idle</span>
                      )}

                      <button
                        disabled={stat === 'generating'}
                        onClick={() => generateSingleSceneAssets(sc.id)}
                        className="px-2.5 py-1 bg-white/5 border border-white/10 rounded hover:border-[#A1824A]/40 text-[10px] text-neutral-300 font-medium"
                      >
                        {sc.imageUrl ? "Redraw" : "Draw"}
                      </button>

                      {sc.videoOperationName && sc.videoStatus === 'pending' && (
                        <button
                          onClick={() => checkVeoVideoStatus(sc.id, sc.videoOperationName!)}
                          className="px-1.5 py-1 bg-[#A1824A]/10 text-[#A1824A] border border-[#A1824A]/20 text-[9px] rounded uppercase font-mono font-bold"
                        >
                          Check Video
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

        </div>

        {/* Story Metadata panel */}
        <div className="bg-[#0C0C0E] border border-white/5 rounded-xl p-6 space-y-4">
          <h4 className="text-sm font-serif italic text-white block">Comic Synthesis Report</h4>
          <div className="space-y-2 text-xs text-neutral-405">
            <div className="flex justify-between border-b border-white/5 pb-1.5">
              <span>Primary Genre</span>
              <strong className="text-neutral-200">{storyboard.genre}</strong>
            </div>
            <div className={`flex justify-between ${originalImages.length > 0 ? "border-b border-white/5" : ""} pb-1.5`}>
              <span>Soundtrack Style</span>
              <strong className="text-[#A1824A] font-mono">{storyboard.soundtrackStyle}</strong>
            </div>
            {originalImages.length > 0 && (
              <div className="flex justify-between pb-1.5">
                <span>Original Pages Cached</span>
                <strong className="text-neutral-200">{originalImages.length} Image files</strong>
              </div>
            )}
            <div className="pt-2">
              <span className="block text-[10px] text-neutral-500 uppercase tracking-widest font-mono mb-1">plot adaptation outline</span>
              <p className="font-light text-neutral-300 leading-relaxed text-[11px] line-clamp-4">
                {storyboard.summary}
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-white/5">
            <button
              onClick={onBackToUpload}
              className="w-full py-2.5 bg-white/5 border border-white/10 hover:bg-white/10 text-xs font-semibold rounded flex items-center justify-center gap-1.5 text-neutral-300 transition-colors cursor-pointer uppercase tracking-wider"
            >
              Upload Another Comic Book
            </button>
          </div>
        </div>

      </div>

    </div>
  );
}
