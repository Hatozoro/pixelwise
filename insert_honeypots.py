import psycopg2
import numpy as np
from sklearn.datasets import fetch_openml

print("Lade MNIST-Daten...")
mnist = fetch_openml('mnist_784', version=1, as_frame=False, parser='auto')
X, y = mnist.data, mnist.target.astype(int)

conn = psycopg2.connect(dbname="pixelwise", user="pixelwise", password="pixelwise", host="localhost")

def insert_honeypot(pixels, expected_label):
    pixel_string = ",".join(str(int(p)) for p in pixels)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO jury_tasks (creator, predicted_label, target_label, pixels, status, is_honeypot, expected_label)
            VALUES ('SYSTEM', %s, %s, %s, 'pending', TRUE, %s)
        """, (expected_label, expected_label, pixel_string, expected_label))

print("Füge 20 saubere Honeypots ein (je 2 pro Ziffer 0-9)...")
for digit in range(10):
    indices = np.where(y == digit)[0][:2]
    for idx in indices:
        insert_honeypot(X[idx], digit)

print("Füge 5 Rausch-Honeypots ein (expected_label = -1 = Troll)...")
for _ in range(5):
    noise = np.random.randint(0, 50, 784).astype(float)
    insert_honeypot(noise, -1)

conn.commit()
conn.close()
print("Fertig! 25 Honeypots eingefügt.")
