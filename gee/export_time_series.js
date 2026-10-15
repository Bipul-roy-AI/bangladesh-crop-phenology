/* Bangladesh crop phenology: Sentinel-2 NDVI and Sentinel-1 VV/VH.
 * Run in the Earth Engine Code Editor after drawing a polygon named geometry.
 * The drawn polygon is ONE sample, not a district-wide crop classification.
 * Replace samples with field polygons containing unique sample_id properties.
 * Export -> Python detector -> independent field validation.
 */
var YEAR = 2024;
var STEP_DAYS = 15;  // Match --step-days in the Python CLI.
var PAD_DAYS = 180;
var SCALE = 10;
if (typeof geometry === 'undefined') {
  throw new Error('Draw/import a polygon named geometry before running.');
}
var roi = geometry;
var samples = ee.FeatureCollection([
  ee.Feature(roi, {sample_id: 'drawn_sample_001'})
]);
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
  collection: table, description: 'bangladesh_phenology_' + YEAR,
  fileFormat: 'CSV', selectors: [
    'sample_id', 'date', 'ndvi', 'valid_pixels', 'vv_db', 'vh_db', 's2_scenes', 's1_scenes'
  ]
});
