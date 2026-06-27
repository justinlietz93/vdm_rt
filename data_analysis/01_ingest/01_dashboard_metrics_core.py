#!/usr/bin/env python3
from __future__ import annotations
import argparse
import matplotlib.pyplot as plt
import pandas as pd
from common import ensure_dir, load_events_jsonl, parse_dashboard_targets, standardize, two_state_kmeans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', required=True)
    ap.add_argument('--html', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    out = ensure_dir(args.out)
    df = load_events_jsonl(args.events).sort_values('t').reset_index(drop=True)
    metrics = parse_dashboard_targets(args.html, df.columns)
    summary = []
    for m in metrics:
        s = pd.to_numeric(df[m], errors='coerce')
        summary.append({
            'metric': m, 'count': int(s.notna().sum()), 'mean': float(s.mean()), 'std': float(s.std()),
            'min': float(s.min()), 'median': float(s.median()), 'p95': float(s.quantile(0.95)), 'max': float(s.max())
        })
    pd.DataFrame(summary).to_csv(out / 'dashboard_metric_summary.csv', index=False)

    if not metrics:
        raise RuntimeError('No dashboard target metrics found in events/html pair.')

    n = len(metrics)
    fig, axes = plt.subplots(n, 1, figsize=(12, 2.2*n), sharex=True)
    if n == 1:
        axes = [axes]
    for ax, m in zip(axes, metrics):
        ax.plot(df['t'], df[m], linewidth=1.0)
        ax.set_ylabel(m)
        ax.grid(alpha=0.25)
    axes[-1].set_xlabel('tick')
    fig.tight_layout()
    fig.savefig(out / 'dashboard_target_metrics_panel.png', dpi=180)
    plt.close(fig)

    tail = df.tail(min(500, len(df))).copy()
    fig, axes = plt.subplots(n, 1, figsize=(12, 2.2*n), sharex=True)
    if n == 1:
        axes = [axes]
    for ax, m in zip(axes, metrics):
        ax.plot(tail['t'], tail[m], linewidth=1.0)
        ax.set_ylabel(m)
        ax.grid(alpha=0.25)
    axes[-1].set_xlabel('tick')
    fig.tight_layout()
    fig.savefig(out / 'dashboard_target_metrics_final500.png', dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12,6))
    for m in metrics[:8]:
        ax.plot(df['t'], standardize(df[m]), label=m, linewidth=1.0)
    ax.legend(ncol=2, fontsize=8)
    ax.grid(alpha=0.25)
    ax.set_xlabel('tick')
    ax.set_ylabel('z-score')
    fig.tight_layout()
    fig.savefig(out / 'dashboard_target_metrics_standardized.png', dpi=180)
    plt.close(fig)

    fit_cols = [c for c in ['connectome_entropy','vt_entropy','active_edges','sie_v2_valence_01','vt_coverage'] if c in df.columns]
    if len(fit_cols) >= 2:
        X = pd.concat([standardize(df[c]) for c in fit_cols], axis=1).to_numpy()
        labels = two_state_kmeans(X)
        if 'active_edges' in df.columns:
            mean0 = df.loc[labels==0, 'active_edges'].mean()
            mean1 = df.loc[labels==1, 'active_edges'].mean()
            if mean1 < mean0:
                labels = 1 - labels
        df['macro_refit'] = labels
        df['input_delta'] = pd.to_numeric(df.get('ute_in_count', 0), errors='coerce').fillna(0).diff().clip(lower=0).fillna(0)
        rows=[]
        for state in [0,1]:
            sub=df[df['macro_refit']==state]
            row={
                'macro_refit': state,
                'ticks': len(sub),
                'fraction': len(sub)/len(df),
                'input_rate': float((sub['input_delta']>0).mean()),
            }
            for col in ['connectome_entropy','vt_entropy','active_edges','b1_z','sie_v2_valence_01','vt_coverage']:
                if col in sub.columns:
                    row[f'mean_{col}'] = float(pd.to_numeric(sub[col], errors='coerce').mean())
            rows.append(row)
        pd.DataFrame(rows).to_csv(out/'scalar_struct_macro_summary.csv', index=False)

        fig, ax = plt.subplots(figsize=(12,4))
        ax.plot(df['t'], df['macro_refit'], drawstyle='steps-mid', linewidth=1.0)
        ax.set_xlabel('tick'); ax.set_ylabel('macro_refit'); ax.grid(alpha=0.25)
        fig.tight_layout(); fig.savefig(out/'scalar_struct_macrostate_over_time.png', dpi=180); plt.close(fig)

        fig, ax = plt.subplots(figsize=(12,4))
        ax.plot(df['t'], df['macro_refit'], drawstyle='steps-mid', linewidth=1.0, color='black', label='macro_refit')
        inp = df.loc[df['input_delta']>0, 't']
        ax.scatter(inp, [1.05]*len(inp), s=10, marker='|', label='input')
        ax.set_ylim(-0.2,1.2)
        ax.set_xlabel('tick'); ax.set_ylabel('state'); ax.grid(alpha=0.25); ax.legend()
        fig.tight_layout(); fig.savefig(out/'scalar_struct_macro_input_overlay.png', dpi=180); plt.close(fig)

if __name__ == '__main__':
    main()
