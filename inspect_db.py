import sqlite3

conn = sqlite3.connect("data/aji_tstaji.db")

for table in ["profil", "candidatures", "profils_utilisateurs"]:
    print("\n---", table, "---")
    columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
    print([col[1] for col in columns])
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print("Nombre de lignes :", count)

conn.close()
