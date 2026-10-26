"""Recheck unresolved grain candidates without rebuilding or changing source data."""
from datetime import datetime, timezone
import json
import sqlite3
from .build import SOURCE, TARGET, connect, js, profile


def refine():
    src = connect(SOURCE)
    out = sqlite3.connect(TARGET)
    out.row_factory = sqlite3.Row
    unresolved = list(out.execute("SELECT * FROM tables WHERE json_extract(profile_json,'$.key_status')='unresolved'"))
    results = []
    for row in unresolved:
        path = src.execute('SELECT sqlite_path FROM physical_tables WHERE release_id=? AND table_name=? COLLATE NOCASE',
                           (row['release_id'],row['table_name'])).fetchone()[0]
        db = connect(path)
        columns = [r[0].upper() for r in src.execute('SELECT column_name FROM physical_columns WHERE release_id=? AND table_name=? COLLATE NOCASE',
                                                   (row['release_id'],row['table_name']))]
        result = profile(db,row['table_name'],columns,json.loads(row['dimension_fields_json']),row['row_count'],candidate_seconds=60)
        db.close()
        out.execute('UPDATE tables SET profile_json=? WHERE release_id=? AND table_name=?',
                    (js(result),row['release_id'],row['table_name']))
        out.execute("UPDATE review_queue SET details_json=? WHERE release_id=? AND table_name=? AND category='record_grain_review'",
                    (js(result),row['release_id'],row['table_name']))
        for column in ['CGUNITID','CAMPUSID','OLDUNITID']:
            out.execute("UPDATE fields SET role='entity_identifier' WHERE release_id=? AND table_name=? AND column_name=? AND definition_status='exact_definition'",
                        (row['release_id'],row['table_name'],column))
        results.append({'release':row['release_id'],'table':row['table_name'],**result})
        print(row['release_id'],row['table_name'],result['key_status'],flush=True)
    out.execute('INSERT OR REPLACE INTO build_info VALUES(?,?)',
                ('grain_refinement',js({'at':datetime.now(timezone.utc).isoformat(),'tables':len(results),
                                        'remaining_unresolved':sum(r['key_status']=='unresolved' for r in results)})))
    out.commit()
    out.close()
    src.close()


if __name__=='__main__':
    refine()
