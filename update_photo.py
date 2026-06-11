import sqlite3

conn = sqlite3.connect('pietro.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Update sewing machine photo
cursor.execute("UPDATE items SET photo=? WHERE name=?", 
               ("pngegg (2).png", "Sewing machine  "))
conn.commit()

# Verify update
cursor.execute("SELECT name, photo FROM items WHERE name=?", ("Sewing machine  ",))
result = cursor.fetchone()
if result:
    print(f"Updated: {result['name']} -> {result['photo']}")
else:
    print("Item not found")

conn.close()
