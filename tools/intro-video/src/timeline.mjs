// One beat grid for the video and the music, so every cut and sound lands on a beat.
export const BPM = 120;
export const FPS = 60;
export const BEAT = (FPS * 60) / BPM;
export const TRANSITION = BEAT / 2;

export const SCENES = [
  {id: 'Title', beats: 8},
  {id: 'Add', beats: 12},
  {id: 'Library', beats: 4},
  {id: 'Read', beats: 16},
  {id: 'Overview', beats: 16},
  {id: 'Blog', beats: 8},
  {id: 'Kindle', beats: 12},
  {id: 'Outro', beats: 12},
];

// First beat of each scene on the whole timeline.
export const START = Object.fromEntries(SCENES.map((scene, i) =>
  [scene.id, SCENES.slice(0, i).reduce((sum, previous) => sum + previous.beats, 0)]));
export const TOTAL_BEATS = SCENES.reduce((sum, scene) => sum + scene.beats, 0);

// Cues in beats from the start of their scene.
export const CUES = {
  Title: {words: [0, 0.5, 1, 1.5, 2.5, 3, 3.5, 4, 4.5], logo: 5.5},
  Add: {typeStart: 3, typeEnd: 7, click: 8},
  Read: {preferences: 4, preferencesClose: 7, size: 8, dark: 12},
  Kindle: {expand: 3, send: 6, arrive: 8},
};
