# PPT Workbench Integration

Use this integration only when the task supplies a callback command or the environment provides a workbench server entry point. Do not search dated visualization directories or hard-code a machine-specific path.

## Completion Record

After every `ppt-correct` gate passes and the ledger state is `verified-final`, resolve the workbench entry point in this order:

1. an explicit command supplied by the current task;
2. the `PPT_WORKBENCH_SERVER` environment variable containing the absolute path to `server.py`.

When neither exists, skip registration and report that the optional workbench entry point was not configured. Do not downgrade an otherwise verified deck solely because this optional integration is absent.

When configured, run:

```powershell
python $env:PPT_WORKBENCH_SERVER record `
  --project "PPT主题" `
  --stage animation `
  --artifact "最终PPTX绝对路径"
```

Use the prompt/PDF theme as the project name. Never record `working`, `candidate`, incomplete-animation, or failed artifacts as complete.

## Batch Callback Contract

When the batch prompt supplies a batch ID, product key, and callback command:

1. Before processing that product, execute the supplied `running` callback.
2. Execute `succeeded` only after the ledger reaches `verified-final`.
3. On a terminal failure, execute `failed` with a concise error, then continue with the next product when the batch contract says to continue.
4. Do not edit workbench business state directly; callbacks and artifact rescans own that state.

Use the callback command exactly as supplied. A callback success is transport evidence, not PPT acceptance evidence.
