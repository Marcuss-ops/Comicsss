import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI, Type } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = 3000;

// Increase payload limit for uploading PDFs and base64 images
app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ limit: "50mb", extended: true }));

// Lazy initializer for Google GenAI client
let genAIClient: any = null;
function getGenAIClient(): any {
  if (!genAIClient) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      throw new Error("GEMINI_API_KEY is not defined in environments. Please configure it in your Secrets panel.");
    }
    genAIClient = new GoogleGenAI({
      apiKey,
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build",
        },
      },
    });
  }
  return genAIClient;
}

// Robust recursive helpers to cleanse accented character corruption, suppress forward/backward slashes, and strip escaping issues
function sanitizeStringForUser(text: string): string {
  if (!text) return text;
  
  // 1. Remove forward slashes (/) as requested by user ("rimuovi i vari / non servono a niente")
  // Using a single space to avoid stitching words like "Batman/Joker" into "BatmanJoker"
  let cleaned = text.replace(/\//g, " ");

  // 2. Rectify Latin-1 percent encoded hex character fragments (e.g. %f9, %e0, %e8, %ec, %f2, %e9 used for accents)
  cleaned = cleaned.replace(/%f9/gi, "ù");
  cleaned = cleaned.replace(/%e0/gi, "à");
  cleaned = cleaned.replace(/%e8/gi, "è");
  cleaned = cleaned.replace(/%ec/gi, "ì");
  cleaned = cleaned.replace(/%f2/gi, "ò");
  cleaned = cleaned.replace(/%e9/gi, "é");

  // 3. Rectify known '$' and common character encoding issues in Italian
  cleaned = cleaned.replace(/pi\$/g, "più");
  cleaned = cleaned.replace(/perch\$/g, "perché");
  cleaned = cleaned.replace(/perchè/g, "perché");
  cleaned = cleaned.replace(/perche'/g, "perché");
  cleaned = cleaned.replace(/cos\$/g, "così");
  cleaned = cleaned.replace(/gi\$/g, "giù");
  cleaned = cleaned.replace(/pu\$/g, "può");
  cleaned = cleaned.replace(/foll\$/g, "follia");
  cleaned = cleaned.replace(/c'\$/g, "c'è");
  cleaned = cleaned.replace(/sar\$/g, "sarà");
  cleaned = cleaned.replace(/andr\$/g, "andrà");
  cleaned = cleaned.replace(/com\$/g, "com'è");
  cleaned = cleaned.replace(/ l\$/g, " là");
  cleaned = cleaned.replace(/ propriet\$/g, " proprietà");
  cleaned = cleaned.replace(/ felicit\$/g, " felicità");
  cleaned = cleaned.replace(/ capacit\$/g, " capacità");
  cleaned = cleaned.replace(/ dignit\$/g, " dignità");
  cleaned = cleaned.replace(/ pover\$/g, " povertà");
  cleaned = cleaned.replace(/ impaziente\$/g, " impaziente");

  // Vowel fallback replacements if '$' follows a vowel
  cleaned = cleaned.replace(/u\$/g, "ù");
  cleaned = cleaned.replace(/a\$/g, "à");
  cleaned = cleaned.replace(/e\$/g, "è");
  cleaned = cleaned.replace(/o\$/g, "ò");
  cleaned = cleaned.replace(/i\$/g, "ì");

  // General spelling sanitizations
  cleaned = cleaned.replace(/\bpiu\b/g, "più");
  cleaned = cleaned.replace(/\bgia\b/g, "già");
  cleaned = cleaned.replace(/\bperche\b/g, "perché");
  cleaned = cleaned.replace(/\bpò\b/g, "po'");
  cleaned = cleaned.replace(/\bpo\b/g, "po'");
  cleaned = cleaned.replace(/\bsò\b/g, "so"); 

  // 4. Purge backslashes (\) completely as requested to keep the voiceover raw, natural text
  cleaned = cleaned.replace(/\\"/g, '"');
  cleaned = cleaned.replace(/\\'/g, "'");
  cleaned = cleaned.replace(/\\/g, "");

  // 5. Clean extra spaces
  cleaned = cleaned.replace(/\s+/g, " ");
  
  return cleaned.trim();
}

function sanitizeObject(obj: any): any {
  if (obj === null || obj === undefined) return obj;
  if (typeof obj === "string") {
    return sanitizeStringForUser(obj);
  }
  if (Array.isArray(obj)) {
    return obj.map(sanitizeObject);
  }
  if (typeof obj === "object") {
    const cleanedObj: any = {};
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        cleanedObj[key] = sanitizeObject(obj[key]);
      }
    }
    return cleanedObj;
  }
  return obj;
}

// ----------------------------------------------------
// API ROUTES
// ----------------------------------------------------

// 1. Parse uploaded PDF or comic images into a structured Cinematic Storyboard
app.post("/api/read-comic", async (req, res) => {
  try {
    const { files, customGenre, customStyle } = req.body;
    if (!files || !Array.isArray(files) || files.length === 0) {
      res.status(400).json({ error: "No comic files uploaded." });
      return;
    }

    const ai = getGenAIClient();

    // Prepare contents parts for Gemini
    const contents: any[] = [];
    
    // Convert base64 files array to Gemini-compatible inlineData objects
    files.forEach((file: { data: string; mimeType: string }) => {
      // Strip out the data:image/png;base64, prefixes if present
      let rawBase64 = file.data;
      if (rawBase64.includes(";base64,")) {
        rawBase64 = rawBase64.split(";base64,")[1];
      }
      contents.push({
        inlineData: {
          data: rawBase64,
          mimeType: file.mimeType,
        },
      });
    });

    // Provide detailed custom screenplay/comic prompt
    const instructions = `You are a professional comic-book director and cinematic screenplay adapter.
Dissect the uploaded pdf or images page-by-page. Analyze the characters, storyline, dramatic text, visual frames, tone, and pacing.
Create a cinematic storyboard which splits the story into consecutive scenes (minimum 4, maximum 10 scenes total).
Each scene represents a dramatic panel or key event. Ensure that the flow is cohesive and forms a satisfying interactive narrative.

For each scene:
- Craft 'narratorText' that sets the dramatic scene, tells what happens, or reads page summaries. Keep it expressive but short enough to be narrated elegantly (20-40 words).
- Extract or write the single most impactful character dialogue in this scene ('characterDialogue'), alongside the speaker's name ('characterDialogueSpeaker'). Keep it dramatic!
- Provide a dramatic comic sound effect ('soundEffect') representing the sensory feedback in that specific state (e.g. WHOOSH, SPLAT, CRASH, THWIP, BOOM, VRROOM).
- Write a 'visualPrompt' that generates widescreen professional illustration of this scene matching the comic's theme (e.g., "Classic retro 1980s superhero comic style showing...", "Manga black and white sketch of...", "Cinematic digital oil painting of..."). Style: ${customStyle || "Classic Graphic Comic Style"}.
- Decide on a dramatic cinematic camera movement ('cameraMovement') to make the static layout feel animated.
- Assign an estimated duration in seconds appropriate for reading the narrative smoothly (usually between 5 and 10 seconds).

Use the requested JSON schema options strictly. Make the story exciting! User's context: Genre: ${customGenre || "Matched automatically"}.`;

    contents.push({ text: instructions });

    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents,
      config: {
        systemInstruction: "You are a master storyteller translating PDFs and comic art into cinematic narrations.",
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            title: { type: Type.STRING, description: "Unifying title for this cinematic adaptation." },
            genre: { type: Type.STRING, description: "Identified story genre." },
            summary: { type: Type.STRING, description: "A high-impact executive summary of the entire comic plot." },
            soundtrackStyle: { type: Type.STRING, description: "Tone of ambient background music, e.g. Neon Cyberpunk Synth, Retro Superhero brass, Whimsical Pixels." },
            scenes: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  id: { type: Type.STRING, description: "Unique scene id e.g. scene_1" },
                  title: { type: Type.STRING, description: "Short scene title" },
                  narratorText: { type: Type.STRING, description: "Expressive story description read by an audio narrator." },
                  characterDialogue: { type: Type.STRING, description: "Direct spoken dialogue or quote. Keep concise." },
                  characterDialogueSpeaker: { type: Type.STRING, description: "Which character is saying it (e.g., 'Spider-Man', 'Narrator', 'The Villain')." },
                  soundEffect: { type: Type.STRING, description: "Action sound effect word displayed in comic bubbles." },
                  visualPrompt: { type: Type.STRING, description: "Widescreen art generation instruction." },
                  cameraMovement: {
                    type: Type.STRING,
                    description: "Motion preset to animate the scene canvas.",
                    enum: ["pan_left", "pan_right", "zoom_in", "zoom_out", "tilt_up", "tilt_down", "static"]
                  },
                  duration: { type: Type.INTEGER, description: "Narrative frame duration in seconds." },
                  sourcePageNumber: { type: Type.INTEGER, description: "Source comic page index (approximate)." }
                },
                required: [
                  "id",
                  "title",
                  "narratorText",
                  "characterDialogue",
                  "characterDialogueSpeaker",
                  "soundEffect",
                  "visualPrompt",
                  "cameraMovement",
                  "duration"
                ]
              }
            }
          },
          required: ["title", "genre", "summary", "soundtrackStyle", "scenes"]
        }
      }
    });

    const parsedData = JSON.parse(response.text || "{}");
    const sanitizedData = sanitizeObject(parsedData);
    res.json(sanitizedData);
  } catch (err: any) {
    console.error("Error reading comic / pdf:", err);
    res.status(500).json({ error: err.message || "Failed to process the comic adapter pipeline." });
  }
});

