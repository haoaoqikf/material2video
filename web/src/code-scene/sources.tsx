/** 已校验结构化来源的场景绘制入口；作品只提供来源 ID。 */
import {useEffect, useRef} from 'react';
import {useSceneContext} from './context';
import {useSceneSource} from './sdk';
import {FinancialTimeSeries, type FinancialTimeSeriesProps} from '../types/financial/FinancialTimeSeries';
import {BuildingConstruction, type BuildingProps} from '../types/building_construction/BuildingConstruction';
import {VehicleShowcase, type VehicleShowcaseProps} from '../types/vehicle_showcase/VehicleShowcase';

function source(id: string, kind: string) {
  const item = useSceneSource(id);
  if (item.kind !== kind) throw new Error(`来源 ${id} 不是 ${kind}`);
  return item.data;
}

export function FinancialSeriesScene({id}: {id: string}) {
  const data = source(id, 'financial-series') as FinancialTimeSeriesProps;
  const {ready} = useSceneContext();
  const announced = useRef(false);
  useEffect(() => {
    if (!announced.current) { announced.current = true; ready(); }
  }, [ready]);
  return <FinancialTimeSeries {...data}/>;
}

export function ConstructionScene({id}: {id: string}) {
  return <BuildingConstruction {...source(id, 'construction') as BuildingProps}/>;
}

export function VehicleScene({id}: {id: string}) {
  return <VehicleShowcase {...source(id, 'vehicle-model') as VehicleShowcaseProps}/>;
}
