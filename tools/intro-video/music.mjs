// Synthesizes the soundtrack to public/music.wav from the shared beat grid. No samples, so no license.
import {writeFileSync} from 'node:fs';
import {BPM, CUES, SCENES, START, TOTAL_BEATS} from './src/timeline.mjs';

const RATE = 48000;
const SPB = 60 / BPM;
const length = Math.round(TOTAL_BEATS * SPB * RATE);
const left = new Float32Array(length), right = new Float32Array(length);
const sendL = new Float32Array(length), sendR = new Float32Array(length);
const at = beat => Math.round(beat * SPB * RATE);
const hz = midi => 440 * 2 ** ((midi - 69) / 12);

// Deterministic noise keeps every render identical.
let seed = 7;
const noise = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 31) - 1;

// Zero-delay state-variable filter, stable at any cutoff; one instance per voice.
const filter = () => {
  let s1 = 0, s2 = 0;
  return (x, cutoff, q = 0.7) => {
    const g = Math.tan(Math.PI * Math.min(cutoff, RATE * 0.45) / RATE), k = 1 / q;
    const a1 = 1 / (1 + g * (g + k)), a2 = g * a1, a3 = g * a2;
    const v3 = x - s2, band = a1 * s1 + a2 * v3, low = s2 + a2 * s1 + a3 * v3;
    s1 = 2 * band - s1; s2 = 2 * low - s2;
    return {low, band, high: x - k * band - low};
  };
};

const add = (i, value, pan = 0, send = 0) => {
  if (i < 0 || i >= length) return;
  const l = value * Math.cos((pan + 1) * Math.PI / 4), r = value * Math.sin((pan + 1) * Math.PI / 4);
  left[i] += l; right[i] += r; sendL[i] += l * send; sendR[i] += r * send;
};

// D major, I-V-vi-IV. The last bar resolves on D.
const CHORDS = [
  {pad: [57, 62, 66, 74], bass: 38},
  {pad: [57, 61, 64, 73], bass: 45},
  {pad: [59, 62, 66, 74], bass: 47},
  {pad: [59, 62, 67, 71], bass: 43},
];
const chordAt = beat => CHORDS[beat >= TOTAL_BEATS - 4 ? 0 : Math.floor(beat / 4) % 4];

const drumsOn = beat => beat >= START.Add && beat < START.Outro + 4;
const kicks = [];
for (let b = START.Add; b < START.Outro + 4; b++) kicks.push(at(b));
// Sidechain: pads and bass dip after each kick.
const duck = new Float32Array(length).fill(1);
for (const k of kicks) for (let i = 0; i < RATE * 0.3 && k + i < length; i++) duck[k + i] = Math.min(duck[k + i], 1 - 0.55 * Math.exp(-i / RATE / 0.09));

// Pad: three detuned band-limited saws per note through a sweeping low-pass filter.
const saw = (phase, dt) => {
  let value = 2 * phase - 1;
  if (phase < dt) { const t = phase / dt; value -= t + t - t * t - 1; }
  else if (phase > 1 - dt) { const t = (phase - 1) / dt; value -= t * t + t + t + 1; }
  return value;
};
for (let bar = 0; bar < TOTAL_BEATS / 4; bar++) {
  const chord = chordAt(bar * 4), begin = at(bar * 4), end = at(bar * 4 + 4) + RATE * 0.6;
  chord.pad.forEach((note, n) => [-8, 0, 8].forEach((cents, v) => {
    const f = hz(note) * 2 ** (cents / 1200), dt = f / RATE, lp = filter();
    let phase = (n * 0.31 + v * 0.17) % 1;
    for (let i = begin; i < Math.min(end, length); i++) {
      const t = (i - begin) / RATE, beat = i / RATE / SPB;
      const env = Math.min(1, t / 0.35) * Math.min(1, Math.max(0, (end - i) / RATE / 0.6)) ** 3;
      const cutoff = beat < START.Add ? 700 + 1500 * (beat / START.Add) ** 2 : 2200;
      phase = (phase + dt) % 1;
      add(i, lp(saw(phase, dt), cutoff).low * env * 0.036 * duck[i], v - 1, 0.5);
    }
  }));
}

