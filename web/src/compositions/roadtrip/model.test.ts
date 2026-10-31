import {describe, expect, it} from 'vitest';
import {buildRouteModel} from '../driving/route';
import {
  cameraForDay, chapterOpacity, dayAtFrame, dayDistance, followMultiplier, followOpacity,
  type RoadTripDay, type RoadTripProps,
} from './model';

const steps = [{road: 'G318', points: [[100.0, 30.0], [100.1, 30.1], [100.2, 30.2], [100.3, 30.3]] as Array<[number, number]>}];

function day(id: string, startFrame: number, durationInFrames: number): RoadTripDay {
  return {
    id, title: id, subtitle: '', originLabel: '起点', destinationLabel: '终点',
    startFrame, durationInFrames, chapterFrames: 42, openingStart: 42, openingFrames: 60,
    followStart: 102, arrivalLocalFrame: durationInFrames - 60, pulloutFrames: 60,
    steps, totalDistanceMeters: 30000, administrativePlaces: [], cities: [],
    card: null, landmarks: [{id: 'turn', label: '拐点', distanceMeters: 12000}],
    narration: [{id: `${id}-a`, text: '旁白'}], segmentWindows: {},
  };
}

function props(): RoadTripProps {
  const first = day('day-01', 0, 600);
  const second = day('day-02', 600, 600);
  return {
    schemaVersion: 1, durationInFrames: 1200, fps: 30, width: 1080, height: 1920,
    title: '测试', originLabel: '起点', destinationLabel: '终点', attribution: '测试',
    sources: {}, days: [first, second], subtitleCues: [],
    subtitle: {safeArea: {x: 108, y: 1580, width: 864, height: 200}, fontSize: 40,
      lineHeight: 1.5, textColor: '#ffffff', plateColor: '#000000'},
  };
}

describe('roadtrip model', () => {
  it('maps frames to the owning day without crossing boundaries', () => {
    const value = props();
    expect(dayAtFrame(value, 0).day.id).toBe('day-01');
    expect(dayAtFrame(value, 599).day.id).toBe('day-01');
    expect(dayAtFrame(value, 600).day.id).toBe('day-02');
    expect(dayAtFrame(value, 600).localFrame).toBe(0);
  });

  it('produces deterministic cameras for the same frame', () => {
    const value = props();
    const model = buildRouteModel(steps);
    const first = cameraForDay(model, value.days[1]!, 300, 1080, 1920);
    const second = cameraForDay(model, value.days[1]!, 300, 1080, 1920);
    expect(first).toEqual(second);
    expect(first.scale).toBeGreaterThan(0);
  });

  it('raises the follow multiplier only inside the landmark window', () => {
    const model = buildRouteModel(steps);
    const target = {...day('day-04', 0, 600),
      landmarks: [{id: 'nujiang-72-turns', label: '七十二拐', distanceMeters: 12000}]};
    const center = 12000 / model.lengthMeters;
    expect(followMultiplier(target, center, model.lengthMeters)).toBeGreaterThan(12);
    expect(followMultiplier(target, 0, model.lengthMeters)).toBe(12);
  });

  it('warms and cools chapter/follow opacity at day edges', () => {
    const target = props().days[0]!;
    expect(chapterOpacity(target, 0)).toBe(1);
    expect(chapterOpacity(target, target.chapterFrames)).toBe(0);
    expect(followOpacity(target, target.followStart - 1)).toBe(0);
    expect(followOpacity(target, target.followStart + 1)).toBe(1);
    expect(followOpacity(target, target.durationInFrames - 1)).toBe(0);
  });

  it('advances distance only during the follow window', () => {
    const model = buildRouteModel(steps);
    const target = props().days[0]!;
    expect(dayDistance(model, target, target.followStart - 1)).toBe(0);
    expect(dayDistance(model, target, target.arrivalLocalFrame)).toBe(model.lengthMeters);
  });
});
