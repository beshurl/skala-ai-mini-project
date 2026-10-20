import json,sys
from pathlib import Path
if len(sys.argv)!=3:raise SystemExit('python scripts/compare.py outputs/base_mlx/metrics.json outputs/tuned_mlx/metrics.json')
a,b=[json.loads(Path(x).read_text(encoding='utf8')) for x in sys.argv[1:]]
for k in ('accuracy','macro_f1','invalid_rate','mean_latency_s'):
 print(f'{k}: base={a[k]:.4f}, tuned={b[k]:.4f}, delta={b[k]-a[k]:+.4f}')
