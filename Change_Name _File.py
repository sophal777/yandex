import os

FOLDER_PATH = r"downloads"

files = sorted(os.listdir(FOLDER_PATH))

index = 1

for old_name in files:
    old_path = os.path.join(FOLDER_PATH, old_name)

    if not os.path.isfile(old_path):
        continue

    extension = os.path.splitext(old_name)[1]
    new_name = f"SH{index:03d}{extension}"
    new_path = os.path.join(FOLDER_PATH, new_name)

    if os.path.exists(new_path):
        print(f"Skip: {new_name}")
        continue

    os.rename(old_path, new_path)
    print(f"{old_name}  →  {new_name}")

    index += 1

print("Rename completed!")
