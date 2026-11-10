#!/bin/zsh
# One run at a time; each run backs off on throttling inside the script. Job fields have no spaces.
# Batch cap: no run starts once the finished runs' metered cost reaches BATCH_CAP_USD (each run is
# itself capped at a forced submit at $2.50, so the batch total stays under BATCH_CAP_USD + ~$2.70).
SP=/private/tmp/claude-501/-Users-cwook-Documents-neurorepro/3dd59e81-2184-4e23-84d2-3fdebc048a02/scratchpad
R=$SP/agent_proto/runs_v2
BATCH_CAP_USD=28
# metered by runs that crashed in the network outage of 2026-11-10 (logs in crashed_network/)
CARRIED_USD=1.1949
cd /Users/cwook/Documents/neurorepro/fmri-repro-agent/extractor_mvp
export PYTHONPATH=$SP/wt_3fa32b6/extractor_mvp/src:$SP/wt_3fa32b6/src:$SP/agent_proto
while read -r pid tag pdf; do
  if [ -f $R/$tag.json ]; then echo "[$tag] SKIPPED: result already on disk"; continue; fi
  # counted from every run's per-turn log (its last metered total), so a crashed run counts too
  spent=$(python3 -c "
import glob,re
t=$CARRIED_USD
for f in glob.glob('$R/logs/*.log'):
    c=[float(x) for x in re.findall(r'turn \d+: \[.*?\] \\\$([\d.]+)', open(f).read())]
    t+=max(c) if c else 0
print(round(t,4))")
  if python3 -c "import sys; sys.exit(0 if $spent >= $BATCH_CAP_USD else 1)"; then
    echo "[$tag] SKIPPED: batch cap reached (spent \$$spent of \$$BATCH_CAP_USD)"
    continue
  fi
  .venv/bin/python $SP/agent_proto/agent_proto_v2.py --paper "$pdf" --paper-id "$pid" --out $R/$tag.json > $R/logs/$tag.log 2>&1 < /dev/null
  echo "[$tag] $(tail -1 $R/logs/$tag.log) (batch spent before this run: \$$spent)"
done < $R/jobs.tsv
echo ALL_DONE
