# Workspace trust-score accessibility

Audit date: 2026-08-14

## Scope

This audit covers the trust and confidence indicators in `components/workspace`, including the default verification-coverage view and the selected-company integrity view.

## Implemented behavior

- Numeric trust and integrity scores expose a named ARIA `meter` with a 0–100 range and descriptive value text.
- Confidence levels are communicated in text and through accessible names, not by color alone.
- Trust scores and confidence bars are reachable with `Tab` and display a 2px visible focus outline.
- The verification-coverage grid uses native table, header, and caption semantics.
- The transaction-monitor filters have programmatic labels.

The score indicators are read-only. Focusing them exposes their value and context; Enter and Space intentionally perform no action.

## Verification

Automated checks used axe-core 4.10.3 with WCAG 2 A/AA and WCAG 2.1 A/AA tags.

| View | Passed checks | Critical violations |
| --- | ---: | ---: |
| Default workspace | 26 | 0 |
| NVIDIA integrity view | 21 | 0 |

Keyboard verification confirmed that all seven company trust scores and the selected-company integrity score plus its three confidence bars are reachable in DOM order and receive a visible focus indicator.

Repository checks:

- `npm run lint` — passes with no errors; existing warnings remain outside this change.
- `npm run build` — passes.

## Known follow-up work

The full workspace audit still reports pre-existing serious findings for low-contrast secondary text and some scrollable regions that are not keyboard focusable. They are outside the trust-score component scope and should be handled separately.
