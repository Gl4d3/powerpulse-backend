import sqlite3

conn = sqlite3.connect('powerpulse.db')
cursor = conn.cursor()

# Check CSI data in database
cursor.execute('SELECT COUNT(*) FROM daily_analyses WHERE csi_score IS NOT NULL')
csi_count = cursor.fetchone()[0]
print(f'Daily analyses with CSI scores: {csi_count}')

cursor.execute('SELECT COUNT(*) FROM daily_analyses')
total_count = cursor.fetchone()[0]
print(f'Total daily analyses: {total_count}')

if csi_count > 0:
    cursor.execute('SELECT sentiment_score, resolution_achieved, csi_score, effectiveness_score FROM daily_analyses WHERE csi_score IS NOT NULL LIMIT 5')
    print('Sample CSI data:')
    for row in cursor.fetchall():
        print(f'  Sentiment: {row[0]}, Resolution: {row[1]}, CSI: {row[2]}, Effectiveness: {row[3]}')
else:
    print('No actual CSI scores found in database!')

# Check what micro-metrics exist
cursor.execute('SELECT COUNT(*) FROM daily_analyses WHERE sentiment_score IS NOT NULL')
sentiment_count = cursor.fetchone()[0]
print(f'Daily analyses with sentiment scores: {sentiment_count}')

cursor.execute('SELECT COUNT(*) FROM daily_analyses WHERE resolution_achieved IS NOT NULL')
resolution_count = cursor.fetchone()[0]
print(f'Daily analyses with resolution scores: {resolution_count}')

# Check if any real AI analysis has been run
cursor.execute('SELECT * FROM daily_analyses LIMIT 3')
print('\nSample daily_analyses records:')
for row in cursor.fetchall():
    print(f'  ID: {row[0]}, Conv: {row[1]}, Date: {row[2]}, Sentiment: {row[3]}, CSI: {row[-1]}')

conn.close()