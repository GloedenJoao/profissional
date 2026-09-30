# Agents

Agents are measurable local strategy units.

## Contract

- Input type: `StrategyContext`
- Output type: `StrategySignal`
- Required output fields: `predicted_price`, `confidence`, `reasoning`
- Valid directions: `up`, `down`, `flat`
- Confidence is a float between `0.0` and `1.0`

## Adding an agent

1. Add a strategy seed or create a catalog entry with Python code exposing `predict(context)`.
2. Keep strategy code pure: no imports, filesystem, network, eval/exec, or hidden global state.
3. Execute it through `StrategyExecutor`, never directly from routers/templates.
4. Add tests for sandbox acceptance/rejection and prediction behavior.

The sandbox is in-process and intended for trusted local experimentation. It is not a security boundary for hostile code.
