import config from './video-config.json';

/** 金融的固定帧率，来自跨语言配置。 */
export const FPS = config.fps;
/** 自驾路线的固定帧率；该类型默认 30 fps。 */
export const DRIVING_ROUTE_FPS = config.drivingRoute.defaultFps;
export const BUILDING_FPS = config.buildingConstruction.defaultFps;
export const VEHICLE_SHOWCASE_FPS = config.vehicleShowcase.defaultFps;
/** 多日地图游记固定 30 fps。 */
export const ROAD_TRIP_FPS = config.roadTrip.defaultFps;
export const GENERAL_DEFAULT_FPS = config.general.defaultFps;
export const GENERAL_ALLOWED_FPS = config.general.allowedFps;
