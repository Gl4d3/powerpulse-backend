import sqlite3

conn = sqlite3.connect('powerpulse.db')
cursor = conn.cursor()

print("Conversations table columns:")
cursor.execute('PRAGMA table_info(conversations)')
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")

print("\nMessages table columns:")
cursor.execute('PRAGMA table_info(messages)')
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")

# Get sample data to understand structure
print("\nSample conversations:")
cursor.execute('SELECT * FROM conversations LIMIT 3')
for row in cursor.fetchall():
    print(f"  {row}")

print("\nSample messages:")
cursor.execute('SELECT * FROM messages LIMIT 3')
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()