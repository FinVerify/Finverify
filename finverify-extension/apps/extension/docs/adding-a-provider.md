# Adding a provider

This walks through turning an inert stub (`adapters/claude`, `adapters/gemini`,
`adapters/copilot`, `adapters/perplexity`) into a real, active adapter. Using
Claude as the example, but the steps are the same for any provider.

## Why this is a manual, one-at-a-time process

Every step here exists because guessing at another product's DOM and
shipping it is worse than not having the feature: a wrong selector doesn't
just silently do nothing, it can also misfire (e.g. `findToolbar`'s
label-matching heuristic finding the wrong button on a differently-laid-out
page). Each provider needs a person actually looking at real, live markup.

## Steps

1. **Open the product and inspect real assistant messages.** Look for
   whatever the product uses to distinguish an assistant turn from a user
   turn — an attribute like ChatGPT's `data-message-author-role`, a stable
   class name, ARIA role, whatever's actually there. Check it across a few
   different conversations/message types (short replies, code blocks,
   tables) since some markup only shows up conditionally.

2. **Write the real selectors** in `adapters/claude/index.ts`, following the
   pattern in `adapters/chatgpt/index.ts`:
   - An ordered list of fallback selectors for `findMessages`, most
     specific first, each wrapped so a thrown `DOMException` degrades to
     "found nothing" rather than crashing.
   - A semantic last-resort (text-length / not-an-input / not-a-user-turn
     heuristics) so a future markup change degrades gracefully instead of
     going fully dark.
   - `findToolbar` — same fallback-chain approach, matching on
     `aria-label` content where possible (far more stable across redesigns
     than class names).
   - `isStreaming` — best-effort only. It's fine (expected, even) for this
     to occasionally get it wrong; it must never throw, and must default
     to `false` ("assume settled") when there's no reliable signal — see
     the reasoning in `adapters/types.ts`.

3. **Test against a live conversation.** Load the extension unpacked,
   open the real product, and confirm:
   - the badge appears next to real assistant replies (and NOT next to
     user messages, system notices, or UI chrome)
   - it appears reasonably promptly on a streaming response, not only
     after generation finishes
   - `extractText` returns clean prose, not markup/UI leftovers
   - the toolbar anchor point looks visually native, not bolted on

4. **Flip `verified: true`** in that adapter's `createUnverifiedStub(...)`
   call (replace it with a real object literal like `chatgptAdapter`'s, or
   extend the stub if most of it still applies).

5. **Add the origin to `manifest.json`'s `content_scripts[0].matches`.**
   Only after step 3 has actually passed — this is what turns the adapter
   on for real users.

6. **Update `docs/architecture.md`'s adapter table** (or add one if it's
   grown past a single verified entry) so the next person doesn't have to
   read source to know what's actually live.

## What NOT to do

- Don't flip `verified: true` from reading the product's source/docs
  alone — DOM structure and rendered markup frequently don't match a
  product's public API surface or marketing copy.
- Don't copy ChatGPT's selectors as a starting guess and ship them
  unverified "since they're probably close enough" — different products'
  markup conventions vary enough that this usually produces exactly the
  silent-failure-or-misfire outcome this whole process exists to avoid.
- Don't add multiple providers in one change. Each is its own PR/session
  with its own live-testing pass.