// 1.5. Pure Comic Panel & Speech Text Extractor (Simplified extraction workflow)
app.post("/api/extract-panels", async (req, res) => {
  try {
    const { files } = req.body;
    if (!files || !Array.isArray(files) || files.length === 0) {
      res.status(400).json({ error: "No comic files uploaded for panel extraction." });
      return;
    }

    const ai = getGenAIClient();

    // Prepare contents parts for Gemini
    const contents: any[] = [];
    
    // Convert base64 files array to Gemini-compatible inlineData objects
    files.forEach((file: { data: string; mimeType: string }) => {
      // Strip out the data:image/png;base64, prefixes if present
      let rawBase64 = file.data;
      if (rawBase64.includes(";base64,")) {
        rawBase64 = rawBase64.split(";base64,")[1];
      }
      contents.push({
        inlineData: {
          data: rawBase64,
          mimeType: file.mimeType,
        },
      });
    });

    const instructions = `You are a professional comic book transcription engine and creative storyteller. Your goal is to parse comic panels and provide high-quality localized output for video narration.

Follow these strict rules:
1. DETECT THE DOMINANT LANGUAGE of the comic book (e.g., Italian, English, French).
2. WRITE THE ENTIRE RESPONSE (including 'title', 'summary', and especially 'youtubeDescription') EXCLUSIVELY in that dominant language. Do not mix languages (e.g., do not write descriptions in English if the comic text/dialogue is in Italian; keep it 100% unified).
3. ELIMINATE TECH JARGON from 'youtubeDescription'. Do NOT write technical layout cues like "Page 1 Top Left Panel", "This panel portrays", "In this square card", "Middle panel contains...". Keep the visual descriptions natural and immersive.
4. FOR 'youtubeDescription' (FUSED WITH DESCRIPTION): This must be an extremely detailed, rich, immersive, and very long VOICE-OVER SCRIPT AND AUDIOBOOK NARRATOR STORYLINE in the dominant language. It MUST be significantly longer than before (at least 350-500 words per panel) to make sure the final video feels like a rich, fully-fledged theatrical narration. In this narration, you MUST describe the setting, actions, landscape, and scenery, AND you MUST transcribe and integrate all active dialogues, characters' speech bubble text, and quotes directly inside this text flow (e.g., "... e Batman risponde sconsolato: 'Non voglio ammazzarti...'"). Quotes must be fully complete and written exactly as they appear on page text.
5. NO FORWARD SLASH SYMBOLS (/) ALLOWED (Critical): Absolutely do not use forward slash symbols (/) anywhere in the generated output values (such as 'title', 'summary', or 'youtubeDescription'). Instead of writing "Batman/Joker" or "scrittore/narratore", use standard, natural words like "Batman e il Joker" or "scrittore o narratore". Slash symbols interrupt narration and sound clumsy when read.
6. INCLUDE DEEP PSYCHOLOGICAL AND THEMATIC REFLECTIONS: Extend each panel's description with an insightful, friendly reflection explaining what is happening underneath the surface (the characters' deeper psychology, the tragic underlying dynamic, their inner suffering, or the subtext of the scene) particularly when the raw actions or environment aren't immediately obvious. Explain why a scene is so important or emotional, like a passionate YouTube video explainer talking to their fans.
7. USE SIMPLE, FRIENDLY AND COMPREHENSIBLE WORDS: Use simple, easily understandable, and friendly words (absolutely avoid difficult, rare, or overly complex literary terms). Explain the scene from a reader's passionate perspective, like a popular YouTube movie explainer channel. Dive deep into the characters' feelings, what they represent, their inner pain, and their psychology in this exact moment, highlighting the tragic dynamic between them. Each panel's voice-over must flow smoothly as a continuation of the previous one to create a cohesive movie-like narration. Do NOT summarize the layout; tell the story of the panel with deep atmosphere, emotional resonance, and dramatic punch.
8. BE EXTREMELY COMPREHENSIVE AND DO NOT SKIP STORY PAGES: Do not skip important pages or jump massive sections of the book. Ensure a tight, dense, step-by-step chronological transcription of all key narrative pages, mapping the story continuously page-by-page. Produce at least 15 to 25 detailed records showing key development pages without big chronological gaps.
9. EXCLUDE/SKIP ONLY PURELY EMPTY OR NON-STORYLINE BACKGROUNDS: Do not include panels in the output that have absolutely no storytelling value (like a blank background with no dialogue, no narrative captions, and no characters). But keep all panels that advance the narrative or show character-driven actions or speech bubbles, even if they have an atmospheric backdrop.
10. PREVENT CHARACTER CORRUPTION / REJECT BROKEN ENCODING (Critical): Absolutely ensure that all special/accented letters (for example, à, è, é, ì, ò, ù in Italian) are written as standard, clean, unescaped UTF-8 text. DO NOT replace accents with characters like '$' (e.g. NEVER write 'pi$', write 'più'), or '\"' or '\n' or other non-standard escaping symbols. Keep everything perfectly readable, clean, and in standard, pure, beautiful UTF-8.

Generate a comprehensive extraction report matching the required JSON schema structure strictly.
Do not omit any key texts. Keep transcripts highly accurate to read page by page.`;

    contents.push({ text: instructions });

    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents,
      config: {
        systemInstruction: "You are an expert OCR, transcription, and narrative model specialized in Italian and English comic books. You write perfect UTF-8 text and never corrupt accented letters.",
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            title: { type: Type.STRING, description: "Title or summary designation of the analyzed comic/document." },
            pageCount: { type: Type.INTEGER, description: "Total pages processed." },
            summary: { type: Type.STRING, description: "High-level summary of the transcribing run." },
            panels: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  panelNumber: { type: Type.INTEGER, description: "Sequential index of panel on page (1, 2, 3...)" },
                  pageNumber: { type: Type.INTEGER, description: "Page marker of this panel" },
                  characters: {
                    type: Type.ARRAY,
                    items: { type: Type.STRING },
                    description: "Characters detected in this panel."
                  },
                  narrativeCaption: { type: Type.STRING, description: "Text in rectangular yellow caption boxes or narrator lines." },
                  youtubeDescription: { type: Type.STRING, description: "A highly descriptive, atmospheric sensory scene narration integrating setting, actions, and all dialogue quotes directly." }
                },
                required: ["panelNumber", "pageNumber", "characters", "youtubeDescription"]
              }
            }
          },
          required: ["title", "pageCount", "summary", "panels"]
        }
      }
    });

    const parsedData = JSON.parse(response.text || "{}");
    const sanitizedData = sanitizeObject(parsedData);
    res.json(sanitizedData);
  } catch (err: any) {
    console.error("Error extracting panels:", err);
    res.status(500).json({ error: err.message || "Failed to process the comic panel extractor pipeline." });
  }
});

