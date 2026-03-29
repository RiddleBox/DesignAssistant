"""给所有 yaml 文档加 industry: gaming 字段（如果还没有的话）"""
import yaml, os, re

doc_dir = os.path.join(os.path.dirname(__file__), 'data', 'documents')
added, skipped = [], []

for fname in sorted(os.listdir(doc_dir)):
    if not fname.endswith('.yaml'):
        continue
    path = os.path.join(doc_dir, fname)
    with open(path, encoding='utf-8') as f:
        raw = f.read()
        d = yaml.safe_load(raw)

    if 'industry' in d:
        skipped.append(fname)
        continue

    # 在 category 行之前插入 industry 行
    lines = raw.splitlines()
    new_lines = []
    inserted = False
    for line in lines:
        if re.match(r'^category\s*:', line) and not inserted:
            new_lines.append('industry: gaming')
            inserted = True
        new_lines.append(line)

    if not inserted:
        # fallback：插到文件末尾
        new_lines.append('industry: gaming')

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines) + '\n')
    added.append(fname)

print(f'已添加 industry: gaming：{len(added)} 个文件')
print(f'已跳过（已有 industry 字段）：{len(skipped)} 个文件')
