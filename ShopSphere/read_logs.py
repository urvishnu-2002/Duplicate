try:
    with open('error_log.txt', 'r', encoding='utf-16le') as f:
        print("--- error_log.txt (last 20 lines) ---")
        lines = f.readlines()
        for line in lines[-20:]:
            print(line.strip())
except Exception as e:
    print(f"Error reading error_log.txt: {e}")

try:
    with open('error_details.txt', 'r', encoding='utf-16le') as f:
        print("\n--- error_details.txt (last 20 lines) ---")
        lines = f.readlines()
        for line in lines[-20:]:
            print(line.strip())
except Exception as e:
    print(f"Error reading error_details.txt: {e}")
