import prestodb
conn = prestodb.dbapi.connect(
    host='prestodb.develop.bhuma.dev',
    port=443,
    user='root',
    catalog='tpcds',
    schema='sf10',
    http_scheme='https',
    auth=prestodb.auth.BasicAuthentication("root", ""),
)
cur = conn.cursor()
cur.execute('SELECT cc_call_center_id, cc_name FROM tpcds.sf10.call_center')
rows = cur.fetchall()
print(rows)
