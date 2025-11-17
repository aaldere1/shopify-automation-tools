#!/bin/bash
# Quick progress checker for backfill

echo "📊 Backfill Progress Check"
echo "=========================="
echo ""

# Check if process is running
if pgrep -f "backfill-all.ts" > /dev/null; then
    echo "✅ Backfill process is RUNNING"
    echo ""
else
    echo "❌ Backfill process is NOT running"
    echo ""
fi

# Show recent log entries
echo "📝 Recent log output:"
echo "-------------------"
tail -50 backfill.log 2>/dev/null || echo "No log file found"

echo ""
echo "💡 To watch live progress, run: tail -f backfill.log"

