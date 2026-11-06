/**
 * 场景说明：左上角小字，年份（金）+ 地点（灰）。属于来源与解释，可作小字保留。
 */
import {T, color} from './kit';

export type SceneNoteProps = {
  year: string;
  place: string;
  opacity?: number;
  x?: number;
  y?: number;
  role?: string;
  state?: string;
};

export default function SceneNote({
  year, place, opacity = 1, x = T.layout.sceneNote.x, y = T.layout.sceneNote.y, role, state,
}: SceneNoteProps) {
  return (
    <div data-m2v-role={role} data-m2v-state={state} style={{
      position: 'absolute', left: x, top: y, opacity, pointerEvents: 'none',
      fontFamily: T.type.fontStack, whiteSpace: 'nowrap',
    }}>
      <span style={{fontSize: T.type.sceneYear, fontWeight: 700, color: color('gold')}}>{year}</span>
      <span style={{fontSize: T.type.scenePlace, color: color('dim'), marginLeft: 14}}>{place}</span>
    </div>
  );
}
