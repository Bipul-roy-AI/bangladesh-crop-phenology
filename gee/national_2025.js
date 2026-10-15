/* Bangladesh 2025: district-batched exploratory cropland sampling.
 * Paste this standalone script into the Earth Engine Code Editor.
 * Change DISTRICT_INDEX from 0 to districtCount-1 and export each district.
 * Sample points represent historical mapped cropland, NOT surveyed crop labels.
 * This samples national coverage; it does not create a wall-to-wall crop map.
 */
var YEAR = 2025;
var DISTRICT_INDEX = 0;
var SAMPLES_PER_DISTRICT = 50;
var RANDOM_SEED = 2025;
var STEP_DAYS = 15;
var PAD_DAYS = 180;
var SCALE = 10;

var districts = ee.FeatureCollection('FAO/GAUL/2015/level2')
  .filter(ee.Filter.eq('ADM0_NAME', 'Bangladesh')).sort('ADM2_CODE');
var districtCount = districts.size();
print('District count: inspect against expected 64 before proceeding', districtCount);
print('Ordered district names', districts.aggregate_array('ADM2_NAME'));
var district = ee.Feature(districts.toList(districtCount).get(DISTRICT_INDEX));
var roi = district.geometry();
print('Selected district', district.get('ADM2_NAME'));
// Historical sampling frame only. It can omit land converted to crops by 2025
// and include land that stopped being cropland. Validate and update this frame.
var historicalCropland = ee.ImageCollection('ESA/WorldCover/v200').first()
  .select('Map').eq(40).rename('cropland').selfMask();
var samples = historicalCropland.stratifiedSample({
  numPoints: SAMPLES_PER_DISTRICT, classBand: 'cropland',
  region: roi, scale: SCALE, seed: RANDOM_SEED,
  geometries: true, tileScale: 4
}).map(function(feature) {
  var xy = feature.geometry().coordinates();
  return feature.set({
    sample_id: ee.Number(district.get('ADM2_CODE')).format('%d')
      .cat('_').cat(ee.Number(xy.get(0)).format('%.6f'))
      .cat('_').cat(ee.Number(xy.get(1)).format('%.6f')),
    district: district.get('ADM2_NAME'), district_code: district.get('ADM2_CODE'),
    longitude: xy.get(0), latitude: xy.get(1), sampling_frame_year: 2021
  });
});
print('Actual sample count (may be below requested count)', samples.size());
Map.addLayer(historicalCropland.clip(roi), {palette: ['green']}, '2021 sampling frame', false);
var start = ee.Date.fromYMD(YEAR, 1, 1).advance(-PAD_DAYS, 'day');
var end = ee.Date.fromYMD(YEAR + 1, 1, 1).advance(PAD_DAYS, 'day');

function cleanS2(image) {
  var scl = image.select('SCL');
  // Retain vegetation, bare surfaces and water; drop cloud/shadow/snow/unknown.
  var clear = scl.eq(4).or(scl.eq(5)).or(scl.eq(6));
  var reflectance = image.select(['B8', 'B4']).multiply(0.0001).updateMask(clear);
  return reflectance.normalizedDifference(['B8', 'B4']).rename('ndvi')
    .copyProperties(image, ['system:time_start']);
}
var optical = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(roi).filterDate(start, end).map(cleanS2);
// Keep acquisition geometry consistent. Inspect local coverage before changing.
var radar = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(roi).filterDate(start, end)
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'));
print('S1 relative orbits: choose ONE locally supported orbit before analysis',
  radar.aggregate_histogram('relativeOrbitNumber_start'));
// A fixed orbit prevents mixing different incidence geometries.
var relativeOrbit = radar.aggregate_array('relativeOrbitNumber_start').distinct().sort();
var orbit = ee.Number(ee.Algorithms.If(relativeOrbit.size().gt(0), relativeOrbit.get(0), -1));
radar = radar.filter(ee.Filter.eq('relativeOrbitNumber_start', orbit));
print('Selected relative orbit (verify coverage)', orbit);

var blankNDVI = ee.Image.constant(0).rename('ndvi').updateMask(ee.Image.constant(0));
var blankRadar = ee.Image.constant([0, 0]).rename(['VV', 'VH'])
  .updateMask(ee.Image.constant(0));
var bins = ee.List.sequence(0, end.difference(start, 'day').divide(STEP_DAYS).ceil().subtract(1));
var table = ee.FeatureCollection(bins.map(function(i) {
  var t0 = start.advance(ee.Number(i).multiply(STEP_DAYS), 'day');
  var t1 = ee.Date(ee.Number(t0.advance(STEP_DAYS, 'day').millis()).min(end.millis()));
  var s2 = optical.filterDate(t0, t1);
  var s1 = radar.filterDate(t0, t1).select(['VV', 'VH']);
  var ndvi = ee.Image(ee.Algorithms.If(s2.size().gt(0), s2.median(), blankNDVI));
  var sar = ee.Image(ee.Algorithms.If(s1.size().gt(0), s1.median(), blankRadar));
  return ndvi.addBands(sar).reduceRegions({
    collection: samples,
    reducer: ee.Reducer.mean().combine({reducer2: ee.Reducer.count(), sharedInputs: true}),
    scale: SCALE, tileScale: 4
  }).map(function(feature) {
    return ee.Feature(null, {
      sample_id: feature.get('sample_id'), date: t0.format('YYYY-MM-dd'),
      district: feature.get('district'), district_code: feature.get('district_code'),
      longitude: feature.get('longitude'), latitude: feature.get('latitude'),
      sampling_frame_year: feature.get('sampling_frame_year'),
      ndvi: feature.get('ndvi_mean'), valid_pixels: feature.get('ndvi_count'),
      vv_db: feature.get('VV_mean'), vh_db: feature.get('VH_mean'),
      s2_scenes: s2.size(), s1_scenes: s1.size()
    });
  });
})).flatten();

Map.centerObject(roi);
Map.addLayer(samples, {color: 'yellow'}, 'Samples');
print('Preview', table.limit(10));
Export.table.toDrive({
  collection: table, description: 'bangladesh_phenology_' + YEAR + '_district_' + DISTRICT_INDEX,
  fileFormat: 'CSV', selectors: [
    'sample_id', 'district', 'district_code', 'longitude', 'latitude',
    'sampling_frame_year', 'date', 'ndvi', 'valid_pixels', 'vv_db', 'vh_db', 's2_scenes', 's1_scenes'
  ]
});
