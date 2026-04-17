"""Additional Stage 1 analysis for image vs text and Stage 2a."""
import json
import glob

results_dir = r'c:\projects\personal\story-app\tools\rs5\results'
files = glob.glob(results_dir + '/*.json')
rows = []
for f in files:
    d = json.load(open(f))
    if 'scores' not in d or not d['scores']:
        continue
    rows.append({
        'input_id': d['input_id'],
        'input_type': d['input_type'],
        'model': d['model'],
        'prompt': d['prompt_variation'],
        'format': d['output_format'],
        'scene': d['input_id'].replace('text-', ''),
        'score': d['scores']['weighted_score'],
        'door_det': d['scores']['door_detection_rate'],
        'pos_err': d['scores']['door_position_error'],
        'spawn': d['scores']['spawn_plausibility'],
        'zone': d['scores']['zone_coverage'],
        'schema': d['scores']['schema_compliance'],
    })


def avg(lst):
    return sum(lst) / len(lst) if lst else None


def pct(x):
    return f"{x:.0%}" if x is not None else "N/A"


s1 = [r for r in rows if r['prompt'] == 'zero-shot' and r['format'] == 'json']
top3 = ['claude-sonnet-4-20250514', 'gemini-2.5-flash', 'gemini-2.5-pro']

print('=== IMAGE vs TEXT (Stage 1, all models, comparable scenes) ===')
for s in ['outdoor-carriage', 'castle-corridor']:
    img = [r for r in s1 if r['scene'] == s and r['input_type'] == 'image']
    txt = [r for r in s1 if r['scene'] == s and r['input_type'] == 'text']
    ia = avg([r['score'] for r in img])
    ta = avg([r['score'] for r in txt])
    print(f"{s}: img n={len(img)} avg={ia:.3f}  txt n={len(txt)} avg={ta:.3f}  delta={ia-ta:+.3f}")

print()
print('=== IMAGE vs TEXT (Stage 1, TOP 3 only) ===')
for s in ['outdoor-carriage', 'castle-corridor']:
    img = [r for r in s1 if r['scene'] == s and r['input_type'] == 'image' and r['model'] in top3]
    txt = [r for r in s1 if r['scene'] == s and r['input_type'] == 'text' and r['model'] in top3]
    ia = avg([r['score'] for r in img])
    ta = avg([r['score'] for r in txt])
    print(f"{s}: img={ia:.3f} txt={ta:.3f} delta={ia-ta:+.3f}")

print()
print('=== CASTLE THRONE ROOM (image only - no text equivalent) ===')
throne = [r for r in s1 if r['scene'] == 'castle-throne-room']
print(f"castle-throne-room: n={len(throne)} avg={avg([r['score'] for r in throne]):.3f} (image only)")

print()
print('=== CHILDS BEDROOM (text only - no image equivalent) ===')
bedroom = [r for r in s1 if r['scene'] == 'childs-bedroom']
ba = avg([r['score'] for r in bedroom])
print(f"childs-bedroom: n={len(bedroom)} avg={ba:.3f} (text only)")

print()
print('=== STAGE 2a PROMPT VARIATION (top 3, JSON only, all inputs) ===')
for p in ['zero-shot', 'few-shot', 'cot', 'two-pass']:
    ps = [r for r in rows if r['prompt'] == p and r['format'] == 'json' and r['model'] in top3]
    if not ps:
        continue
    sc = avg([r['score'] for r in ps])
    sh = avg([r['schema'] for r in ps])
    dd = avg([r['door_det'] for r in ps])
    print(f"{p}: n={len(ps)} score={sc:.3f} schema={pct(sh)} door={dd:.3f}")

print()
print('=== STAGE 2a PROMPT VARIATION (top 3, image only) ===')
for p in ['zero-shot', 'few-shot', 'cot', 'two-pass']:
    ps = [r for r in rows if r['prompt'] == p and r['format'] == 'json' and r['model'] in top3 and r['input_type'] == 'image']
    if not ps:
        continue
    sc = avg([r['score'] for r in ps])
    sh = avg([r['schema'] for r in ps])
    dd = avg([r['door_det'] for r in ps])
    print(f"  {p}: n={len(ps)} score={sc:.3f} schema={pct(sh)} door={dd:.3f}")

print()
print('=== CASTLE THRONE ROOM per model (image, Stage 1) ===')
for m in top3:
    mr = [r for r in s1 if r['model'] == m and r['scene'] == 'castle-throne-room' and r['input_type'] == 'image']
    if mr:
        sc = avg([r['score'] for r in mr])
        sh = avg([r['schema'] for r in mr])
        dd = avg([r['door_det'] for r in mr])
        print(f"  {m}: score={sc:.3f} schema={pct(sh)} door={dd:.3f}")
