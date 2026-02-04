# Unused Files & Folders

## Unused Upload Folders
- `static/uploads/shop/originals/` - Legacy folder (app uses `original/` instead)
  - Contains 7 files, only 1 is referenced in database
  - Can be safely deleted once the Flask app is stopped

## Notes
- The app uses `ORIG_FOLDER = "original"` (singular) not "originals" (plural)
- All current uploads go to the `original/` folder with 79 files
