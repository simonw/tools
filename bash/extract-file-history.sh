#!/usr/bin/env bash
#
# extract-file-history.sh
#
# Copy the full Git history of a single file into a brand-new repository.
#
# Usage:
#   ./extract-file-history.sh <source_repo_path> <target_file_path> <new_repo_name> [output_filename]
# Example:
#   ./extract-file-history.sh ~/projects/my-project src/utils/helper.js helper-history helper.js
#
# The new repository will contain one commit for every change ever made to the
# specified file, preserving author, date and original commit message. If
# output_filename is provided, the file in the new repo will be named accordingly.

set -euo pipefail

###############################################################################
# 1. Validate arguments & environment
###############################################################################
if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
  echo "Usage: $0 <source_repo_path> <target_file_path> <new_repo_name> [output_filename]"
  exit 1
fi

SOURCE_REPO=$1          # e.g. /path/to/original/repo
TARGET_FILE=$2          # e.g. src/utils/helper.js
NEW_REPO_NAME=$3        # e.g. helper-history

# Determine output filename in new repo
if [ "$#" -eq 4 ]; then
  OUTPUT_FILENAME=$4
else
  OUTPUT_FILENAME=$(basename "$TARGET_FILE")
fi

# Ensure Git is installed
command -v git >/dev/null 2>&1 || {
  echo "Error: Git is not installed. Please install Git and try again."
  exit 1
}

# Ensure SOURCE_REPO is a Git repository
if [ ! -d "$SOURCE_REPO/.git" ]; then
  echo "Error: $SOURCE_REPO is not a Git repository."
  exit 1
fi

# Ensure TARGET_FILE exists *somewhere* in the repo history
if ! git -C "$SOURCE_REPO" ls-files --error-unmatch -- "$TARGET_FILE" >/dev/null 2>&1; then
  echo "Error: $TARGET_FILE does not exist in $SOURCE_REPO (at HEAD)."
  exit 1
fi

###############################################################################
# 2. Create the new repository
###############################################################################
echo "Creating new repository: ${NEW_REPO_NAME}..."
mkdir -p "${NEW_REPO_NAME}"
cd "${NEW_REPO_NAME}"
git init -q

###############################################################################
# 3. Iterate over commits that touched the file (oldest → newest)
###############################################################################
echo "Retrieving commit list for ${TARGET_FILE}..."
COMMITS=$(git -C "$SOURCE_REPO" log --follow --reverse --pretty=%H -- "$TARGET_FILE")

TOTAL=0
for COMMIT in $COMMITS; do
  # Extract metadata (author, email, date) and commit message
  AUTHOR_NAME=$(git -C "$SOURCE_REPO" show -s --format=%an "$COMMIT")
  AUTHOR_EMAIL=$(git -C "$SOURCE_REPO" show -s --format=%ae "$COMMIT")
  COMMIT_DATE=$(git -C "$SOURCE_REPO" show -s --format=%ad "$COMMIT")
  COMMIT_MSG=$(git -C "$SOURCE_REPO" show -s --format=%B "$COMMIT")

  printf 'Importing %s ...\n' "$(git -C "$SOURCE_REPO" rev-parse --short "$COMMIT")"

  # Write the file content for that commit into the new repo
  if ! git -C "$SOURCE_REPO" show "$COMMIT":"$TARGET_FILE" > "$OUTPUT_FILENAME" 2>/dev/null; then
    echo "Warning: could not extract ${TARGET_FILE} at ${COMMIT} – skipping."
    continue
  fi

  git add "$OUTPUT_FILENAME"

  # Re-create the commit with original metadata
  GIT_AUTHOR_NAME="$AUTHOR_NAME" \
  GIT_AUTHOR_EMAIL="$AUTHOR_EMAIL" \
  GIT_AUTHOR_DATE="$COMMIT_DATE" \
  GIT_COMMITTER_NAME="$AUTHOR_NAME" \
  GIT_COMMITTER_EMAIL="$AUTHOR_EMAIL" \
  GIT_COMMITTER_DATE="$COMMIT_DATE" \
    git commit -q -m "$COMMIT_MSG"

  TOTAL=$((TOTAL + 1))
done

###############################################################################
# 4. Done!
###############################################################################
echo "Done! New repository '${NEW_REPO_NAME}' contains ${TOTAL} commit(s) of '${TARGET_FILE}' as '${OUTPUT_FILENAME}'."

