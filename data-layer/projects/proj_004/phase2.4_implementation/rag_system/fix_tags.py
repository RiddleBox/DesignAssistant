"""修复 kb_044~kb_062 中 tags 里混入 content_type 值的问题"""
import yaml, os, re

CONTENT_TYPE_VALUES = {'glossary', 'few_shot_example', 'constraint_rule',
                       'case_record', 'market_data', 'background'}
doc_dir = os.path.join(os.path.dirname(__file__), 'data', 'documents')
fixed = []

for fname in sorted(os.listdir(doc_dir)):
    if not fname.endswith('.yaml'):
        continue
    path = os.path.join(doc_dir, fname)
    with open(path, encoding='utf-8') as f:
        raw = f.read()
        d = yaml.safe_load(raw)

    tags = d.get('tags', []) or []
    bad = [t for t in tags if t in CONTENT_TYPE_VALUES]
    if not bad:
        continue

    clean_tags = [t for t in tags if t not in CONTENT_TYPE_VALUES]

    # 精准替换 tags 行（支持单行 inline list 格式）
    lines = raw.splitlines()
    new_lines = []
    skip_list = False
    for line in lines:
        if re.match(r'^tags\s*:', line):
            tag_str = ', '.join(f'"{t}"' for t in clean_tags)
            new_lines.append(f'tags: [{tag_str}]')
            skip_list = line.strip() == 'tags:'   # 原来是多行列表
            continue
        if skip_list:
            if re.match(r'^\s*-\s+', line):
                continue
            else:
                skip_list = False
        new_lines.append(line)

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines) + '\n')
    fixed.append((fname, bad, clean_tags))
    print(f'  [fixed] {fname}: removed {bad}  ->  tags={clean_tags}')

print(f'\n共修复 {len(fixed)} 个文件')
