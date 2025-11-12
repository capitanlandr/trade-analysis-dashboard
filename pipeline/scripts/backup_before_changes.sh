#!/bin/bash
# Backup critical files before making dynamic weekly column changes

BACKUP_DIR="backups/pre_dynamic_columns_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Files to backup
FILES=(
    "stage3_cache_values.py"
    "weekly_2026_pick_projections_expanded.csv"
    "asset_values_cache.csv"
    "league_trades_analysis_pipeline.csv"
    "constants.py"
    "config/default.yaml"
)

echo "🔄 Creating backup in $BACKUP_DIR"

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$BACKUP_DIR/"
        echo "✓ Backed up $file"
    else
        echo "⚠️  File not found: $file"
    fi
done

# Create restore script
cat > "$BACKUP_DIR/restore.sh" << EOF
#!/bin/bash
# Restore files from this backup
echo "🔄 Restoring files from $BACKUP_DIR"

# Restore each file
FILES=(
    "stage3_cache_values.py"
    "weekly_2026_pick_projections_expanded.csv"
    "asset_values_cache.csv"
    "league_trades_analysis_pipeline.csv"
    "constants.py"
    "config/default.yaml"
)

for file in "\${FILES[@]}"; do
    if [ -f "$BACKUP_DIR/\$file" ]; then
        cp "$BACKUP_DIR/\$file" "./\$file"
        echo "✓ Restored \$file"
    else
        echo "⚠️  Backup file not found: \$file"
    fi
done

echo "✅ Files restored from backup"
echo "Run 'python3 validate_pipeline.py' to verify restoration"
EOF

chmod +x "$BACKUP_DIR/restore.sh"

# Create validation snapshot
echo "📊 Creating validation snapshot..."
if [ -f "asset_values_cache.csv" ]; then
    wc -l asset_values_cache.csv > "$BACKUP_DIR/cache_line_count.txt"
    echo "Cache line count: $(cat "$BACKUP_DIR/cache_line_count.txt")"
fi

if [ -f "league_trades_analysis_pipeline.csv" ]; then
    wc -l league_trades_analysis_pipeline.csv > "$BACKUP_DIR/analysis_line_count.txt"
    echo "Analysis line count: $(cat "$BACKUP_DIR/analysis_line_count.txt")"
fi

echo "✅ Backup complete: $BACKUP_DIR"
echo "📋 To restore: ./$BACKUP_DIR/restore.sh"
echo "🔍 Validation data saved for comparison"