// 2. Generate Cinematic Scene Slides (Images) via Imagen / Gemini Image Model
app.post("/api/generate-image-asset", async (req, res) => {
  try {
    const { visualPrompt, style } = req.body;
    if (!visualPrompt) {
      res.status(400).json({ error: "visualPrompt is required." });
      return;
    }

    const ai = getGenAIClient();
    
    // Render detailed widescreen art according to modern Gemini image properties
    const enrichedPrompt = `Cinematic comic panel art. ${visualPrompt}. Widescreen, vibrant coloring, high impact composition, masterpiece, comic book style: ${style || "modern digital graphic"}.`;
    
    const imageResponse = await ai.models.generateImages({
      model: "imagen-4.0-generate-001",
      prompt: enrichedPrompt,
      config: {
        numberOfImages: 1,
        outputMimeType: "image/jpeg",
        aspectRatio: "16:9",
      },
    });

    if (imageResponse.generatedImages && imageResponse.generatedImages.length > 0) {
      const base64Bytes = imageResponse.generatedImages[0].image.imageBytes;
      res.json({ imageUrl: `data:image/jpeg;base64,${base64Bytes}` });
    } else {
      throw new Error("No images generated by the API model.");
    }
  } catch (err: any) {
    console.warn("Imagen generation error, trying fallback to gemini-2.5-flash-image:", err.message);
    try {
      const ai = getGenAIClient();
      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash-image",
        contents: {
          parts: [{ text: `Widescreen detailed comic book layout illustrating: ${req.body.visualPrompt}` }],
        },
        config: {
          imageConfig: {
            aspectRatio: "16:9",
          },
        },
      });

      let foundImage = false;
      if (response.candidates && response.candidates[0]?.content?.parts) {
        for (const part of response.candidates[0].content.parts) {
          if (part.inlineData) {
            res.json({ imageUrl: `data:img/png;base64,${part.inlineData.data}` });
            foundImage = true;
            break;
          }
        }
      }
      if (!foundImage) throw new Error("Fallback generateContent failed to yield inline image data.");
    } catch (fallbackErr: any) {
      console.error("Deep image generation failure:", fallbackErr);
      res.status(500).json({ error: "Failed to generate dynamic visual panels. Fallback UI will render styled gradients.", isFallback: true });
    }
  }
});

