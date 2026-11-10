import {describe, expect, it} from 'vitest';
import {createFlight} from './flight';
import {LAYOUT, positionOf} from './layout';
import {trialConfig} from './trial-config';
import type {CodeSceneProps} from '../src/code-scene/context';
import type {Shot} from '../src/code-scene/cinematic/camera';

const config = trialConfig({props: {}, fps: 60, durationInFrames: 2, width: 1920, height: 1080,
  segmentWindows: {}, subtitleSafeArea: {x: 100, y: 900, width: 1720, height: 100}} satisfies CodeSceneProps);
const shots = config.props.shots as Shot[];
const makeFlight = () => createFlight(shots, config.segmentWindows,
  Object.fromEntries(Object.keys(LAYOUT).map(id => [id, positionOf(id)])));

describe('continuous journey camera', () => {
  it('returns the same pose after seeking in arbitrary order', () => {
    const flight = makeFlight();
    const indices = [0, ...Object.values(config.segmentWindows).map(window => window.startFrame),
      config.durationInFrames - 1];
    const original = indices.map(frame => flight(frame));
    for (let index = indices.length - 1; index >= 0; index--) {
      const pose = flight(indices[index]);
      expect(pose.position.distanceTo(original[index].position)).toBeLessThan(1e-9);
      expect(pose.quaternion.toArray()).toEqual(original[index].quaternion.toArray());
      expect(pose.fov).toBe(original[index].fov);
    }
  });

  it('keeps position and orientation continuous across joined shot boundaries', () => {
    const flight = makeFlight();
    for (const shot of shots.slice(1)) {
      const before = flight(shot.startFrame - 0.0001);
      const after = flight(shot.startFrame + 0.0001);
      expect(after.position.distanceTo(before.position)).toBeLessThan(0.001);
      expect(after.quaternion.angleTo(before.quaternion)).toBeLessThan(0.001);
      expect([...after.position.toArray(), ...after.quaternion.toArray(), after.fov].every(Number.isFinite)).toBe(true);
    }
  });
});
