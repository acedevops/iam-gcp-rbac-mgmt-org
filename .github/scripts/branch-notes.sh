#!/bin/bash

notes_file="branch-notes.md"

function show_help {
  echo "Branch Notes CLI"
  echo ""
  echo "Usage:"
  echo "  $0 add                 Add a new branch note"
  echo "  $0 show <branch>       Show details of a branch"
  echo "  $0 list                List all documented branches"
  echo ""
}

function add_branch {
  read -p "Enter branch name (e.g., feature/login-mfa): " branch
  read -p "Purpose: " purpose
  read -p "Status (e.g., in progress, merged): " status
  read -p "Created by: " created_by
  created_on=$(date +"%Y-%m-%d")
  read -p "Additional notes: " notes

  echo -e "\n## Branch: $branch" >> "$notes_file"
  echo "- Purpose: $purpose" >> "$notes_file"
  echo "- Status: $status" >> "$notes_file"
  echo "- Created by: $created_by" >> "$notes_file"
  echo "- Created on: $created_on" >> "$notes_file"
  echo "- Notes: $notes" >> "$notes_file"

  echo "✅ Branch note added to $notes_file"
}

function show_branch {
  branch="$1"
  if [ -z "$branch" ]; then
    echo "❌ Please provide a branch name"
    exit 1
  fi
  echo "🔍 Looking for notes on branch: $branch"
  echo "----------------------------------------"
  awk -v branch="## Branch: $branch" '
    $0 == branch {print; found=1; next}
    found && /^## Branch:/ {exit}
    found {print}
  ' "$notes_file"
}

function list_branches {
  grep '^## Branch:' "$notes_file" | sed 's/^## Branch: //'
}

# Main logic
case "$1" in
  add)
    add_branch
    ;;
  show)
    show_branch "$2"
    ;;
  list)
    list_branches
    ;;
  *)
    show_help
    ;;
esac