// Pluck arpeggio on sixteenths: a short FM bell.
const ARP = [0, 1, 2, 3, 2, 1, 3, 2];
for (let s = 0; s < TOTAL_BEATS * 4; s++) {
  const beat = s / 4, chord = chordAt(beat);
  const note = chord.pad[1 + (ARP[s % 8] % 3)] + 12 + (ARP[s % 8] === 3 ? 12 : 0);
  const f = hz(note), begin = at(beat);
  const gain = (beat < START.Add ? 0.6 + 0.4 * beat / START.Add : 1) * (s % 4 === 0 ? 1 : 0.7);
  const fade = beat >= TOTAL_BEATS - 6 ? Math.max(0, (TOTAL_BEATS - beat) / 6) : 1;
  for (let i = 0; i < RATE * 0.35; i++) {
    const t = i / RATE;
    const value = Math.sin(2 * Math.PI * f * t + 1.4 * Math.exp(-t / 0.04) * Math.sin(2 * Math.PI * 2 * f * t));
    add(begin + i, value * Math.exp(-t / 0.11) * 0.09 * gain * fade, s % 2 ? 0.35 : -0.35, 0.35);
  }
}

// Ping-pong echo on the arpeggio's send, three sixteenths behind.
{
  const delay = at(0.75);
  for (let i = delay; i < length; i++) { left[i] += sendR[i - delay] * 0.22; right[i] += sendL[i - delay] * 0.22; }
}

// Bass on the offbeat eighths while the drums play, and a held root in the intro and outro.
for (let e = 0; e < TOTAL_BEATS * 2; e++) {
  const beat = e / 2, f = hz(chordAt(beat).bass), begin = at(beat);
  const pumping = drumsOn(beat);
  if (pumping && e % 2 === 0) continue;
  const hold = pumping ? 0.2 : 0.5;
  for (let i = 0; i < RATE * hold * 2; i++) {
    const t = i / RATE;
    const env = Math.min(1, t / 0.008) * Math.exp(-t / hold);
    add(begin + i, Math.tanh(1.6 * Math.sin(2 * Math.PI * f * t)) * env * (pumping ? 0.12 : 0.07) * duck[begin + i]);
  }
}

// Drums.
const kick = (begin, gain = 1) => {
  let phase = 0;
  for (let i = 0; i < RATE * 0.5; i++) {
    const t = i / RATE;
    phase += (45 + 110 * Math.exp(-t / 0.03)) / RATE;
    add(begin + i, (Math.sin(2 * Math.PI * phase) * Math.exp(-t / 0.22) + (i < 150 ? noise() * 0.3 : 0)) * 0.36 * gain);
  }
};
const clap = begin => {
  const bp = filter();
  for (let i = 0; i < RATE * 0.3; i++) {
    const t = i / RATE, burst = [0, 0.011, 0.022].some(start => t >= start && t < start + 0.008) ? 1 : 0;
    const env = Math.max(burst, t > 0.022 ? Math.exp(-(t - 0.022) / 0.07) : 0);
    add(begin + i, bp(noise(), 1300, 1.2).band * env * 0.22, 0, 0.4);
  }
};
const hat = (begin, gain, pan) => {
  const hp = filter();
  for (let i = 0; i < RATE * 0.06; i++) add(begin + i, hp(noise(), 8000).high * Math.exp(-i / RATE / 0.018) * gain, pan);
};
for (let b = 0; b < TOTAL_BEATS; b++) {
  if (!drumsOn(b)) continue;
  if (b !== START.Outro) kick(at(b));
  if (b % 2 === 1 && b < START.Outro) clap(at(b));
  if (b < START.Outro) {
    hat(at(b + 0.5), 0.12, 0.2);
    hat(at(b + 0.25), 0.03, -0.3);
    hat(at(b + 0.75), 0.03, -0.3);
  }
}

// Effects on cues.
const crash = (begin, gain = 1) => {
  const hp = filter();
  for (let i = 0; i < RATE * 2.2; i++) add(begin + i, hp(noise(), 5000).high * Math.exp(-i / RATE / 0.7) * 0.12 * gain, 0, 0.6);
};
const sweep = (begin, seconds, from, to, gain, shape) => {
  const bp = filter();
  const count = Math.round(seconds * RATE);
  for (let i = 0; i < count; i++) {
    const p = i / count;
    add(begin + i, bp(noise(), from * (to / from) ** p, 1.5).band * shape(p) * gain, -0.7 + 1.4 * p, 0.3);
  }
};
// Riser into the first drop.
sweep(at(CUES.Title.logo - 1.5), (START.Add - CUES.Title.logo + 1.5) * SPB, 250, 7000, 0.35, p => p ** 2.2);
crash(at(START.Add));
kick(at(START.Outro), 1.2);
crash(at(START.Outro), 1.2);
// A whoosh on every scene change after the first.
for (const scene of SCENES.slice(2)) sweep(at(START[scene.id] - 0.35), 0.5, 500, 3500, 0.28, p => Math.sin(Math.PI * p) ** 2);

