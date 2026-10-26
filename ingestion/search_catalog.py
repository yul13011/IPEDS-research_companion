"""Read-only keyword discovery of source metadata; no agent or measure mapping."""
from pathlib import Path
import argparse,json,sqlite3
CATALOG=Path(__file__).resolve().parents[1]/'data'/'metadata_catalog.sqlite'
def search(query,release=None,kind=None,limit=10):
    if not 1<=limit<=100:raise ValueError('Limit must be between 1 and 100')
    db=sqlite3.connect('file:'+CATALOG.as_posix()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    try:
        conditions=['search_index MATCH ?'];params=[query]
        if release:conditions.append('r.release_id LIKE ?');params.append('%'+release+'%')
        if kind:conditions.append('r.kind=?');params.append(kind)
        params.append(limit)
        rows=db.execute('''SELECT r.record_id,r.release_id,r.kind,r.table_name,r.variable_name,r.title,
          snippet(search_index,5,'[',']',' ... ',36) AS excerpt,f.path AS source_file,s.sheet_name,r.source_row
          FROM search_index JOIN records r ON r.record_id=search_index.record_id
          JOIN source_files f ON f.source_id=r.source_id LEFT JOIN sheets s ON s.sheet_id=r.sheet_id
          WHERE '''+' AND '.join(conditions)+''' ORDER BY bm25(search_index),r.record_id LIMIT ?''',params).fetchall()
        result=[]
        for row in rows:
            item=dict(row)
            item['issues']=[dict(x) for x in db.execute('SELECT issue_type,severity,description,candidate_locations_json,status FROM issues WHERE source_record_id=?',(row['record_id'],))]
            for issue in item['issues']:
                issue['candidate_locations']=json.loads(issue.pop('candidate_locations_json'))
            if row['table_name']:
                reconciled=bool(db.execute('SELECT 1 FROM physical_tables WHERE release_id=?',(row['release_id'],)).fetchone())
                item['physical_table_present']=bool(db.execute('SELECT 1 FROM physical_tables WHERE release_id=? AND table_name=? COLLATE NOCASE',(row['release_id'],row['table_name'])).fetchone()) if reconciled else None
                if row['variable_name']:
                    item['documented_column_present']=bool(db.execute('SELECT 1 FROM physical_columns WHERE release_id=? AND table_name=? COLLATE NOCASE AND column_name=? COLLATE NOCASE',(row['release_id'],row['table_name'],row['variable_name'])).fetchone()) if reconciled else None
            result.append(item)
        return result
    finally:db.close()
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('query',help='SQLite FTS5 expression; quote phrases or use AND/OR');parser.add_argument('--release');parser.add_argument('--kind',choices=['table_definition','variable_definition','code_value','release_note','supplementary_change','metadata_definition','introduction','other_documentation']);parser.add_argument('--limit',type=int,default=10)
    args=parser.parse_args()
    print(json.dumps(search(args.query,args.release,args.kind,args.limit),indent=2,ensure_ascii=False))
