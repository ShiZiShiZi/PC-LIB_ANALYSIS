import json
r = json.load(open('runs/pc-lib-3456/mpg123/2026-07-11T00-16-51-712Z/report.json', 'r', encoding='utf-8'))
warnings = r['meta'].get('harmony_warnings', [])
print(f'Harmony warnings: {len(warnings)}')
for w in warnings:
    print(f"  [{w['class']}] {w['code']}: {w['message']}")
    
# Check key properties
print(f'\nporting_class: {r["harmony_adaptation"]["porting_class"]}')
print(f'effort_level: {r["harmony_adaptation"]["effort"]["level"]}')
print(f'adaptation_assessment: {r["harmony_adaptation"]["adaptation_assessment"]["effective_class"]}')
print(f'overall: {r["harmony_adaptation"]["adaptation_assessment"]["overall"]}')
