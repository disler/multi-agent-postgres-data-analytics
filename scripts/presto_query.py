import prestodb
connection = prestodb.dbapi.connect(
    host='prestodb.develop.bhuma.dev',
    port=443,
    user='root',
    catalog='tpcds',
    schema='sf10',
    http_scheme='https',
    auth=prestodb.auth.BasicAuthentication("root", ""),
)
cursor = connection.cursor()
cursor.execute('SELECT cc_call_center_id, cc_name FROM tpcds.sf10.call_center')
rows = cursor.fetchall()
print(rows)
