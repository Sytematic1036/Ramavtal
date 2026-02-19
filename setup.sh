#!/bin/bash
# setup.sh - Ramavtal Semantisk Dokumentsökning
# Sätter upp projektet från scratch

set -e

echo "=== Ramavtal Setup ==="
echo ""

# 1. Kontrollera Python
if ! command -v python &> /dev/null; then
    echo "FEL: Python hittades inte. Installera Python 3.10+ först."
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1)
echo "Python: $PYTHON_VERSION"

# 2. Skapa virtuell miljö om den inte finns
if [ ! -d "venv" ]; then
    echo "Skapar virtuell miljö..."
    python -m venv venv
else
    echo "Virtuell miljö finns redan."
fi

# 3. Aktivera venv
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "Virtuell miljö aktiverad: $(which python)"

# 4. Installera dependencies
echo ""
echo "Installerar dependencies..."
pip install -r requirements.txt --quiet

# 5. Skapa Docs-mapp om den inte finns
if [ ! -d "Docs" ]; then
    mkdir Docs
    echo "Skapade Docs/ - lägg dina PDF/DOCX-filer här."
else
    DOC_COUNT=$(ls Docs/*.pdf Docs/*.docx 2>/dev/null | wc -l)
    echo "Docs/ finns redan ($DOC_COUNT dokument)."
fi

# 6. Kontrollera ANTHROPIC_API_KEY
echo ""
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "OBS: ANTHROPIC_API_KEY är inte satt."
    echo "     Krävs enbart för 'kategori'-kommandot (Claude-klassificering)."
    echo "     Sätt med: export ANTHROPIC_API_KEY=sk-ant-..."
else
    echo "ANTHROPIC_API_KEY: konfigurerad"
fi

# 7. Koppla GitHub remote om det saknas
if ! git remote get-url origin &> /dev/null 2>&1; then
    echo ""
    echo "Kopplar GitHub remote..."
    git remote add origin https://github.com/Sytematic1036/Ramavtal.git
    echo "Remote tillagd: https://github.com/Sytematic1036/Ramavtal"
else
    REMOTE_URL=$(git remote get-url origin)
    echo "GitHub remote: $REMOTE_URL"
fi

# 8. Klar
echo ""
echo "=== Setup klar ==="
echo ""
echo "Nästa steg:"
echo "  1. Lägg PDF/DOCX-filer i Docs/"
echo "  2. python search.py index        # Indexera dokument"
echo "  3. python search.py search \"..\"  # Sök"
echo "  4. python search.py kategori \"..\" # Kategorisök (kräver API-nyckel)"
