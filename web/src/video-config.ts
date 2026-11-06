import config from './video-config.json';

/** 金融的固定帧率，来自跨语言配置。 */
export const FPS = config.fps;
export const BUILDING_FPS = config.buildingConstruction.defaultFps;
export const VEHICLE_SHOWCASE_FPS = config.vehicleShowcase.defaultFps;
export const GENERAL_DEFAULT_FPS = config.general.defaultFps;
export const GENERAL_ALLOWED_FPS = config.general.allowedFps;
