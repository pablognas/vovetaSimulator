$seeds = @(42, 123, 456, 789, 1001, 2002, 3003, 4004, 5005, 6006)
$topologies = @("1x1", "1x5", "1x10", "1x25", "1x50","2x1", "2x5", "2x10", "2x25", "2x50", "3x1", "3x5", "3x10", "3x25", "3x50")
# $topologies = @("3x1", "3x5", "3x10", "3x25", "3x50", "4x1", "4x5", "4x10", "4x25", "4x50", "5x1", "5x5", "5x10", "5x25", "5x50")

function Run-Scenario {
    param($name, $variation, $jitter, $cycles)
    foreach ($topo in $topologies) {
        $layers = $topo.Split("x")[0]
        $nodes = $topo.Split("x")[1]
        $seedIdx = 0
        foreach ($seed in $seeds) {
            $seedIdx++
            $simName = "${name}_${topo}_seed${seedIdx}"
            Write-Host "Running $simName..."
            python vovetasimulator4.py `
                --sim_name $simName `
                --seed $seed `
                --harvesting_variation $variation `
                --tick_jitter $jitter `
                --cycles $cycles `
                --layers $layers `
                --nodes_per_layer $nodes
        }
    }
}

# Write-Host "=== C1: Baseline ==="
# Run-Scenario -name "C1_baseline" -variation 0 -jitter 0 -cycles 1440

Write-Host "=== C2: Energy Variation 5% ==="
Run-Scenario -name "C2_evar5" -variation 5 -jitter 0 -cycles 1440
Write-Host "=== C2: Energy Variation 10% ==="
Run-Scenario -name "C2_evar10" -variation 10 -jitter 0 -cycles 1440
# Write-Host "=== C2: Energy Variation 15% ==="
# Run-Scenario -name "C2_evar15" -variation 15 -jitter 0 -cycles 1440

# Write-Host "=== C3: Tick Jitter 5% ==="
# Run-Scenario -name "C3_jitter5" -variation 7 -jitter 5 -cycles 1440
# Write-Host "=== C3: Tick Jitter 10% ==="
# Run-Scenario -name "C3_jitter10" -variation 7 -jitter 10 -cycles 1440
# Write-Host "=== C3: Tick Jitter 15% ==="
# Run-Scenario -name "C3_jitter15" -variation 7 -jitter 15 -cycles 1440

# Write-Host "=== C4: Long-running 2h ==="
# Run-Scenario -name "C4_long2h" -variation 7 -jitter 0 -cycles 2880
# Write-Host "=== C4: Long-running 4h ==="
# Run-Scenario -name "C4_long4h" -variation 7 -jitter 0 -cycles 5760
# Write-Host "=== C4: Long-running 6h ==="
# Run-Scenario -name "C4_long6h" -variation 7 -jitter 0 -cycles 8640

# Write-Host "All scenarios complete."