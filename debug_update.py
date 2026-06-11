import sqlite3

conn = sqlite3.connect('pietro.db')
cursor = conn.cursor()

# Get all items with their names
cursor.execute("SELECT id, name, photo FROM items WHERE name LIKE '%Sewing%'")
rows = cursor.fetchall()
print("Found items:")
for r in rows:
    print(f"ID: {r[0]}, Name: '{r[1]}' (len={len(r[1])}), Photo: {r[2]}")

# Now update using the exact name found
if rows:
    exact_name = rows[0][1]
    cursor.execute("UPDATE items SET photo=? WHERE name=?", ("pngegg (2).png", exact_name))
    conn.commit()
    
    # Verify
    cursor.execute("SELECT name, photo FROM items WHERE name=?", (exact_name,))
    result = cursor.fetchone()
    print(f"\nUpdated: {result[0]} -> {result[1]}")

conn.close()
