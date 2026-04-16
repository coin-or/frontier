#!/usr/bin/env python3
import json

with open('dev_temp/eval/run_001/base/frontier/results.json') as f:
    fd = json.load(f)
with open('dev_temp/eval/run_001/base/solver/results.json') as f:
    sd = json.load(f)
with open('dev_temp/eval/run_001/base/llm/results.json') as f:
    ld = json.load(f)

targets = [4, 6, 8, 10, 12, 14, 18]
for t in targets:
    fb = min(fd['base']['solutions'], key=lambda s: abs(s['return_pct']-t))
    sb = min(sd['base']['solutions'], key=lambda s: abs(s['return_pct']-t))
    lb = min(ld['base']['solutions'], key=lambda s: abs(s['return_pct']-t))
    fc = f'{fb["volatility_pct"]:.1f}' if abs(fb['return_pct']-t)<=1.0 else '---'
    sc = f'{sb["volatility_pct"]:.1f}' if abs(sb['return_pct']-t)<=1.0 else '---'
    lc = f'{lb["volatility_pct"]:.1f}' if abs(lb['return_pct']-t)<=1.0 else '---'
    print(f'{t}pct: F={fc} S={sc} L={lc}')
