export interface Scene {
  id: string;
  title: string;
  narratorText: string;
  characterDialogue: string;
  characterDialogueSpeaker: string;
  soundEffect: string;
  visualPrompt: string;
  cameraMovement: 'pan_left' | 'pan_right' | 'zoom_in' | 'zoom_out' | 'tilt_up' | 'tilt_down' | 'static';
  imageUrl: string | null;
  speechAudio: string | null; // Base64 audio string (data:audio/mp3;base64,...)
  videoUrl: string | null; // Generated video URL if Veo is used
  videoOperationName: string | null; // Operation name from Veo API
  videoStatus: 'idle' | 'pending' | 'completed' | 'failed';
  duration: number; // in seconds
  sourcePageNumber?: number; // Sourced page from input PDF or comic
}

export interface Storyboard {
  title: string;
  genre: string;
  summary: string;
  soundtrackStyle: string; // e.g. "Action Synth", "Fantasy Orchestral", "Mysterious Ambient"
  scenes: Scene[];
}

export interface ExtractedPanel {
  panelNumber: number;
  pageNumber: number;
  characters: string[];
  narrativeCaption?: string;
  youtubeDescription?: string;
}

export interface ExtractResponse {
  title: string;
  pageCount: number;
  summary: string;
  panels: ExtractedPanel[];
}

export interface GenerationStatus {
  step: 'idle' | 'uploading' | 'parsing' | 'generating_assets' | 'completed' | 'failed';
  progress: number; // 0 to 100
  message: string;
}