// 3. Generate Narrator Voice track (TTS) using real Gemini Speech TTS Modality
app.post("/api/generate-speech-asset", async (req, res) => {
  try {
    const { narratorText, dialogue, speaker, voiceName } = req.body;
    if (!narratorText) {
      res.status(400).json({ error: "narratorText is required." });
      return;
    }

    const ai = getGenAIClient();

    // Construct dramatic audio direction combining narration + spoken dialogue
    let speechPrompt = `Read the following comic audio script dramatically:
    Narrator: "${narratorText.replace(/"/g, '')}"`;
    
    if (dialogue && speaker) {
      speechPrompt += `\n${speaker}: "${dialogue.replace(/"/g, '')}"`;
    }

    const response = await ai.models.generateContent({
      model: "gemini-3.1-flash-tts-preview",
      contents: [{ parts: [{ text: speechPrompt }] }],
      config: {
        responseModalities: ["AUDIO"],
        speechConfig: {
          voiceConfig: {
            prebuiltVoiceConfig: { voiceName: voiceName || "Kore" },
          },
        },
      },
    });

    const base64Audio = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
    if (base64Audio) {
      res.json({ speechAudio: `data:audio/wav;base64,${base64Audio}` });
    } else {
      throw new Error("Speech compilation did not return any audio payload.");
    }
  } catch (err: any) {
    console.error("TTS speech generation failed:", err);
    res.status(500).json({ error: "Speech API was unavailable. Falling back to frontend speech synthesizer." });
  }
});

