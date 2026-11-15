class Logger:
    def __init__(self):
        self.successful_renames = 0
        self.saved_metadata = 0

    def increment_successful_renames(self):
        self.successful_renames += 1

    def increment_saved_metadata(self):
        self.saved_metadata += 1

    def log_folders(self, folders, root_folder):
        if folders:
            print(f"Found {len(folders)} folders in {root_folder}")
            for folder in folders:
                print(f" - {folder}")
        else:
            print("No folders found to rename.")

    def print_completion_status(self, metadata_path: str):
        print(f"\nCompleted: {self.successful_renames} folders renamed successfully.")
        if self.saved_metadata:
            print(f"Saved metadata for {self.saved_metadata} series to {metadata_path}")
