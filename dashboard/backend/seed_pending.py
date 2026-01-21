
import requests
import random

BASE_URL = "http://localhost:8000/api/admin"

def seed_data():
    # Seed Replace Words
    for i in range(5):
        data = {
            "source_word": f"seed_replace_sourrce_{i}_{random.randint(1000,9999)}",
            "target_word": f"seed_replace_target_{i}"
        }
        try:
            # We don't have a direct "add pending word" endpoint exposed easily for admin from previous file view
            # The discover_new_words DAG writes to DB.
            # But we can use `add-replace-word` or similar? No that adds to PROTECTED or APPROVED list.
            # We need to insert into PENDING.
            # `admin_words.py` doesn't have "create pending".
            pass
        except Exception as e:
            print(e)
            
    # Since I cannot easily hit an endpoint to creating PENDING words (only approve/reject/add-approved),
    # I might have to rely on the fact that the user might have some data, or I need to insert into DB directly.
    # OR I can mock the response in browser? No, I need to test the "Clear All" button.
    
    # Wait, `add-replace-word` adds to `ReplaceWord` (approved).
    # `pending` comes from ETL.
    
    # I will try to use the `POST /api/test/seed-pending` if it exists? Probably not.
    # I will construct a SQL insert command via `psql` if possible, or just hopefully there is data.
    # If not, I'll have to create a temporary script to insert into DB using sqlalchemy.
    pass

if __name__ == "__main__":
    print("Please use the following SQL to seed data if needed:")
    print("INSERT INTO pending_replace_words (source_word, target_word, confidence_score, status) VALUES ('test_src', 'test_tgt', 0.9, 'pending');")