// 4. Generate Cinematic Video with Veo AI (Option B for premium, active video elements!)
app.post("/api/generate-video-asset", async (req, res) => {
  try {
    const { prompt, base64Image } = req.body;
    if (!prompt) {
      res.status(400).json({ error: "prompt is required for Veo compilation." });
      return;
    }

    const ai = getGenAIClient();
    const config: any = {
      numberOfVideos: 1,
      resolution: "720p",
      aspectRatio: "16:9"
    };

    let payload: any = {
      model: "veo-3.1-lite-generate-preview",
      prompt: `Cinematic comic book panning motion. ${prompt}. High quality comic coloring.`,
      config
    };

    // If we have an image frame from preceding Imagen step, supply it to preserve visual character continuity
    if (base64Image) {
      let cleanBase64 = base64Image;
      if (cleanBase64.includes(";base64,")) {
        cleanBase64 = cleanBase64.split(";base64,")[1];
      }
      payload.image = {
        imageBytes: cleanBase64,
        mimeType: "image/jpeg"
      };
    }

    const operation = await ai.models.generateVideos(payload);
    res.json({ operationName: operation.name });
  } catch (err: any) {
    console.error("Veo starting failure:", err);
    res.status(500).json({ error: err.message || "Failed to start Veo video compilation pipeline." });
  }
});

