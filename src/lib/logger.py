class Logger:
    def __init__(self):
        self.successful_renames = 0

    def increment_successful_renames(self):
        self.successful_renames += 1

    def log_folders(self, folders, root_folder):
        if folders:
            print(f"Found {len(folders)} folders in {root_folder}")
            for folder in folders:
                print(f" - {folder}")
        else:
            print("No folders found to rename.")

    def print_completion_status(self):
        print(f"\nCompleted: {self.successful_renames} folders renamed successfully.")
