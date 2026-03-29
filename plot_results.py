"""
plot_results.py — Generate plots from simulation results.

Reads all results/*.json files recursively, parses scenario names, and
generates plots saved as PNG files in a plots/ directory.

Usage:
    python plot_results.py [--results_dir RESULTS_DIR]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TOPOLOGY_ORDER = ['1x1', '1x2', '2x1', '2x2', '2x4', '3x2', '3x4', '2x25']
ENERGY_VAR_ORDER = ['0', '7', '15', '30']
JITTER_ORDER = ['0', '10', '20', '50']
DURATION_ORDER = ['1h', '2h', '4h', '6h']

plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'legend.fontsize': 9,
    'figure.dpi': 120,
})


def _topology_sort_key(topo: str) -> tuple:
    """Return a sort key for topology strings like '2x25'."""
    parts = topo.lower().split('x')
    try:
        return (int(parts[0]), int(parts[1]))
    except (IndexError, ValueError):
        return (999, 999)


def sorted_topologies(topos):
    known = [t for t in TOPOLOGY_ORDER if t in topos]
    extra = sorted([t for t in topos if t not in TOPOLOGY_ORDER], key=_topology_sort_key)
    return known + extra


def load_results(results_dir: str) -> list:
    """Recursively load all results.json files under results_dir."""
    records = []
    for path in Path(results_dir).rglob('results.json'):
        try:
            with open(path) as f:
                data = json.load(f)
            records.append(data)
        except (json.JSONDecodeError, OSError) as exc:
            print(f'Warning: could not read {path}: {exc}', file=sys.stderr)
    return records


def parse_scenario(name: str) -> dict:
    """
    Parse a scenario name into components.

    Supported patterns:
      C1_baseline_{topology}_seed{N}
      C2_evar{pct}_{topology}_seed{N}
      C3_jitter{pct}_{topology}_seed{N}
      C4_long{hours}h_{topology}_seed{N}
    """
    info = {'raw': name, 'scenario': None, 'topology': None, 'seed': None,
            'energy_var': None, 'jitter': None, 'duration': None}

    m = re.match(r'^(C[1-4])_', name)
    if m:
        info['scenario'] = m.group(1)

    m = re.search(r'_seed(\d+)', name)
    if m:
        info['seed'] = int(m.group(1))

    # topology: last token before _seedN, formatted as NxM
    m = re.search(r'_(\d+x\d+)_seed', name)
    if m:
        info['topology'] = m.group(1)

    # C2: energy variation
    m = re.search(r'_evar(\d+)_', name)
    if m:
        info['energy_var'] = m.group(1)

    # C3: jitter
    m = re.search(r'_jitter(\d+)_', name)
    if m:
        info['jitter'] = m.group(1)

    # C4: duration
    m = re.search(r'_long(\d+h)_', name)
    if m:
        info['duration'] = m.group(1)

    return info


def enrich(records: list) -> list:
    """Attach parsed scenario info to each record."""
    enriched = []
    for rec in records:
        name = rec.get('simulation_name', '')
        info = parse_scenario(name)
        # override topology with parameters field if present
        if 'parameters' in rec and 'topology' in rec['parameters']:
            info['topology'] = rec['parameters']['topology']
        rec['_info'] = info
        enriched.append(rec)
    return enriched


def get_metric(rec: dict, key: str, default=None):
    return rec.get('metrics', {}).get(key, default)


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def group_by(records, *keys):
    """Group records into nested dicts by successive keys from _info."""
    result = {}
    for rec in records:
        node = result
        for k in keys[:-1]:
            val = rec['_info'].get(k)
            node = node.setdefault(val, {})
        val = rec['_info'].get(keys[-1])
        node.setdefault(val, []).append(rec)
    return result


def mean_std(values):
    if not values:
        return float('nan'), float('nan')
    arr = np.array(values, dtype=float)
    return float(np.mean(arr)), float(np.std(arr))


def collect_pdr(records):
    """Return list of PDR values from a list of records."""
    return [get_metric(r, 'pdr', float('nan')) for r in records]


# ---------------------------------------------------------------------------
# Plot 1 — C1 Baseline: PDR vs Topology
# ---------------------------------------------------------------------------

def plot_c1_pdr_vs_topology(records, out_dir):
    c1 = [r for r in records if r['_info']['scenario'] == 'C1']
    if not c1:
        print('Plot 1 skipped: no C1 data.')
        return

    by_topo = group_by(c1, 'topology')
    topos = sorted_topologies(by_topo.keys())

    means, stds = [], []
    for t in topos:
        recs = by_topo.get(t, [])
        m, s = mean_std(collect_pdr(recs))
        means.append(m)
        stds.append(s)

    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(topos))
    ax.bar(x, means, yerr=stds, capsize=4, color='steelblue', alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(topos)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel('Topology')
    ax.set_ylabel('PDR')
    ax.set_title('C1 Baseline — PDR vs Topology')
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    fig.tight_layout()
    path = os.path.join(out_dir, 'plot1_c1_pdr_vs_topology.png')
    fig.savefig(path)
    plt.close(fig)
    print(f'Saved: {path}')


# ---------------------------------------------------------------------------
# Plot 2 — C2: PDR vs Energy Variation (grouped bars)
# ---------------------------------------------------------------------------

def plot_c2_pdr_vs_evar(records, out_dir):
    c2 = [r for r in records if r['_info']['scenario'] == 'C2']
    if not c2:
        print('Plot 2 skipped: no C2 data.')
        return

    by_topo_evar = group_by(c2, 'topology', 'energy_var')
    topos = sorted_topologies(by_topo_evar.keys())
    evars = [v for v in ENERGY_VAR_ORDER if any(v in by_topo_evar.get(t, {}) for t in topos)]
    if not evars:
        evars = sorted({r['_info']['energy_var'] for r in c2 if r['_info']['energy_var']})

    _grouped_bar_plot(
        groups=topos,
        bars=evars,
        data_fn=lambda t, e: collect_pdr(by_topo_evar.get(t, {}).get(e, [])),
        xlabel='Topology',
        ylabel='PDR',
        title='C2 — PDR vs Energy Variation',
        legend_title='Energy Variation (%)',
        legend_labels=[f'{e}%' for e in evars],
        filename=os.path.join(out_dir, 'plot2_c2_pdr_vs_evar.png'),
    )


# ---------------------------------------------------------------------------
# Plot 3 — C3: PDR vs Tick Jitter (grouped bars)
# ---------------------------------------------------------------------------

def plot_c3_pdr_vs_jitter(records, out_dir):
    c3 = [r for r in records if r['_info']['scenario'] == 'C3']
    if not c3:
        print('Plot 3 skipped: no C3 data.')
        return

    by_topo_jitter = group_by(c3, 'topology', 'jitter')
    topos = sorted_topologies(by_topo_jitter.keys())
    jitters = [v for v in JITTER_ORDER if any(v in by_topo_jitter.get(t, {}) for t in topos)]
    if not jitters:
        jitters = sorted({r['_info']['jitter'] for r in c3 if r['_info']['jitter']})

    _grouped_bar_plot(
        groups=topos,
        bars=jitters,
        data_fn=lambda t, j: collect_pdr(by_topo_jitter.get(t, {}).get(j, [])),
        xlabel='Topology',
        ylabel='PDR',
        title='C3 — PDR vs Tick Jitter',
        legend_title='Jitter (%)',
        legend_labels=[f'±{j}%' for j in jitters],
        filename=os.path.join(out_dir, 'plot3_c3_pdr_vs_jitter.png'),
    )


# ---------------------------------------------------------------------------
# Plot 4 — C4: PDR over Duration (line plot)
# ---------------------------------------------------------------------------

def plot_c4_pdr_over_duration(records, out_dir):
    c4 = [r for r in records if r['_info']['scenario'] == 'C4']
    if not c4:
        print('Plot 4 skipped: no C4 data.')
        return

    by_topo_dur = group_by(c4, 'topology', 'duration')
    topos = sorted_topologies(by_topo_dur.keys())

    # Determine duration order
    all_durs = sorted({r['_info']['duration'] for r in c4 if r['_info']['duration']},
                      key=lambda d: int(re.sub(r'\D', '', d) or 0))
    durs = [d for d in DURATION_ORDER if d in all_durs] + [d for d in all_durs if d not in DURATION_ORDER]

    fig, ax = plt.subplots(figsize=(8, 4))
    colors = plt.cm.tab10(np.linspace(0, 0.8, max(len(topos), 1)))
    for topo, color in zip(topos, colors):
        means, stds, xs = [], [], []
        for dur in durs:
            recs = by_topo_dur.get(topo, {}).get(dur, [])
            m, s = mean_std(collect_pdr(recs))
            if not np.isnan(m):
                means.append(m)
                stds.append(s)
                xs.append(dur)
        if xs:
            ax.errorbar(xs, means, yerr=stds, marker='o', label=topo, color=color, capsize=4)

    ax.set_ylim(0, 1.05)
    ax.set_xlabel('Duration')
    ax.set_ylabel('PDR')
    ax.set_title('C4 — PDR over Duration')
    ax.legend(title='Topology', bbox_to_anchor=(1.02, 1), loc='upper left')
    ax.grid(linestyle='--', alpha=0.5)
    fig.tight_layout()
    path = os.path.join(out_dir, 'plot4_c4_pdr_over_duration.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {path}')


# ---------------------------------------------------------------------------
# Plot 5 — BS Resets across C1, C2, C3
# ---------------------------------------------------------------------------

def plot_bs_resets(records, out_dir):
    relevant = [r for r in records if r['_info']['scenario'] in ('C1', 'C2', 'C3')]
    if not relevant:
        print('Plot 5 skipped: no C1/C2/C3 data.')
        return

    by_scenario_topo = group_by(relevant, 'scenario', 'topology')
    scenarios = [s for s in ('C1', 'C2', 'C3') if s in by_scenario_topo]
    all_topos = sorted_topologies({t for s in scenarios for t in by_scenario_topo.get(s, {})})

    def collect_resets(recs):
        return [get_metric(r, 'bs_resets', float('nan')) for r in recs]

    _grouped_bar_plot(
        groups=scenarios,
        bars=all_topos,
        data_fn=lambda s, t: collect_resets(by_scenario_topo.get(s, {}).get(t, [])),
        xlabel='Scenario',
        ylabel='BS Resets',
        title='BS Resets — C1 vs C2 vs C3',
        legend_title='Topology',
        legend_labels=all_topos,
        filename=os.path.join(out_dir, 'plot5_bs_resets.png'),
    )


# ---------------------------------------------------------------------------
# Plot 6 — Control Overhead across scenarios
# ---------------------------------------------------------------------------

def plot_control_overhead(records, out_dir):
    relevant = [r for r in records if r['_info']['scenario'] in ('C1', 'C2', 'C3')]
    if not relevant:
        print('Plot 6 skipped: no C1/C2/C3 data.')
        return

    by_scenario_topo = group_by(relevant, 'scenario', 'topology')
    scenarios = [s for s in ('C1', 'C2', 'C3') if s in by_scenario_topo]
    all_topos = sorted_topologies({t for s in scenarios for t in by_scenario_topo.get(s, {})})

    def collect_overhead(recs):
        return [get_metric(r, 'control_overhead', float('nan')) for r in recs]

    _grouped_bar_plot(
        groups=scenarios,
        bars=all_topos,
        data_fn=lambda s, t: collect_overhead(by_scenario_topo.get(s, {}).get(t, [])),
        xlabel='Scenario',
        ylabel='Control Overhead (setup_msgs / data_msgs)',
        title='Control Overhead — C1 vs C2 vs C3',
        legend_title='Topology',
        legend_labels=all_topos,
        filename=os.path.join(out_dir, 'plot6_control_overhead.png'),
    )


# ---------------------------------------------------------------------------
# Plot 7 — Average Latency (ms) across scenarios
# ---------------------------------------------------------------------------

def plot_latency_ms(records, out_dir):
    with_latency = [r for r in records if get_metric(r, 'avg_latency_ms', 0) > 0]
    if not with_latency:
        print('Plot 7 skipped: no latency (ms) data available.')
        return

    by_scenario_topo = group_by(with_latency, 'scenario', 'topology')
    scenarios = sorted({r['_info']['scenario'] for r in with_latency if r['_info']['scenario']})
    all_topos = sorted_topologies({t for s in scenarios for t in by_scenario_topo.get(s, {})})

    def collect_lat(recs):
        return [get_metric(r, 'avg_latency_ms', float('nan')) for r in recs]

    _grouped_bar_plot(
        groups=scenarios,
        bars=all_topos,
        data_fn=lambda s, t: collect_lat(by_scenario_topo.get(s, {}).get(t, [])),
        xlabel='Scenario',
        ylabel='Average Latency (ms)',
        title='Average End-to-End Latency (ms)',
        legend_title='Topology',
        legend_labels=all_topos,
        filename=os.path.join(out_dir, 'plot7_avg_latency_ms.png'),
    )


# ---------------------------------------------------------------------------
# Plot 8 — Average Latency (ticks) across scenarios
# ---------------------------------------------------------------------------

def plot_latency_ticks(records, out_dir):
    with_latency = [r for r in records if get_metric(r, 'avg_latency_ticks', 0) > 0]
    if not with_latency:
        print('Plot 8 skipped: no latency (ticks) data available.')
        return

    by_scenario_topo = group_by(with_latency, 'scenario', 'topology')
    scenarios = sorted({r['_info']['scenario'] for r in with_latency if r['_info']['scenario']})
    all_topos = sorted_topologies({t for s in scenarios for t in by_scenario_topo.get(s, {})})

    def collect_lat(recs):
        return [get_metric(r, 'avg_latency_ticks', float('nan')) for r in recs]

    _grouped_bar_plot(
        groups=scenarios,
        bars=all_topos,
        data_fn=lambda s, t: collect_lat(by_scenario_topo.get(s, {}).get(t, [])),
        xlabel='Scenario',
        ylabel='Average Latency (ticks)',
        title='Average End-to-End Latency (ticks)',
        legend_title='Topology',
        legend_labels=all_topos,
        filename=os.path.join(out_dir, 'plot8_avg_latency_ticks.png'),
    )


# ---------------------------------------------------------------------------
# Generic grouped-bar helper
# ---------------------------------------------------------------------------

def _grouped_bar_plot(groups, bars, data_fn, xlabel, ylabel, title,
                      legend_title, legend_labels, filename):
    """
    Draw a grouped bar chart.

    groups: list of group labels (x-axis positions)
    bars:   list of bar labels (one colour per bar within each group)
    data_fn(group, bar) -> list of float values (averaged with std)
    """
    if not groups or not bars:
        print(f'Skipping {filename}: insufficient data.')
        return

    n_groups = len(groups)
    n_bars = len(bars)
    width = 0.7 / max(n_bars, 1)
    offsets = np.linspace(-(n_bars - 1) / 2 * width, (n_bars - 1) / 2 * width, n_bars)

    colors = plt.cm.tab10(np.linspace(0, 0.9, max(n_bars, 1)))
    fig, ax = plt.subplots(figsize=(max(6, n_groups * 1.5), 4))

    for bi, (bar_label, offset, color) in enumerate(zip(bars, offsets, colors)):
        means, stds = [], []
        for g in groups:
            vals = [v for v in data_fn(g, bar_label) if not (isinstance(v, float) and np.isnan(v))]
            m, s = mean_std(vals) if vals else (float('nan'), 0.0)
            means.append(m)
            stds.append(s)

        x = np.arange(n_groups) + offset
        valid = [(i, m, s) for i, (m, s) in enumerate(zip(means, stds)) if not np.isnan(m)]
        if valid:
            xi, mi, si = zip(*valid)
            ax.bar(np.array(xi) + offset, mi, width=width, yerr=si, capsize=3,
                   label=legend_labels[bi] if bi < len(legend_labels) else bar_label,
                   color=color, alpha=0.85)

    ax.set_xticks(np.arange(n_groups))
    ax.set_xticklabels(groups)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(title=legend_title, bbox_to_anchor=(1.02, 1), loc='upper left')
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    fig.tight_layout()
    fig.savefig(filename, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {filename}')


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def print_summary(records):
    header = f"{'Simulation':<45} {'Scenario':<8} {'Topology':<10} {'Seed':<6} {'PDR':>6} {'BSRst':>6} {'Ovhd':>6} {'LatMs':>8} {'LatTk':>7}"
    print('\n' + '=' * len(header))
    print(header)
    print('=' * len(header))
    for r in sorted(records, key=lambda x: x.get('simulation_name', '')):
        info = r['_info']
        m = r.get('metrics', {})
        print(
            f"{r.get('simulation_name', ''):<45} "
            f"{info.get('scenario') or '':<8} "
            f"{info.get('topology') or '':<10} "
            f"{str(info.get('seed') or ''):<6} "
            f"{m.get('pdr', float('nan')):>6.4f} "
            f"{m.get('bs_resets', '?'):>6} "
            f"{m.get('control_overhead', float('nan')):>6.2f} "
            f"{m.get('avg_latency_ms', 0):>8.1f} "
            f"{m.get('avg_latency_ticks', 0):>7.1f}"
        )
    print('=' * len(header) + '\n')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Generate plots from simulation results.')
    parser.add_argument('--results_dir', default='results', help='Directory containing results (default: results/)')
    args = parser.parse_args()

    results_dir = args.results_dir
    if not os.path.isdir(results_dir):
        print(f'Error: results directory "{results_dir}" not found.', file=sys.stderr)
        sys.exit(1)

    out_dir = 'plots'
    os.makedirs(out_dir, exist_ok=True)

    print(f'Loading results from: {results_dir}')
    records = load_results(results_dir)
    if not records:
        print('No results found. Exiting.')
        sys.exit(0)

    records = enrich(records)
    print(f'Loaded {len(records)} result(s).\n')

    print_summary(records)

    plot_c1_pdr_vs_topology(records, out_dir)
    plot_c2_pdr_vs_evar(records, out_dir)
    plot_c3_pdr_vs_jitter(records, out_dir)
    plot_c4_pdr_over_duration(records, out_dir)
    plot_bs_resets(records, out_dir)
    plot_control_overhead(records, out_dir)
    plot_latency_ms(records, out_dir)
    plot_latency_ticks(records, out_dir)

    print(f'\nAll plots saved to: {out_dir}/')


if __name__ == '__main__':
    main()