// 5. Poll Veo Video Operation Status
app.post("/api/video-status", async (req, res) => {
  try {
    const { operationName } = req.body;
    if (!operationName) {
      res.status(400).json({ error: "operationName is required for polling status." });
      return;
    }

    const ai = getGenAIClient();
    const { GenerateVideosOperation } = await import("@google/genai");

    const op = new GenerateVideosOperation();
    op.name = operationName;

    const updated = await ai.operations.getVideosOperation({ operation: op });
    res.json({ done: updated.done, response: updated.response });
  } catch (err: any) {
    console.error("Veo polling error:", err);
    res.status(500).json({ error: err.message || "Could not fetch video compilation state." });
  }
});

// 6. Direct Proxy Stream down for Veo MP4 Video
app.get("/api/video-download", async (req, res) => {
  try {
    const operationName = req.query.operationName as string;
    if (!operationName) {
      res.status(400).send("operationName query parameter is required.");
      return;
    }

    const ai = getGenAIClient();
    const apiKey = process.env.GEMINI_API_KEY;
    const { GenerateVideosOperation } = await import("@google/genai");

    const op = new GenerateVideosOperation();
    op.name = operationName;

    const updated = await ai.operations.getVideosOperation({ operation: op });
    const uri = updated.response?.generatedVideos?.[0]?.video?.uri;
    
    if (!uri) {
      res.status(404).send("Completed video resource location not found in operation report.");
      return;
    }

    // Proxy the video file stream down to protect keys
    const videoRes = await fetch(uri, {
      headers: { "x-goog-api-key": apiKey || "" },
    });

    res.setHeader("Content-Type", "video/mp4");
    
    if (videoRes.body) {
      const reader = videoRes.body.getReader();
      const stream = new ReadableStream({
        async start(controller) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            controller.enqueue(value);
          }
          controller.close();
        }
      });
      
      const buffer = await new Response(stream).arrayBuffer();
      res.send(Buffer.from(buffer));
    } else {
      res.status(500).send("Video download body stream empty.");
    }
  } catch (err: any) {
    console.error("Proxy video stream failure:", err);
    res.status(500).send("Failed to stream cinematic video assets.");
  }
});

// ----------------------------------------------------
// VITE DEV / PROD HOSTING MIDDLEWARE
// ----------------------------------------------------

async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    // Mount Vite middleware for dev modes (includes HMR/compilers)
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    // Hold static production directories securely
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`[FULLSTACK SERVER] Running on host 0.0.0.0 targeting Port ${PORT}`);
  });
}

startServer();
