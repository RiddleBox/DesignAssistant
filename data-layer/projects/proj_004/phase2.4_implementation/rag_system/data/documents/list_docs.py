import yaml, glob
docs = sorted(glob.glob('*.yaml'))
for f in docs:
    with open(f, encoding='utf-8') as fh:
        d = yaml.safe_load(fh)
    doc_id = d.get('id','')
    cat = d.get('category','')
    title = d.get('title','')[:55]
    tags = d.get('tags', [])
    print(f"{doc_id:<10} [{cat:<20}] {title:<55} tags={tags}")
