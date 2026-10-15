"""Independent reference collection: never turn model candidates into truth."""
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path

ANNUAL_FIELDS = ['sample_id', 'year', 'longitude', 'latitude', 'district',
                 'reference_land_cover', 'annual_review_complete', 'reference_cycle_count',
                 'crop_sequence_2025', 'source_type', 'source_reference', 'source_dates', 'reviewer',
                 'review_date', 'notes']
EPISODE_FIELDS = ['sample_id', 'crop_name', 'establishment_date', 'peak_date',
                  'harvest_date', 'date_uncertainty_days', 'source_type',
                  'source_reference', 'reviewer', 'notes']


def locations(path):
    found = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        required = {'sample_id', 'longitude', 'latitude', 'district'}
        if required-set(reader.fieldnames or []):
            raise ValueError('Export must include sample_id, longitude, latitude and district')
        for r in reader:
            lon, lat = float(r['longitude']), float(r['latitude'])
            if not math.isfinite(lon+lat) or not (-180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError('Invalid coordinates')
            item = dict(sample_id=r['sample_id'], longitude=lon, latitude=lat, district=r['district'])
            if r['sample_id'] in found and found[r['sample_id']] != item:
                raise ValueError(f"Inconsistent location for {r['sample_id']}")
            found[r['sample_id']] = item
    if not found:
        raise ValueError('No locations')
    return [found[k] for k in sorted(found)]


def spatial_split(lon, lat, seed=2025):
    # Entire 0.1-degree blocks share one role. This is a planning split, not a
    # guarantee of independent fields or a prescribed spatial buffer distance.
    block = f'{math.floor(lon/.1)}_{math.floor(lat/.1)}'
    digest = hashlib.sha256(f'{seed}:{block}'.encode()).hexdigest()
    role = 'evaluation' if int(digest[:8], 16) % 10 < 3 else 'calibration'
    return block, role


def make_package(source, output_dir, year=2025):
    points = locations(source)
    out = Path(output_dir)
    # Do not overwrite previously entered labels or the original package.
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output directory must be empty to protect existing reference labels')
    out.mkdir(parents=True, exist_ok=True)
    with (out/'annual_reference.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=ANNUAL_FIELDS)
        writer.writeheader()
        for p in points:
            writer.writerow({**p, 'year': year})
    with (out/'episode_reference.csv').open('w', newline='') as handle:
        csv.DictWriter(handle, fieldnames=EPISODE_FIELDS).writeheader()
    features = []
    for p in points:
        block, role = spatial_split(p['longitude'], p['latitude'])
        features.append({'type': 'Feature', 'geometry': {'type':'Point',
                         'coordinates':[p['longitude'], p['latitude']]},
                         'properties': {**p, 'year':year, 'spatial_block':block, 'planned_role':role}})
    (out/'sample_locations.geojson').write_text(json.dumps({'type':'FeatureCollection',
                                                          'features':features}, indent=2)+'\n')
    metadata = {'year': year, 'samples': len(points),
                'source_sha256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                'reference_labels_entered':0,
                'planned_split':dict(Counter(f['properties']['planned_role'] for f in features)),
                'spatial_blocks':len({f['properties']['spatial_block'] for f in features}),
                'split_seed':2025, 'block_size_degrees':.1,
                'warning':'No reference labels or accuracy estimates have been generated.'}
    (out/'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    _atlas(points, out/'location_atlas.html', year)
    return metadata


def check_reference(path, year=2025):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader=csv.DictReader(handle)
        if set(ANNUAL_FIELDS)-set(reader.fieldnames or []):
            raise ValueError('Use the annual_reference.csv template')
        rows=list(reader)
    errors=[]; statuses=Counter(); ready=[]; seen=set()
    for i, row in enumerate(rows, start=2):
        sample=row['sample_id']; issues=[]
        if not sample or sample in seen:issues.append('missing_or_duplicate_sample_id')
        seen.add(sample)
        if row['year'] != str(year):issues.append('unexpected_year')
        values=[row[k].strip() for k in ANNUAL_FIELDS[5:]]
        if not any(values) and not issues:
            statuses['unreviewed']+=1
            continue
        if row['reference_land_cover'] not in {'cropland','noncrop','mixed','uncertain'}:
            issues.append('invalid_land_cover')
        if row['annual_review_complete'] not in {'yes','no','uncertain'}:
            issues.append('invalid_review_complete')
        if row['source_type'] not in {'field_record','farmer_record','local_knowledge','independent_imagery','multiple','other'}:
            issues.append('invalid_source_type')
        for key in ['source_reference','source_dates','reviewer','review_date']:
            if not row[key].strip():issues.append('missing_'+key)
        if row['review_date']:
            try:date.fromisoformat(row['review_date'])
            except ValueError:issues.append('invalid_review_date')
        count=None
        if row['reference_cycle_count']:
            try:
                count=int(row['reference_cycle_count'])
                if not 0 <= count <= 6:raise ValueError
            except ValueError:issues.append('invalid_cycle_count')
        if row['annual_review_complete']=='yes' and row['reference_land_cover'] in {'cropland','noncrop'}:
            if count is None:issues.append('complete_review_requires_count')
            if row['reference_land_cover']=='noncrop' and count not in {None,0}:
                issues.append('noncrop_has_positive_crop_count')
        if row['reference_land_cover'] in {'mixed','uncertain'} and count is not None:
            issues.append('mixed_or_uncertain_requires_blank_count')
        if row['annual_review_complete']!='yes' and count is not None:
            issues.append('incomplete_review_requires_blank_count')
        if issues:
            statuses['invalid']+=1
            errors.append({'row':i,'sample_id':sample,'issues':issues})
        elif row['annual_review_complete']=='yes' and count is not None:
            statuses['ready_for_independent_audit']+=1
            ready.append(sample)
        else:statuses['reviewed_but_uncertain']+=1
    return {'year':year,'rows':len(rows),'status_counts':dict(statuses),'errors':errors,
            'ready_sample_ids':ready,'accuracy':None,
            'note':'Structural checks do not verify evidence quality or model accuracy.'}


def _atlas(points, path, year):
    data=json.dumps(points).replace('<','\\u003c')
    template='''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Independent reference locations</title>
<style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:15px;color:#17352d}
main{display:grid;grid-template-columns:1.2fr 1fr;gap:25px}svg{width:100%;border:1px solid #ccd9d2;background:#f2f8f5}circle{cursor:pointer}
select{width:100%;padding:10px}button{padding:8px}p{line-height:1.5}a{color:#12624a}@media(max-width:650px){main{display:block}}</style>
<h1>Barguna __YEAR__: independent reference locations</h1>
<p>All __N__ locations; no model predictions shown. This diagram is a coordinate index,
not a satellite image or land-cover map. Open a location and inspect independently dated
2025 evidence. Current imagery alone cannot establish 2025 crops.</p>
<main><svg id="map" viewBox="0 0 600 600" aria-label="Sample locations"></svg>
<section><label for="sample">Select sample</label><select id="sample"></select>
<h2 id="name"></h2><p id="coords"></p><p id="district"></p>
<p><a id="earth" target="_blank" rel="noopener">Open location in Google Earth</a></p>
<p>The link locates the point; it does not select 2025 imagery. Verify each image's
acquisition date using a historical-imagery source that actually covers the location.</p>
<p>Enter evidence in <a href="annual_reference.csv">annual_reference.csv</a> and
<a href="episode_reference.csv">episode_reference.csv</a>. Leave unknown counts blank.</p>
<button id="copy">Copy coordinates</button><p id="notice"></p>
<p>Do not label from the prototype's candidates. Farmer recall, field records and
image interpretation have different uncertainties: record the source and date.</p></section></main>
<script>
const points=__DATA__;
const select=document.getElementById('sample'),svg=document.getElementById('map');
const xs=points.map(p=>p.longitude),ys=points.map(p=>p.latitude);
const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
points.forEach((p,i)=>{
const option=document.createElement('option');option.value=i;option.textContent=p.sample_id;select.append(option);
const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
c.setAttribute('cx',30+540*(p.longitude-minX)/(maxX-minX||1));
c.setAttribute('cy',570-540*(p.latitude-minY)/(maxY-minY||1));c.setAttribute('r',6);c.dataset.index=i;
c.addEventListener('click',()=>{select.value=i;render()});svg.append(c);
});
function render(){const p=points[Number(select.value)];
document.getElementById('name').textContent=p.sample_id;
document.getElementById('coords').textContent=`Latitude ${p.latitude.toFixed(6)}, longitude ${p.longitude.toFixed(6)}`;
document.getElementById('district').textContent=p.district;
document.getElementById('earth').href='https://earth.google.com/web/search/'+encodeURIComponent(p.latitude+','+p.longitude);
svg.querySelectorAll('circle').forEach(c=>c.setAttribute('fill',Number(c.dataset.index)===Number(select.value)?'#d75c26':'#21744e'));
document.getElementById('notice').textContent='';}
select.addEventListener('change',render);
document.getElementById('copy').addEventListener('click',async()=>{const p=points[Number(select.value)];
try{await navigator.clipboard.writeText(p.latitude+','+p.longitude);document.getElementById('notice').textContent='Copied';}
catch(e){document.getElementById('notice').textContent='Select and copy the coordinates above.'}});
render();</script></html>'''
    path.write_text(template.replace('__YEAR__',str(year)).replace('__N__',str(len(points))).replace('__DATA__',data))
