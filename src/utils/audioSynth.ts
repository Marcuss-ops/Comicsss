// Procedural background music drone generator using Web Audio API

class AudioSynthEngine {
  private ctx: AudioContext | null = null;
  private primaryOsc: OscillatorNode | null = null;
  private secondaryOsc: OscillatorNode | null = null;
  private noiseNode: AudioWorkletNode | ScriptProcessorNode | null = null;
  private filter: BiquadFilterNode | null = null;
  private masterGain: GainNode | null = null;
  private intervalId: any = null;
  private notesList: number[] = [110, 130.81, 146.83, 164.81, 196.0]; // Am7, G-ish pentatonic

  constructor() {}

  public start(style: string) {
    try {
      if (this.ctx) {
        this.stop();
      }

      this.ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const ctx = this.ctx;

      // Master Gain for safe volume limits
      this.masterGain = ctx.createGain();
      this.masterGain.gain.setValueAtTime(0, ctx.currentTime);
      this.masterGain.connect(ctx.destination);

      // Main Low Filter
      this.filter = ctx.createBiquadFilter();
      this.filter.type = "lowpass";
      this.filter.frequency.setValueAtTime(450, ctx.currentTime);
      this.filter.connect(this.masterGain);

      // Set chord profiles based on soundtrackStyle
      let baseFreq = 110; // A2
      let chordIntervals = [1, 1.25, 1.5, 1.875]; // Major triad-ish

      if (style.toLowerCase().includes("cyber") || style.toLowerCase().includes("synth")) {
        baseFreq = 82.41; // E2 (Heavy bass)
        chordIntervals = [1, 1.189, 1.498, 1.782]; // Dark minor-ish
      } else if (style.toLowerCase().includes("orchestral") || style.toLowerCase().includes("hero")) {
        baseFreq = 130.81; // C3
        chordIntervals = [1, 1.2, 1.5, 2.0]; // Heroic C minor / Major sweep
      } else if (style.toLowerCase().includes("spooky") || style.toLowerCase().includes("ambient") || style.toLowerCase().includes("dark")) {
        baseFreq = 73.42; // D2 (Very deep drone)
        chordIntervals = [1, 1.059, 1.414, 1.888]; // Eerie tritone
      }

      // 1. Primary Low Drone
      this.primaryOsc = ctx.createOscillator();
      this.primaryOsc.type = "sawtooth";
      this.primaryOsc.frequency.setValueAtTime(baseFreq, ctx.currentTime);
      
      const primGain = ctx.createGain();
      primGain.gain.setValueAtTime(0.04, ctx.currentTime);
      this.primaryOsc.connect(primGain);
      primGain.connect(this.filter);
      this.primaryOsc.start();

      // 2. Secondary Harmonizer Drone
      this.secondaryOsc = ctx.createOscillator();
      this.secondaryOsc.type = "sine";
      this.secondaryOsc.frequency.setValueAtTime(baseFreq * chordIntervals[2], ctx.currentTime);
      
      const secGain = ctx.createGain();
      secGain.gain.setValueAtTime(0.06, ctx.currentTime);
      this.secondaryOsc.connect(secGain);
      secGain.connect(this.filter);
      this.secondaryOsc.start();

      // Smooth master gain fade in
      this.masterGain.gain.linearRampToValueAtTime(0.18, ctx.currentTime + 2.0);

      // 3. Simple rhythmic arpeggiator / chime pattern
      let steps = 0;
      this.intervalId = setInterval(() => {
        if (!ctx || ctx.state === "suspended") return;

        // Play random note from selected harmony
        const chime = ctx.createOscillator();
        const chimeGain = ctx.createGain();
        const chimeDelay = ctx.createDelay();
        const feedback = ctx.createGain();

        const noteIndex = steps % chordIntervals.length;
        const pitch = baseFreq * chordIntervals[noteIndex] * (Math.floor(steps / 4) % 2 === 0 ? 3 : 2);

        chime.type = "triangle";
        chime.frequency.setValueAtTime(pitch, ctx.currentTime);

        chimeGain.gain.setValueAtTime(0.02, ctx.currentTime);
        chimeGain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 1.2);

        chimeDelay.delayTime.setValueAtTime(0.3, ctx.currentTime);
        feedback.gain.setValueAtTime(0.4, ctx.currentTime);

        // Feed chimes into feedback loop
        chime.connect(chimeGain);
        chimeGain.connect(this.filter);
        
        // Echo effect
        chimeGain.connect(chimeDelay);
        chimeDelay.connect(feedback);
        feedback.connect(chimeDelay);
        feedback.connect(this.filter);

        chime.start();
        chime.stop(ctx.currentTime + 1.5);

        steps++;
      }, 900);

    } catch (e) {
      console.warn("AudioContext failed or is blocked by browser interaction guidelines:", e);
    }
  }

  public stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    try {
      if (this.masterGain && this.ctx) {
        this.masterGain.gain.cancelScheduledValues(this.ctx.currentTime);
        this.masterGain.gain.linearRampToValueAtTime(0, this.ctx.currentTime + 0.3);
      }
      setTimeout(() => {
        if (this.primaryOsc) {
          this.primaryOsc.stop();
          this.primaryOsc = null;
        }
        if (this.secondaryOsc) {
          this.secondaryOsc.stop();
          this.secondaryOsc = null;
        }
        if (this.ctx) {
          this.ctx.close();
          this.ctx = null;
        }
      }, 400);
    } catch (e) {
       console.warn("Error tearing down AudioContext", e);
    }
  }
}

export const audioSynth = new AudioSynthEngine();
