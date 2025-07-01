#!/bin/bash

# Bump the version in the pyproject.toml file
# Note: uv doesn't have a built-in version bump command, so we'll use a Python script
python -c "
import re
with open('pyproject.toml', 'r') as f:
    content = f.read()
version_match = re.search(r'version = \"([0-9]+)\.([0-9]+)\.([0-9]+)\"', content)
if version_match:
    major, minor, patch = map(int, version_match.groups())
    new_version = f'{major}.{minor}.{patch + 1}'
    new_content = re.sub(r'version = \"[0-9]+\.[0-9]+\.[0-9]+\"', f'version = \"{new_version}\"', content)
    with open('pyproject.toml', 'w') as f:
        f.write(new_content)
    print(new_version)
else:
    print('Version not found')
    exit(1)
" > /tmp/new_version

# Get the new version
version=$(cat /tmp/new_version)
rm /tmp/new_version

# Create a new branch
git checkout -b release/$version

# Commit the change
git add .
git commit -m "chore(pyproject.toml): Bumps version to $version"

# Push the branch
git push origin release/$version