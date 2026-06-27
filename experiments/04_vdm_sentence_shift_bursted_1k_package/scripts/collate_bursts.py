#!/usr/bin/env python3
import csv,json,shutil,sys
from pathlib import Path
root=Path(sys.argv[1])
out=Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
bursts=sorted([p for p in root.iterdir() if p.is_dir() and (p/'tick_rows.csv').exists()], key=lambda p:int(p.name.split('_')[1]))
# copy final h5
if bursts:
    last=bursts[-1]
    for h5 in sorted(last.glob('state_*.h5')):
        shutil.copy2(h5, out/h5.name)
# combine csv
header=None
with open(out/'tick_rows.csv','w',newline='',encoding='utf-8') as fo:
    writer=None
    for b in bursts:
        with open(b/'tick_rows.csv', newline='', encoding='utf-8') as fi:
            r=csv.DictReader(fi)
            if writer is None:
                header=r.fieldnames; writer=csv.DictWriter(fo, fieldnames=header); writer.writeheader()
            for row in r: writer.writerow(row)
for name in ['trace_log.jsonl','utd_events.jsonl','ute_input_stream.jsonl']:
    with open(out/name,'w',encoding='utf-8') as fo:
        for b in bursts:
            p=b/name
            if p.exists():
                fo.write(p.read_text(encoding='utf-8'))
# combine burst summaries
summ=[]
for b in bursts:
    for p in b.glob('burst_*.json'):
        try: summ.append(json.loads(p.read_text()))
        except Exception: pass
summ=sorted(summ, key=lambda x:x.get('start_tick',0))
(out/'burst_summaries.json').write_text(json.dumps(summ,indent=2),encoding='utf-8')
# copy group map/config
for b in bursts[:1]:
    for name in ['run_config.json','selector_group_map.json']:
        p=b/name
        if p.exists(): shutil.copy2(p,out/name)
print(json.dumps({'bursts':len(bursts),'rows':sum(s.get('rows_written',0) for s in summ),'final_h5':str(out/(f"state_{summ[-1]['end_tick']}.h5" if summ else '')),'all_h5_ok':all(s.get('h5_reload_signature_ok') for s in summ)},indent=2))
