from pathlib import Path

import uvicorn


def ensure_data_folder():
    home_dir = Path.home()
    data_folder = home_dir / "transcom-hackathons-data"

    print(f"Because user-uploaded files need to be saved, we need a data folder at: {data_folder}")

    if data_folder.exists():
        if data_folder.is_dir():
            print(f"Detected that the folder {data_folder} already exists. No need to create.")
        else:
            print(f"Error: {data_folder} exists but is not a folder!")
            raise FileExistsError(f"{data_folder} exists and is not a directory.")
    else:
        data_folder.mkdir(exist_ok=True)
        print("Folder {data_folder} created successfully.")


if __name__ == "__main__":
    # ensure_data_folder()
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
