"""Targeted Stage 1 analysis for RS-5 section population."""
import json
import os
import glob

results_dir = r'c:\projects\personal\story-app\tools\rs5\results'
files = glob.glob(os.path.join(results_dir, '*.json'))

rows = []
for f in files:
    with open(f) as fh:
        d = json.load(fh)
    if 'scores' not in d or d['scores'] is None:
        continue
    rows.append({
        'input_id': d['input_id'],
        'input_type': d['input_type'],
        'model': d['model'],
        'prompt': d['prompt_variation'],
        'format': d['output_format'],
        'scene': d['input_id'].replace('text-', ''),
        'door_det': d['scores']['door_detection_rate'],
        'pos_err': d['scores']['door_position_error'],
        'spawn': d['scores']['spawn_plausibility'],
        'zone': d['scores']['zone_coverage'],
        'schema': d['scores']['schema_compliance'],
        'consist': d['scores']['consistency'],
        'score': d['scores']['weighted_score'],
        'cost': d.get('cost_estimate', 0),
        'latency_ms': d.get('latency_ms', 0),
        'provider': d.get('provider', ''),
    })


def avg(lst):
    return sum(lst) / len(lst) if lst else 0


MODELS = [
    'claude-sonnet-4-20250514',
    'gemini-2.5-flash',
    'gemini-2.5-pro',
    'qwen/qwen3-vl-4b',
    'google/gemma-4-e2b',
    'google/gemma-3-4b',
    'qwen2.5-vl-3b-instruct',
]
SCENES = ['outdoor-carriage', 'castle-corridor', 'castle-throne-room']
PROVIDER_MAP = {
    'claude-sonnet-4-20250514': 'Anthropic',
    'gemini-2.5-flash': 'Google',
    'gemini-2.5-pro': 'Google',
    'qwen/qwen3-vl-4b': 'Local',
    'google/gemma-4-e2b': 'Local',
    'google/gemma-3-4b': 'Local',
    'qwen2.5-vl-3b-instruct': 'Local',
}

# Stage 1: zero-shot json only
s1 = [r for r in rows if r['prompt'] == 'zero-shot' and r['format'] == 'json']

print('=== STAGE 1: IMAGE INPUT (per model, averaged across image scenes) ===')
print('Model | Provider | Avg Score | Door Det | Pos Err | Spawn | Zone | Schema | Latency | Cost')
for m in MODELS:
    mr = [r for r in s1 if r['model'] == m and r['input_type'] == 'image']
    if not mr:
        continue
    sc = avg([r['score'] for r in mr])
    dd = avg([r['door_det'] for r in mr])
    pe = avg([r['pos_err'] for r in mr])
    sp = avg([r['spawn'] for r in mr])
    zo = avg([r['zone'] for r in mr])
    sh = avg([r['schema'] for r in mr])
    lat = avg([r['latency_ms'] for r in mr]) / 1000
    co = avg([r['cost'] for r in mr])
    print(f'{m} | {PROVIDER_MAP[m]} | {sc:.3f} | {dd:.3f} | {pe:.3f} | {sp:.3f} | {zo:.3f} | {sh:.0%} | {lat:.1f}s | ${co:.4f}')

print()
print('=== STAGE 1: TEXT INPUT (per model, averaged across text scenes) ===')
for m in MODELS:
    mr = [r for r in s1 if r['model'] == m and r['input_type'] == 'text']
    if not mr:
        continue
    sc = avg([r['score'] for r in mr])
    dd = avg([r['door_det'] for r in mr])
    pe = avg([r['pos_err'] for r in mr])
    sp = avg([r['spawn'] for r in mr])
    zo = avg([r['zone'] for r in mr])
    sh = avg([r['schema'] for r in mr])
    lat = avg([r['latency_ms'] for r in mr]) / 1000
    co = avg([r['cost'] for r in mr])
    print(f'{m} | {PROVIDER_MAP[m]} | {sc:.3f} | {dd:.3f} | {pe:.3f} | {sp:.3f} | {zo:.3f} | {sh:.0%} | {lat:.1f}s | ${co:.4f}')

print()
print('=== STAGE 1: PER-SCENE IMAGE (top 3 models) ===')
for m in MODELS[:3]:
    for s in SCENES:
        mr = [r for r in s1 if r['model'] == m and r['scene'] == s and r['input_type'] == 'image']
        if not mr:
            continue
        sc = avg([r['score'] for r in mr])
        dd = avg([r['door_det'] for r in mr])
        pe = avg([r['pos_err'] for r in mr])
        sp = avg([r['spawn'] for r in mr])
        zo = avg([r['zone'] for r in mr])
        sh = avg([r['schema'] for r in mr])
        co = avg([r['cost'] for r in mr])
        print(f'{m} | {s} | {sc:.3f} | {dd:.3f} | {pe:.3f} | {sp:.3f} | {zo:.3f} | {sh:.0%} | ${co:.4f}')

