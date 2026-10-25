mkdir -p org-boundary/evidence/runtime
if [ -f org-boundary/fixtures/cross-org-ingress.json ]; then
  python3 org-boundary/runtime/process_boundary.py \
    --envelope org-boundary/fixtures/cross-org-ingress.json \
    --out org-boundary/evidence/runtime/cross-org-execution.json
fi
