# Unused Files & Folders

## Current Database State
- **Total art records:** 2 (1 active, 1 inactive)
- **Database references only 1 active file**

## Orphaned Upload Files (safe to delete)

### `static/uploads/shop/thumbs/` 
- **Total files:** 19
- **Referenced in DB:** 1
- **Orphaned:** 18 files (safe to delete)

### `static/uploads/shop/examples/`
- **Total files:** 66  
- **Referenced in DB:** 0
- **All 66 files are orphaned** (safe to delete)

### `static/uploads/shop/owned/`
- **Total files:** 4
- **Referenced in DB:** 0
- **All 4 files are orphaned** (safe to delete)

### `static/uploads/shop/original/`
- **Total files:** 79
- **Referenced in DB:** 0
- **All 79 files are orphaned** (safe to delete)

### `static/uploads/shop/originals/` (Legacy)
- **Total files:** 7
- **Referenced in DB:** 1
- Contains legacy files from old folder structure
- Can be deleted once app is stopped

## Summary
- **Total orphaned files:** ~173 files that are not referenced in the current database
- **Safe to delete:** All files in thumbs/, examples/, owned/, original/, and originals/
- **Recommendation:** Keep only the 1-2 active art files, delete the rest to save space

## Notes
- The app currently uses `ORIG_FOLDER = "original"` (singular) not "originals" (plural)
- Most of these files appear to be from testing and development

