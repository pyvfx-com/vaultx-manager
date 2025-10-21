name: 🚀 VaultX Cross-Platform Release

on:
  push:
    tags:
      - 'v*.*.*'   # Example: v1.0.0, v1.2.3

jobs:
  build-and-release:
    name: Build & Release VaultX
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: [3.11]

    permissions:
      contents: write

    steps:
    - name: 📥 Checkout repository
      uses: actions/checkout@v4

    - name: 🐍 Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: ⚙️ Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller

    - name: 🧪 Run tests
      run: |
        python test_vaultx.py

    # 🧱 Build executables using PyInstaller
    - name: 🧱 Build VaultX Executable
      run: |
        echo "Building VaultX binary..."
        pyinstaller --noconfirm --onefile --windowed \
          --name "VaultX_${{ runner.os }}" \
          vaultx_app.py
      shell: bash

    - name: 🗜 Prepare distribution artifacts
      run: |
        mkdir -p dist_release
        cp -r dist/* dist_release/
        zip -r dist_release/VaultX_${{ runner.os }}_${{ github.ref_name }}.zip dist_release/*
        echo "✅ Built zip archive for ${{ runner.os }}"

    # 📝 Generate release notes dynamically
    - name: 📝 Generate release notes
      id: changelog
      run: |
        echo "### 🚀 VaultX ${GITHUB_REF_NAME} Release" > release_notes.md
        echo "" >> release_notes.md
        echo "**Release Date:** $(date)" >> release_notes.md
        echo "" >> release_notes.md
        echo "**Recent Commits:**" >> release_notes.md
        git log -5 --pretty=format:"- %s (%h)" >> release_notes.md
        echo "" >> release_notes.md
        echo "**Builds Included:**" >> release_notes.md
        echo "- 🪟 Windows Executable (.exe)" >> release_notes.md
        echo "- 🐧 Linux Binary (.bin)" >> release_notes.md
        echo "- 📦 Source ZIP" >> release_notes.md
        echo "" >> release_notes.md
        echo "✅ Built & tested automatically by GitHub Actions." >> release_notes.md

    # 🚀 Publish release and upload binaries
    - name: 🚀 Create GitHub Release
      uses: softprops/action-gh-release@v2
      with:
        tag_name: ${{ github.ref_name }}
        name: "VaultX ${{ github.ref_name }}"
        body_path: release_notes.md
        files: |
          dist_release/VaultX_${{ runner.os }}_${{ github.ref_name }}.zip
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