print()
print('=== STAGE 1: PER-SCENE TEXT (top 3 models) ===')
for m in MODELS[:3]:
    for s in SCENES:
        mr = [r for r in s1 if r['model'] == m and r['scene'] == s and r['input_type'] == 'text']
        if not mr:
            continue
        sc = avg([r['score'] for r in mr])
        dd = avg([r['door_det'] for r in mr])
        pe = avg([r['pos_err'] for r in mr])
        sp = avg([r['spawn'] for r in mr])
        zo = avg([r['zone'] for r in mr])
        sh = avg([r['schema'] for r in mr])
        co = avg([r['cost'] for r in mr])
        print(f'{m} | {s} | {sc:.3f} | {dd:.3f} | {pe:.3f} | {sp:.3f} | {zo:.3f} | {sh:.0%} | ${co:.4f}')

print()
print('=== STAGE 2a: PROMPT VARIATION (top 3, zero-shot baseline from Stage 1) ===')
# Stage 2a: top 3 models, json format only
s2a_models = MODELS[:3]
s2a = [r for r in rows if r['model'] in s2a_models and r['format'] == 'json']
prompts = ['zero-shot', 'few-shot', 'cot', 'two-pass']
zero_shot_avg = avg([r['score'] for r in s2a if r['prompt'] == 'zero-shot'])
print(f'Zero-shot baseline (Stage 1, top-3, JSON): {zero_shot_avg:.3f}')
for p in prompts[1:]:
    pr = [r for r in s2a if r['prompt'] == p]
    if not pr:
        continue
    sc = avg([r['score'] for r in pr])
    dd = avg([r['door_det'] for r in pr])
    pe = avg([r['pos_err'] for r in pr])
    sp = avg([r['spawn'] for r in pr])
    sh = avg([r['schema'] for r in pr])
    co = avg([r['consist'] for r in pr])
    print(f'{p}: score={sc:.3f} delta={sc-zero_shot_avg:+.3f} door={dd:.3f} pos={pe:.3f} schema={sh:.0%}')

print()
print('=== STAGE 2b: JSON vs SVG (top 3 models, 3 image scenes, few-shot) ===')
# Note: image-only for Stage 2b  
for fmt in ['json', 'svg']:
    fr = [r for r in rows if r['format'] == fmt and r['prompt'] == 'few-shot' and r['input_type'] == 'image' and r['model'] in s2a_models]
    if not fr:
        continue
    sc = avg([r['score'] for r in fr])
    sh = avg([r['schema'] for r in fr])
    pe = avg([r['pos_err'] for r in fr])
    dd = avg([r['door_det'] for r in fr])
    print(f'{fmt.upper()}: score={sc:.3f} schema={sh:.0%} pos_acc={pe:.3f} door_det={dd:.3f} n={len(fr)}')

print()
print('=== IMAGE vs TEXT (Stage 1, per scene) ===')
for s in SCENES:
    img = [r for r in s1 if r['scene'] == s and r['input_type'] == 'image']
    txt = [r for r in s1 if r['scene'] == s and r['input_type'] == 'text']
    if img and txt:
        ia = avg([r['score'] for r in img])
        ta = avg([r['score'] for r in txt])
        print(f'{s}: image={ia:.3f} text={ta:.3f} delta={ia-ta:+.3f}')

print()
print('=== LOCAL VLM STAGE 1 SUMMARY ===')
local_models = MODELS[3:]
for m in local_models:
    mr = [r for r in s1 if r['model'] == m]
    if not mr:
        continue
    sc = avg([r['score'] for r in mr])
    sh = avg([r['schema'] for r in mr])
    lat = avg([r['latency_ms'] for r in mr]) / 1000
    print(f'{m}: score={sc:.3f} schema={sh:.0%} latency={lat:.1f}s')

print()
print('=== PROMPT PORTABILITY (zero-shot vs few-shot per top-3 model, JSON only) ===')
for m in s2a_models:
    z = [r for r in rows if r['model'] == m and r['prompt'] == 'zero-shot' and r['format'] == 'json']
    f = [r for r in rows if r['model'] == m and r['prompt'] == 'few-shot' and r['format'] == 'json']
    if z and f:
        za = avg([r['score'] for r in z])
        fa = avg([r['score'] for r in f])
        print(f'{m}: zero-shot={za:.3f} few-shot={fa:.3f} delta={fa-za:+.3f}')