const tick = (begin, frequency, gain, seconds = 0.012) => {
  for (let i = 0; i < RATE * seconds; i++) {
    const t = i / RATE;
    add(begin + i, (Math.sin(2 * Math.PI * frequency * t) * 0.6 + noise() * 0.4) * Math.exp(-t / (seconds / 4)) * gain);
  }
};
// Title words.
for (const word of CUES.Title.words) tick(at(word), 1800, 0.12, 0.02);
// Typing on thirty-second notes, then the Add paper click.
for (let b = CUES.Add.typeStart; b < CUES.Add.typeEnd; b += 0.125) tick(at(START.Add + b), 3200 + 400 * Math.sin(b * 11), 0.06);
tick(at(START.Add + CUES.Add.click), 2100, 0.35, 0.02);
tick(at(START.Add + CUES.Add.click), 180, 0.4, 0.05);
// Dialog pop, theme switch, and the Kindle arrival.
const pop = (begin, gain = 0.12) => {
  for (let i = 0; i < RATE * 0.09; i++) {
    const t = i / RATE;
    add(begin + i, Math.sin(2 * Math.PI * (500 + 5000 * t) * t) * Math.exp(-t / 0.025) * gain, 0, 0.3);
  }
};
pop(at(START.Read + CUES.Read.preferences));
tick(at(START.Read + CUES.Read.dark), 1500, 0.25, 0.015);
tick(at(START.Read + CUES.Read.dark + 0.06), 1100, 0.2, 0.015);
pop(at(START.Kindle + CUES.Kindle.arrive), 0.16);
// Two bell notes when the logo lands.
for (const [beat, note] of [[START.Outro + 1, 86], [START.Outro + 1.5, 93]]) {
  const f = hz(note);
  for (let i = 0; i < RATE * 2.5; i++) {
    const t = i / RATE;
    add(at(beat) + i, Math.sin(2 * Math.PI * f * t + 2 * Math.exp(-t / 0.3) * Math.sin(2 * Math.PI * 3.5 * f * t)) * Math.exp(-t / 0.7) * 0.07, 0, 0.6);
  }
}

// Reverb on the send bus: four damped combs into two all-passes per channel.
const reverb = (input, offset) => {
  const out = new Float32Array(length);
  for (const size of [1557, 1617, 1491, 1422]) {
    const buffer = new Float32Array(size + offset);
    let index = 0, damp = 0;
    for (let i = 0; i < length; i++) {
      const delayed = buffer[index];
      damp = delayed * 0.7 + damp * 0.3;
      buffer[index] = input[i] + damp * 0.8;
      out[i] += delayed / 4;
      index = (index + 1) % buffer.length;
    }
  }
  for (const size of [556, 441]) {
    const buffer = new Float32Array(size + offset);
    let index = 0;
    for (let i = 0; i < length; i++) {
      const delayed = buffer[index];
      buffer[index] = out[i] + delayed * 0.5;
      out[i] = delayed - out[i];
      index = (index + 1) % buffer.length;
    }
  }
  return out;
};
const wetL = reverb(sendL, 0), wetR = reverb(sendR, 23);

// Mix, fade the last beats, soft-clip, and peak at -3 dBFS.
const fadeStart = at(TOTAL_BEATS - 3);
let peak = 0;
for (let i = 0; i < length; i++) {
  const fade = i > fadeStart ? Math.cos((i - fadeStart) / (length - fadeStart) * Math.PI / 2) : 1;
  left[i] = Math.tanh((left[i] + wetL[i] * 0.3) * 1.2) * fade;
  right[i] = Math.tanh((right[i] + wetR[i] * 0.3) * 1.2) * fade;
  peak = Math.max(peak, Math.abs(left[i]), Math.abs(right[i]));
}
const scale = 10 ** (-3 / 20) / peak;
const wav = Buffer.alloc(44 + length * 4);
wav.write('RIFF', 0); wav.writeUInt32LE(36 + length * 4, 4); wav.write('WAVEfmt ', 8);
wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(2, 22); wav.writeUInt32LE(RATE, 24);
wav.writeUInt32LE(RATE * 4, 28); wav.writeUInt16LE(4, 32); wav.writeUInt16LE(16, 34);
wav.write('data', 36); wav.writeUInt32LE(length * 4, 40);
for (let i = 0; i < length; i++) {
  wav.writeInt16LE(Math.round(left[i] * scale * 32767), 44 + i * 4);
  wav.writeInt16LE(Math.round(right[i] * scale * 32767), 46 + i * 4);
}
writeFileSync(new URL('public/music.wav', import.meta.url), wav);
console.log(`Wrote public/music.wav: ${(length / RATE).toFixed(2)} s at ${BPM} BPM`);
